#!/usr/bin/env python3
"""
Teste corrigido de benchmark de formatos Iceberg
Corrige os problemas de scale factor e adiciona suporte ao Avro
"""

import os
import json
import time
from datetime import datetime

def main():
    print('🚀 BENCHMARK DE FORMATOS ICEBERG - VERSÃO CORRIGIDA')
    print('=' * 60)

    # Configurações de teste corrigidas
    scales = {
        'micro': {'factor': 0.001, 'rows': 100},
        'small': {'factor': 0.01, 'rows': 1000}, 
        'medium': {'factor': 0.1, 'rows': 10000},
        'large': {'factor': 1.0, 'rows': 100000}
    }

    formats = ['parquet', 'orc', 'avro']
    compressions = {
        'parquet': ['snappy', 'gzip', 'zstd'],
        'orc': ['snappy', 'zlib', 'zstd'],  # ORC não suporta gzip, usa zlib
        'avro': ['snappy', 'deflate']       # Avro suporta snappy e deflate
    }

    results = {}

    def generate_scalable_data(scale_name, scale_config):
        """Gerar dados que realmente escalem conforme o fator"""
        print(f'\n📊 Gerando dados para escala {scale_name} (fator {scale_config["factor"]}, {scale_config["rows"]} rows)')
        
        try:
            from pyspark.sql import SparkSession
            from pyspark.sql.functions import rand, col, expr, monotonically_increasing_id
            
            spark = SparkSession.builder \
                .appName(f'DataGen-{scale_name}') \
                .config('spark.master', 'local[2]') \
                .config('spark.sql.adaptive.enabled', 'true') \
                .getOrCreate()
            
            data_dir = f'/app/data/{scale_name}_corrected'
            os.makedirs(data_dir, exist_ok=True)
            
            # Gerar store_sales com número correto de rows
            num_rows = scale_config['rows']
            
            # Criar DataFrame com número correto de linhas
            df = spark.range(num_rows).select(
                col('id').alias('ss_sold_date_sk'),
                expr('cast(rand() * 1000000 as int)').alias('ss_sold_time_sk'),
                expr('cast(1 + rand() * 18000 as int)').alias('ss_item_sk'),
                expr('cast(1 + rand() * 100000 as int)').alias('ss_customer_sk'),
                expr('cast(1 + rand() * 1920800 as int)').alias('ss_cdemo_sk'),
                expr('cast(1 + rand() * 7200 as int)').alias('ss_hdemo_sk'),
                expr('cast(1 + rand() * 50000 as int)').alias('ss_addr_sk'),
                expr('cast(1 + rand() * 12 as int)').alias('ss_store_sk'),
                expr('cast(1 + rand() * 300 as int)').alias('ss_promo_sk'),
                expr('cast(rand() * 80000 as int)').alias('ss_ticket_number'),
                expr('cast(1 + rand() * 100 as int)').alias('ss_quantity'),
                expr('cast(rand() * 200.00 as decimal(7,2))').alias('ss_wholesale_cost'),
                expr('cast(rand() * 500.00 as decimal(7,2))').alias('ss_list_price'),
                expr('cast(rand() * 400.00 as decimal(7,2))').alias('ss_sales_price'),
                expr('cast(rand() * 50.00 as decimal(7,2))').alias('ss_ext_discount_amt'),
                expr('cast(rand() * 1000.00 as decimal(7,2))').alias('ss_ext_sales_price'),
                expr('cast(rand() * 800.00 as decimal(7,2))').alias('ss_ext_wholesale_cost'),
                expr('cast(rand() * 1200.00 as decimal(7,2))').alias('ss_ext_list_price'),
                expr('cast(rand() * 100.00 as decimal(7,2))').alias('ss_ext_tax'),
                expr('cast(rand() * 200.00 as decimal(7,2))').alias('ss_coupon_amt'),
                expr('cast(rand() * 1000.00 as decimal(7,2))').alias('ss_net_paid'),
                expr('cast(rand() * 1100.00 as decimal(7,2))').alias('ss_net_paid_inc_tax'),
                expr('cast(rand() * 300.00 as decimal(7,2))').alias('ss_net_profit')
            )
            
            # Salvar como CSV para usar nos testes
            df.coalesce(1).write \
                .mode('overwrite') \
                .option('header', 'false') \
                .option('delimiter', '|') \
                .csv(f'{data_dir}/store_sales_temp')
            
            # Mover arquivo para .dat
            import shutil
            csv_files = [f for f in os.listdir(f'{data_dir}/store_sales_temp') 
                        if f.endswith('.csv') and not f.startswith('_')]
            if csv_files:
                shutil.move(
                    f'{data_dir}/store_sales_temp/{csv_files[0]}',
                    f'{data_dir}/store_sales.dat'
                )
                shutil.rmtree(f'{data_dir}/store_sales_temp')
            
            spark.stop()
            
            # Verificar tamanho
            file_size = os.path.getsize(f'{data_dir}/store_sales.dat')
            actual_rows = sum(1 for line in open(f'{data_dir}/store_sales.dat'))
            
            print(f'   ✅ {actual_rows} rows geradas, {file_size/1024:.2f} KB')
            return True, file_size, actual_rows
            
        except Exception as e:
            print(f'   ❌ Erro: {e}')
            return False, 0, 0

    def test_format_performance_corrected(scale_name, format_type, compression):
        """Testar performance com suporte correto para todos os formatos"""
        print(f'\n🔬 Testando: {scale_name} | {format_type} | {compression}')
        
        try:
            from pyspark.sql import SparkSession
            
            # Configurar Spark com suporte para Avro
            spark_builder = SparkSession.builder \
                .appName(f'FormatTest-{scale_name}-{format_type}-{compression}') \
                .config('spark.master', 'local[2]') \
                .config('spark.sql.adaptive.enabled', 'true')
            
            # Adicionar Avro package se necessário
            if format_type == 'avro':
                spark_builder = spark_builder.config(
                    'spark.jars.packages', 
                    'org.apache.spark:spark-avro_2.12:3.4.2'
                )
            
            spark = spark_builder.getOrCreate()
            
            # Carregar dados
            data_path = f'/app/data/{scale_name}_corrected/store_sales.dat'
            if not os.path.exists(data_path):
                print('   ❌ Dados não encontrados')
                spark.stop()
                return None
            
            # Ler dados
            start_read = time.time()
            df = spark.read.csv(data_path, sep='|', header=False)
            row_count = df.count()
            end_read = time.time()
            read_time = end_read - start_read
            
            # Salvar em formato específico
            output_dir = f'/app/output/{scale_name}_corrected/{format_type}_{compression}'
            os.makedirs(output_dir, exist_ok=True)
            
            start_write = time.time()
            writer = df.write.mode('overwrite')
            
            # Configurar compressão específica por formato
            if format_type == 'parquet':
                writer = writer.option('compression', compression)
                writer.format('parquet').save(output_dir)
            elif format_type == 'orc':
                writer = writer.option('compression', compression)
                writer.format('orc').save(output_dir)
            elif format_type == 'avro':
                writer = writer.option('compression', compression)
                writer.format('avro').save(output_dir)
            
            end_write = time.time()
            write_time = end_write - start_write
            
            # Medir tamanho do arquivo
            total_size = 0
            file_count = 0
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if not file.startswith('.') and not file.startswith('_'):
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                        file_count += 1
            
            # Testar leitura do formato
            start_read_formatted = time.time()
            df_formatted = spark.read.format(format_type).load(output_dir)
            formatted_count = df_formatted.count()
            end_read_formatted = time.time()
            read_formatted_time = end_read_formatted - start_read_formatted
            
            # Executar query simples
            df_formatted.createOrReplaceTempView('test_table')
            start_query = time.time()
            result = spark.sql('SELECT COUNT(*), SUM(_c13) FROM test_table').collect()
            end_query = time.time()
            query_time = end_query - start_query
            
            spark.stop()
            
            metrics = {
                'scale': scale_name,
                'format': format_type,
                'compression': compression,
                'row_count': row_count,
                'read_time_seconds': round(read_time, 3),
                'write_time_seconds': round(write_time, 3),
                'read_formatted_time_seconds': round(read_formatted_time, 3),
                'query_time_seconds': round(query_time, 3),
                'file_size_bytes': total_size,
                'file_size_kb': round(total_size / 1024, 2),
                'file_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'compression_ratio': round(total_size / (row_count * 100), 3) if row_count > 0 else 0,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f'   ✅ {row_count} rows | {metrics["file_size_kb"]} KB | Write: {write_time:.3f}s | Query: {query_time:.3f}s')
            return metrics
            
        except Exception as e:
            print(f'   ❌ Erro: {e}')
            import traceback
            traceback.print_exc()
            return {'error': str(e), 'scale': scale_name, 'format': format_type, 'compression': compression}

    # Executar testes
    print('\n🔄 Iniciando geração de dados corrigida...')

    # Gerar dados para cada escala
    data_info = {}
    for scale_name, scale_config in scales.items():
        success, size, count = generate_scalable_data(scale_name, scale_config)
        data_info[scale_name] = {'success': success, 'size': size, 'count': count, 'config': scale_config}

    print('\n🔄 Iniciando testes de formato corrigidos...')

    # Testar combinações formato+compressão
    test_count = 0
    total_tests = sum(len(scales) * len(compressions[fmt]) for fmt in formats)

    for scale_name in scales.keys():
        if not data_info[scale_name]['success']:
            continue
            
        for format_type in formats:
            for compression in compressions[format_type]:
                test_count += 1
                print(f'\n📊 Teste {test_count}/{total_tests}')
                
                result = test_format_performance_corrected(scale_name, format_type, compression)
                if result:
                    key = f'{scale_name}_{format_type}_{compression}'
                    results[key] = result

    # Análise dos resultados
    print('\n' + '=' * 60)
    print('📈 ANÁLISE DOS RESULTADOS CORRIGIDOS')
    print('=' * 60)

    if results:
        # Análise por escala
        for scale_name in scales.keys():
            scale_results = {k: v for k, v in results.items() if k.startswith(scale_name) and 'error' not in v}
            
            if scale_results:
                print(f'\n🔍 ESCALA: {scale_name.upper()} ({scales[scale_name]["rows"]} rows)')
                print('-' * 50)
                
                # Top 3 por compressão
                size_ranking = sorted(scale_results.values(), key=lambda x: x.get('file_size_kb', float('inf')))
                print('💾 Top 3 compressão (menor = melhor):')
                for i, result in enumerate(size_ranking[:3]):
                    format_compression = f"{result['format']} + {result['compression']}"
                    size_kb = result.get('file_size_kb', 0)
                    print(f'   {i+1}. {format_compression:<20} | {size_kb:>8.2f} KB')
                
                # Top 3 por performance
                perf_ranking = sorted(scale_results.values(), key=lambda x: x.get('query_time_seconds', float('inf')))
                print('\n⚡ Top 3 performance (menor = melhor):')
                for i, result in enumerate(perf_ranking[:3]):
                    format_compression = f"{result['format']} + {result['compression']}"
                    query_time = result.get('query_time_seconds', 0)
                    print(f'   {i+1}. {format_compression:<20} | {query_time:.3f}s')

        # Análise geral por formato
        print(f'\n🎯 ANÁLISE GERAL')
        print('-' * 40)
        
        format_stats = {}
        compression_stats = {}
        
        for result in results.values():
            if 'error' in result:
                continue
                
            format_type = result['format']
            compression = result['compression']
            size = result.get('file_size_kb', 0)
            query_time = result.get('query_time_seconds', 0)
            
            if format_type not in format_stats:
                format_stats[format_type] = {'sizes': [], 'times': []}
            format_stats[format_type]['sizes'].append(size)
            format_stats[format_type]['times'].append(query_time)
            
            comp_key = f"{format_type}_{compression}"
            if comp_key not in compression_stats:
                compression_stats[comp_key] = {'sizes': [], 'times': []}
            compression_stats[comp_key]['sizes'].append(size)
            compression_stats[comp_key]['times'].append(query_time)
        
        # Médias por formato
        print('\n📊 FORMATO (médias):')
        for format_type, stats in format_stats.items():
            avg_size = sum(stats['sizes']) / len(stats['sizes'])
            avg_time = sum(stats['times']) / len(stats['times'])
            print(f'   {format_type.upper():<8} | Tamanho: {avg_size:>8.2f} KB | Tempo: {avg_time:.3f}s')
        
        # Encontrar o melhor geral
        valid_results = [r for r in results.values() if 'error' not in r]
        if valid_results:
            best_overall = min(valid_results, 
                              key=lambda x: (x.get('file_size_kb', float('inf')) / 100 + 
                                           x.get('query_time_seconds', float('inf')) * 1000))
            
            print(f'\n🏆 MELHOR COMBINAÇÃO GERAL:')
            print(f'   Formato: {best_overall["format"].upper()}')
            print(f'   Compressão: {best_overall["compression"].upper()}')
            print(f'   Escala: {best_overall["scale"]}')
            print(f'   Tamanho: {best_overall.get("file_size_kb", 0)} KB')
            print(f'   Performance: {best_overall.get("query_time_seconds", 0):.3f}s')
    
    else:
        print('❌ Nenhum resultado válido obtido')

    # Salvar resultados
    results_file = '/app/metrics/format_comparison_corrected.json'
    os.makedirs('/app/metrics', exist_ok=True)

    final_results = {
        'test_summary': {
            'scales_tested': list(scales.keys()),
            'scale_configs': scales,
            'formats_tested': formats,
            'compressions_tested': compressions,
            'total_tests': len(results),
            'successful_tests': len([r for r in results.values() if 'error' not in r]),
            'timestamp': datetime.now().isoformat()
        },
        'data_generation': data_info,
        'test_results': results
    }

    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2)

    print(f'\n💾 Resultados salvos em: {results_file}')
    print('\n🎉 Benchmark corrigido concluído!')

if __name__ == '__main__':
    main()
