#!/usr/bin/env python3
"""
Automated Iceberg Format Benchmark Script
Tests different file formats and compression combinations
"""

import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

class IcebergFormatBenchmark:
    def __init__(self):
        self.formats = ['parquet', 'orc', 'avro']
        self.compressions = ['snappy', 'gzip', 'zstd']
        self.scales = ['micro', 'medium', 'large']
        self.results = {}
        
    def run_benchmark(self, scale, format_type, compression):
        """Run benchmark for specific format/compression combination"""
        print(f"\n🔄 Testing {scale} scale: {format_type} + {compression}")
        
        start_time = time.time()
        
        try:
            # Generate test data
            data_success = self.generate_data(scale)
            if not data_success:
                return None
                
            # Create Iceberg table with specific format
            table_success = self.create_iceberg_table(scale, format_type, compression)
            if not table_success:
                return None
                
            # Run queries and measure performance
            query_results = self.run_queries(scale, format_type, compression)
            
            # Measure storage metrics
            storage_metrics = self.get_storage_metrics(scale, format_type, compression)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            result = {
                'scale': scale,
                'format': format_type,
                'compression': compression,
                'total_time_seconds': round(total_time, 2),
                'data_generation_success': data_success,
                'table_creation_success': table_success,
                'query_results': query_results,
                'storage_metrics': storage_metrics,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"✅ Completed in {total_time:.2f}s")
            return result
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                'scale': scale,
                'format': format_type, 
                'compression': compression,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def generate_data(self, scale):
        """Generate TPC-DS data for scale"""
        from src.iceberg_benchmark.utils import generate_tpcds_data
        
        scale_factors = {'micro': 0.001, 'medium': 0.1, 'large': 1.0}
        scale_factor = scale_factors[scale]
        
        data_dir = f"/app/data/{scale}"
        os.makedirs(data_dir, exist_ok=True)
        
        return generate_tpcds_data(scale_factor, data_dir)
    
    def create_iceberg_table(self, scale, format_type, compression):
        """Create Iceberg table with specific format and compression"""
        try:
            from pyspark.sql import SparkSession
            
            # Configure Spark with Iceberg
            spark = SparkSession.builder \
                .appName(f'IcebergBenchmark-{scale}-{format_type}-{compression}') \
                .config('spark.master', 'local[4]') \
                .config('spark.sql.adaptive.enabled', 'true') \
                .getOrCreate()
            
            # Load store_sales data (main table)
            data_path = f"/app/data/{scale}/store_sales.dat"
            if not os.path.exists(data_path):
                return False
                
            # Define schema for store_sales
            df = spark.read.csv(data_path, sep="|", header=False)
            
            # Rename columns to standard TPC-DS names
            columns = [
                'ss_sold_date_sk', 'ss_sold_time_sk', 'ss_item_sk', 'ss_customer_sk',
                'ss_cdemo_sk', 'ss_hdemo_sk', 'ss_addr_sk', 'ss_store_sk', 'ss_promo_sk',
                'ss_ticket_number', 'ss_quantity', 'ss_wholesale_cost', 'ss_list_price',
                'ss_sales_price', 'ss_ext_discount_amt', 'ss_ext_sales_price',
                'ss_ext_wholesale_cost', 'ss_ext_list_price', 'ss_ext_tax',
                'ss_coupon_amt', 'ss_net_paid', 'ss_net_paid_inc_tax', 'ss_net_profit'
            ]
            
            # Ensure we have the right number of columns
            actual_columns = len(df.columns)
            if actual_columns < len(columns):
                columns = columns[:actual_columns]
            
            # Rename columns
            for i, col_name in enumerate(columns):
                df = df.withColumnRenamed(f"_c{i}", col_name)
            
            # Create warehouse directory
            warehouse_dir = f"/app/output/warehouse-{scale}"
            os.makedirs(warehouse_dir, exist_ok=True)
            
            # Write as Iceberg table with specific format and compression
            table_name = f"store_sales_{format_type}_{compression}"
            table_path = f"{warehouse_dir}/{table_name}"
            
            writer = df.write.mode("overwrite")
            writer = writer.option("compression", compression)
            
            if format_type == "parquet":
                writer.format("parquet").save(table_path)
            elif format_type == "orc":
                writer.format("orc").save(table_path)
            elif format_type == "avro":
                writer.format("avro").save(table_path)
                
            spark.stop()
            return True
            
        except Exception as e:
            print(f"Table creation error: {e}")
            return False
    
    def run_queries(self, scale, format_type, compression):
        """Run benchmark queries and measure performance"""
        try:
            from pyspark.sql import SparkSession
            
            spark = SparkSession.builder \
                .appName(f'Query-{scale}-{format_type}-{compression}') \
                .config('spark.master', 'local[4]') \
                .getOrCreate()
            
            # Load table
            table_path = f"/app/output/warehouse-{scale}/store_sales_{format_type}_{compression}"
            df = spark.read.format(format_type).load(table_path)
            df.createOrReplaceTempView("store_sales")
            
            queries = [
                ("count", "SELECT COUNT(*) as total_rows FROM store_sales"),
                ("sum_sales", "SELECT SUM(ss_sales_price) as total_sales FROM store_sales"),
                ("avg_by_item", "SELECT ss_item_sk, AVG(ss_sales_price) as avg_price FROM store_sales GROUP BY ss_item_sk LIMIT 10"),
                ("top_sales", "SELECT ss_item_sk, SUM(ss_sales_price) as total FROM store_sales GROUP BY ss_item_sk ORDER BY total DESC LIMIT 5")
            ]
            
            query_results = {}
            for query_name, sql in queries:
                start = time.time()
                result = spark.sql(sql).collect()
                end = time.time()
                
                query_results[query_name] = {
                    'execution_time_seconds': round(end - start, 3),
                    'result_count': len(result),
                    'first_result': str(result[0]) if result else None
                }
            
            spark.stop()
            return query_results
            
        except Exception as e:
            print(f"Query execution error: {e}")
            return {'error': str(e)}
    
    def get_storage_metrics(self, scale, format_type, compression):
        """Get storage size and file metrics"""
        try:
            table_path = f"/app/output/warehouse-{scale}/store_sales_{format_type}_{compression}"
            
            if not os.path.exists(table_path):
                return {'error': 'Table path not found'}
            
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(table_path):
                for file in files:
                    if not file.startswith('.') and not file.startswith('_'):
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                        file_count += 1
            
            return {
                'total_size_bytes': total_size,
                'total_size_kb': round(total_size / 1024, 2),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'avg_file_size_kb': round((total_size / 1024) / file_count, 2) if file_count > 0 else 0
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def run_all_benchmarks(self):
        """Run benchmarks for all combinations"""
        print("🚀 Starting Iceberg Format Benchmark Suite")
        print("=" * 60)
        
        total_tests = len(self.scales) * len(self.formats) * len(self.compressions)
        test_count = 0
        
        for scale in self.scales:
            for format_type in self.formats:
                for compression in self.compressions:
                    test_count += 1
                    print(f"\n📊 Test {test_count}/{total_tests}")
                    
                    result = self.run_benchmark(scale, format_type, compression)
                    
                    if result:
                        key = f"{scale}_{format_type}_{compression}"
                        self.results[key] = result
        
        return self.results
    
    def analyze_results(self):
        """Analyze benchmark results and provide recommendations"""
        print("\n" + "=" * 60)
        print("📈 ANÁLISE DOS RESULTADOS")
        print("=" * 60)
        
        # Group by scale
        for scale in self.scales:
            scale_results = {k: v for k, v in self.results.items() if k.startswith(scale)}
            if not scale_results:
                continue
                
            print(f"\n🔍 Escala: {scale.upper()}")
            print("-" * 40)
            
            # Storage efficiency analysis
            storage_analysis = []
            performance_analysis = []
            
            for key, result in scale_results.items():
                if 'storage_metrics' in result and 'query_results' in result:
                    _, format_type, compression = key.split('_', 2)
                    
                    storage = result['storage_metrics']
                    queries = result['query_results']
                    
                    if 'total_size_kb' in storage:
                        storage_analysis.append({
                            'format': format_type,
                            'compression': compression,
                            'size_kb': storage['total_size_kb'],
                            'file_count': storage.get('file_count', 0)
                        })
                    
                    if 'count' in queries and 'execution_time_seconds' in queries['count']:
                        avg_query_time = sum(
                            q.get('execution_time_seconds', 0) 
                            for q in queries.values() 
                            if isinstance(q, dict) and 'execution_time_seconds' in q
                        ) / len([q for q in queries.values() if isinstance(q, dict)])
                        
                        performance_analysis.append({
                            'format': format_type,
                            'compression': compression,
                            'avg_query_time': avg_query_time
                        })
            
            # Best storage efficiency
            if storage_analysis:
                best_storage = min(storage_analysis, key=lambda x: x['size_kb'])
                print(f"💾 Melhor compressão: {best_storage['format']} + {best_storage['compression']}")
                print(f"   Tamanho: {best_storage['size_kb']} KB")
                
                print("\\n📊 Ranking de compressão:")
                for i, item in enumerate(sorted(storage_analysis, key=lambda x: x['size_kb'])[:5]):
                    print(f"   {i+1}. {item['format']} + {item['compression']}: {item['size_kb']} KB")
            
            # Best performance
            if performance_analysis:
                best_performance = min(performance_analysis, key=lambda x: x['avg_query_time'])
                print(f"\\n⚡ Melhor performance: {best_performance['format']} + {best_performance['compression']}")
                print(f"   Tempo médio: {best_performance['avg_query_time']:.3f}s")
                
                print("\\n🏃 Ranking de performance:")
                for i, item in enumerate(sorted(performance_analysis, key=lambda x: x['avg_query_time'])[:5]):
                    print(f"   {i+1}. {item['format']} + {item['compression']}: {item['avg_query_time']:.3f}s")
        
        # Overall recommendations
        print(f"\\n🎯 RECOMENDAÇÕES GERAIS")
        print("-" * 40)
        
        # Find best overall combinations
        all_results = []
        for key, result in self.results.items():
            if 'storage_metrics' in result and 'query_results' in result:
                scale, format_type, compression = key.split('_', 2)
                
                storage = result['storage_metrics']
                queries = result['query_results']
                
                if 'total_size_kb' in storage and queries:
                    avg_query_time = sum(
                        q.get('execution_time_seconds', 0) 
                        for q in queries.values() 
                        if isinstance(q, dict) and 'execution_time_seconds' in q
                    ) / len([q for q in queries.values() if isinstance(q, dict)])
                    
                    # Calculate efficiency score (lower is better)
                    # Normalize size and time, then combine
                    size_score = storage['total_size_kb']
                    time_score = avg_query_time * 1000  # Convert to ms for scoring
                    efficiency_score = size_score + time_score
                    
                    all_results.append({
                        'scale': scale,
                        'format': format_type,
                        'compression': compression,
                        'size_kb': storage['total_size_kb'],
                        'avg_query_time': avg_query_time,
                        'efficiency_score': efficiency_score
                    })
        
        if all_results:
            # Best overall efficiency
            best_overall = min(all_results, key=lambda x: x['efficiency_score'])
            print(f"🏆 Combinação mais eficiente: {best_overall['format']} + {best_overall['compression']}")
            print(f"   Tamanho: {best_overall['size_kb']} KB")
            print(f"   Performance: {best_overall['avg_query_time']:.3f}s")
            
            # Format recommendations
            format_scores = {}
            compression_scores = {}
            
            for result in all_results:
                format_type = result['format']
                compression = result['compression']
                score = result['efficiency_score']
                
                if format_type not in format_scores:
                    format_scores[format_type] = []
                format_scores[format_type].append(score)
                
                if compression not in compression_scores:
                    compression_scores[compression] = []
                compression_scores[compression].append(score)
            
            # Average scores
            format_avg = {f: sum(scores)/len(scores) for f, scores in format_scores.items()}
            compression_avg = {c: sum(scores)/len(scores) for c, scores in compression_scores.items()}
            
            best_format = min(format_avg, key=format_avg.get)
            best_compression = min(compression_avg, key=compression_avg.get)
            
            print(f"\\n📋 Recomendações por categoria:")
            print(f"   Melhor formato: {best_format}")
            print(f"   Melhor compressão: {best_compression}")
            
            print(f"\\n📊 Ranking de formatos:")
            for i, (fmt, score) in enumerate(sorted(format_avg.items(), key=lambda x: x[1])):
                print(f"   {i+1}. {fmt}: {score:.2f} pontos")
                
            print(f"\\n📊 Ranking de compressões:")
            for i, (comp, score) in enumerate(sorted(compression_avg.items(), key=lambda x: x[1])):
                print(f"   {i+1}. {comp}: {score:.2f} pontos")
    
    def save_results(self, filename):
        """Save results to JSON file"""
        os.makedirs("/app/metrics", exist_ok=True)
        filepath = f"/app/metrics/{filename}"
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\\n💾 Resultados salvos em: {filepath}")

if __name__ == "__main__":
    benchmark = IcebergFormatBenchmark()
    results = benchmark.run_all_benchmarks()
    benchmark.analyze_results()
    benchmark.save_results("format_benchmark_results.json")
