"""
Main benchmark class for Iceberg TPC-DS benchmark.

This module contains the core benchmark logic for testing Apache Iceberg
with different formats, compressions, and partitioning strategies.
"""

import os
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType

from .config import BenchmarkConfig
from .metrics import MetricsCollector, QueryResult
from .utils import setup_logging, Timer, run_command, format_duration


class TpcdsDataGenerator:
    """Generates TPC-DS data using the TPC-DS toolkit."""
    
    def __init__(self, spark_home: str = "/opt/spark"):
        """Initialize benchmark with Spark home (TPC-DS data generation is now Spark-based)."""
        self.spark_home = spark_home
        self.logger = setup_logging()
        
        # Note: No validation needed as TPC-DS generation is now Spark-based
    
    def generate_data(self, scale_factor: float, output_dir: str) -> bool:
        """Generate TPC-DS data at specified scale factor using Spark."""
        from .utils import generate_tpcds_data
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Generating TPC-DS data with scale factor {scale_factor}")
        
        with Timer(f"TPC-DS data generation (scale {scale_factor})"):
            # Generate data using the utility function
            success = generate_tpcds_data(scale_factor, str(output_path))
            
            if not success:
                self.logger.error("Failed to generate TPC-DS data")
                return False
            
            # Verify data files were created
            data_files = list(output_path.glob("*.dat"))
            if not data_files:
                self.logger.error("No .dat files found after generation")
                return False
            
            self.logger.info(f"Successfully generated {len(data_files)} data files")
            return True
            
            if not result['success']:
                self.logger.error(f"Data generation failed: {result['stderr']}")
                return False
        
        # Verify generated files
        expected_tables = [
            'call_center.dat', 'catalog_page.dat', 'catalog_returns.dat',
            'catalog_sales.dat', 'customer.dat', 'customer_address.dat',
            'customer_demographics.dat', 'date_dim.dat', 'household_demographics.dat',
            'income_band.dat', 'inventory.dat', 'item.dat', 'promotion.dat',
            'reason.dat', 'ship_mode.dat', 'store.dat', 'store_returns.dat',
            'store_sales.dat', 'time_dim.dat', 'warehouse.dat', 'web_page.dat',
            'web_returns.dat', 'web_sales.dat', 'web_site.dat'
        ]
        
        missing_files = []
        for table_file in expected_tables:
            if not (output_path / table_file).exists():
                missing_files.append(table_file)
        
        if missing_files:
            self.logger.warning(f"Missing data files: {missing_files}")
        
        self.logger.info(f"TPC-DS data generated successfully in {output_path}")
        return True


class IcebergTableManager:
    """Manages Iceberg table operations."""
    
    def __init__(self, spark: SparkSession, warehouse_path: str = "/tmp/iceberg-warehouse"):
        self.spark = spark
        self.warehouse_path = warehouse_path
        self.logger = setup_logging()
        
        # Ensure warehouse directory exists
        Path(warehouse_path).mkdir(parents=True, exist_ok=True)
    
    def create_table_from_data(self, table_name: str, data_path: str, 
                              format_type: str = "parquet", 
                              compression: str = "snappy",
                              partitioning: Optional[Dict[str, Any]] = None) -> bool:
        """Create Iceberg table from TPC-DS data files."""
        try:
            self.logger.info(f"Creating table {table_name} with format {format_type}")
            
            # Read data file (assuming CSV format from TPC-DS)
            data_file = Path(data_path) / f"{table_name}.dat"
            
            if not data_file.exists():
                self.logger.error(f"Data file not found: {data_file}")
                return False
            
            # Read CSV data
            df = self.spark.read.option("header", "false").option("delimiter", "|").csv(str(data_file))
            
            # Get schema based on table name (simplified for demo)
            schema = self._get_table_schema(table_name)
            if schema:
                # Apply schema if available
                for i, field in enumerate(schema.fields):
                    if i < len(df.columns):
                        df = df.withColumnRenamed(f"_c{i}", field.name)
            
            # Set up table options
            table_options = {
                "format": format_type,
                "compression": compression,
            }
            
            # Configure partitioning
            partition_by = None
            if partitioning and partitioning.get("type") != "none":
                if partitioning["type"] == "date":
                    partition_by = partitioning.get("columns", [])
                elif partitioning["type"] == "hash":
                    # For hash partitioning, we'll use bucket() function
                    pass
            
            # Create table path
            table_path = f"{self.warehouse_path}/{table_name}"
            
            # Write as Iceberg table
            writer = df.write.format("iceberg").mode("overwrite")
            
            # Apply options
            for key, value in table_options.items():
                writer = writer.option(key, value)
            
            # Apply partitioning
            if partition_by:
                writer = writer.partitionBy(*partition_by)
            
            # Save table
            writer.option("path", table_path).saveAsTable(f"local.{table_name}")
            
            self.logger.info(f"Table {table_name} created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create table {table_name}: {str(e)}")
            return False
    
    def _get_table_schema(self, table_name: str) -> Optional[StructType]:
        """Get schema for TPC-DS table (simplified version)."""
        # This is a simplified schema mapping
        # In production, you would have complete schema definitions
        schemas = {
            "store_sales": ["ss_sold_date_sk", "ss_sold_time_sk", "ss_item_sk", 
                           "ss_customer_sk", "ss_cdemo_sk", "ss_hdemo_sk",
                           "ss_addr_sk", "ss_store_sk", "ss_promo_sk",
                           "ss_ticket_number", "ss_quantity", "ss_wholesale_cost",
                           "ss_list_price", "ss_sales_price", "ss_ext_discount_amt",
                           "ss_ext_sales_price", "ss_ext_wholesale_cost",
                           "ss_ext_list_price", "ss_ext_tax", "ss_coupon_amt",
                           "ss_net_paid", "ss_net_paid_inc_tax", "ss_net_profit"],
            "date_dim": ["d_date_sk", "d_date_id", "d_date", "d_month_seq",
                        "d_week_seq", "d_quarter_seq", "d_year", "d_dow",
                        "d_moy", "d_dom", "d_qoy", "d_fy_year", "d_fy_quarter_seq",
                        "d_fy_week_seq", "d_day_name", "d_quarter_name",
                        "d_holiday", "d_weekend", "d_following_holiday",
                        "d_first_dom", "d_last_dom", "d_same_day_ly",
                        "d_same_day_lq", "d_current_day", "d_current_week",
                        "d_current_month", "d_current_quarter", "d_current_year"],
        }
        
        # Return None for now - in production you'd create proper StructType schemas
        return None


class QueryEngine:
    """Executes TPC-DS queries against Iceberg tables."""
    
    def __init__(self, spark: SparkSession, queries_dir: str = "/app/queries"):
        self.spark = spark
        self.queries_dir = Path(queries_dir)
        self.logger = setup_logging()
    
    def load_query(self, query_name: str) -> Optional[str]:
        """Load SQL query from file."""
        query_file = self.queries_dir / f"{query_name}.sql"
        
        if not query_file.exists():
            self.logger.error(f"Query file not found: {query_file}")
            return None
        
        try:
            with open(query_file, 'r') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to load query {query_name}: {str(e)}")
            return None
    
    def execute_query(self, query_name: str, query_sql: str) -> Tuple[bool, Dict[str, Any]]:
        """Execute a single query and collect metrics."""
        start_time = time.time()
        
        try:
            # Execute query
            self.logger.info(f"Executing query: {query_name}")
            
            # Get query execution plan for metrics
            df = self.spark.sql(query_sql)
            
            # Trigger execution and collect results
            results = df.collect()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Collect metrics from Spark
            metrics = self._collect_spark_metrics()
            
            result_metrics = {
                'execution_time': execution_time,
                'rows_returned': len(results),
                'spark_metrics': metrics,
            }
            
            self.logger.info(f"Query {query_name} completed in {format_duration(execution_time)}")
            return True, result_metrics
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            error_msg = str(e)
            self.logger.error(f"Query {query_name} failed after {format_duration(execution_time)}: {error_msg}")
            
            return False, {
                'execution_time': execution_time,
                'error': error_msg,
            }
    
    def _collect_spark_metrics(self) -> Dict[str, Any]:
        """Collect metrics from Spark execution."""
        # This would collect detailed Spark metrics
        # For now, return basic metrics
        return {
            'rows_read': 0,
            'bytes_read': 0,
            'rows_written': 0,
            'bytes_written': 0,
            'shuffle_read': 0,
            'shuffle_write': 0,
        }


class IcebergBenchmark:
    """Main benchmark class for Iceberg performance testing."""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.logger = setup_logging()
        self.metrics_collector = MetricsCollector(
            output_dir=config.output.results_dir,
            interval=config.monitoring.metrics_interval
        )
        
        # Initialize components
        self.spark: Optional[SparkSession] = None
        self.data_generator: Optional[TpcdsDataGenerator] = None
        self.table_manager: Optional[IcebergTableManager] = None
        self.query_engine: Optional[QueryEngine] = None
        
        # Data directory
        self.data_dir = "/data/tpcds"
        
    def setup(self) -> bool:
        """Setup benchmark environment."""
        self.logger.info("Setting up Iceberg benchmark")
        
        try:
            # Initialize Spark session
            self._initialize_spark()
            
            # Initialize components
            self.data_generator = TpcdsDataGenerator()
            self.table_manager = IcebergTableManager(self.spark)
            self.query_engine = QueryEngine(self.spark)
            
            self.logger.info("Benchmark setup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Benchmark setup failed: {str(e)}")
            return False
    
    def _initialize_spark(self) -> None:
        """Initialize Spark session with Iceberg configuration."""
        self.logger.info("Initializing Spark session")
        
        # Get Spark configuration
        spark_conf = self.config.get_spark_conf()
        
        # Create Spark session builder
        builder = SparkSession.builder.appName("IcebergBenchmark")
        
        # Apply configuration
        for key, value in spark_conf.items():
            builder = builder.config(key, value)
        
        # Create session
        self.spark = builder.getOrCreate()
        
        # Set log level
        self.spark.sparkContext.setLogLevel("WARN")
        
        self.logger.info("Spark session initialized")
    
    def generate_data(self) -> bool:
        """Generate TPC-DS data."""
        if not self.data_generator:
            self.logger.error("Data generator not initialized")
            return False
        
        return self.data_generator.generate_data(
            scale_factor=self.config.tpcds.scale_factor,
            output_dir=self.data_dir
        )
    
    def create_tables(self) -> bool:
        """Create Iceberg tables from generated data."""
        if not self.table_manager:
            self.logger.error("Table manager not initialized")
            return False
        
        self.logger.info("Creating Iceberg tables")
        
        # Key tables for TPC-DS
        tables = ["store_sales", "date_dim", "item", "customer", "store"]
        
        success_count = 0
        
        for table_name in tables:
            for format_type in self.config.iceberg.formats:
                for compression in self.config.iceberg.compressions:
                    for partitioning in self.config.iceberg.partitioning:
                        table_full_name = f"{table_name}_{format_type}_{compression}"
                        
                        if self.table_manager.create_table_from_data(
                            table_full_name, self.data_dir, format_type, compression, partitioning
                        ):
                            success_count += 1
        
        self.logger.info(f"Created {success_count} tables")
        return success_count > 0
    
    def run_queries(self) -> bool:
        """Run TPC-DS queries against all table configurations."""
        if not self.query_engine:
            self.logger.error("Query engine not initialized")
            return False
        
        self.logger.info("Running benchmark queries")
        
        # Start metrics collection
        if self.config.monitoring.enabled:
            self.metrics_collector.start_collection()
        
        total_queries = 0
        successful_queries = 0
        
        try:
            # Run queries for each configuration
            for format_type in self.config.iceberg.formats:
                for compression in self.config.iceberg.compressions:
                    for partitioning in self.config.iceberg.partitioning:
                        partition_str = partitioning.get("type", "none")
                        
                        for query_name in self.config.tpcds.queries:
                            total_queries += 1
                            
                            # Load query
                            query_sql = self.query_engine.load_query(query_name)
                            if not query_sql:
                                continue
                            
                            # Execute query
                            success, metrics = self.query_engine.execute_query(query_name, query_sql)
                            
                            if success:
                                successful_queries += 1
                                
                                # Create query result
                                result = QueryResult(
                                    query_name=query_name,
                                    format=format_type,
                                    compression=compression,
                                    partitioning=partition_str,
                                    execution_time=metrics['execution_time'],
                                    rows_read=metrics['spark_metrics']['rows_read'],
                                    bytes_read=metrics['spark_metrics']['bytes_read'],
                                    rows_written=metrics['spark_metrics']['rows_written'],
                                    bytes_written=metrics['spark_metrics']['bytes_written'],
                                    shuffle_read=metrics['spark_metrics']['shuffle_read'],
                                    shuffle_write=metrics['spark_metrics']['shuffle_write'],
                                )
                            else:
                                # Create failed result
                                result = QueryResult(
                                    query_name=query_name,
                                    format=format_type,
                                    compression=compression,
                                    partitioning=partition_str,
                                    execution_time=metrics['execution_time'],
                                    rows_read=0,
                                    bytes_read=0,
                                    rows_written=0,
                                    bytes_written=0,
                                    error=metrics.get('error', 'Unknown error'),
                                )
                            
                            self.metrics_collector.add_query_result(result)
        
        finally:
            # Stop metrics collection
            if self.config.monitoring.enabled:
                self.metrics_collector.stop_collection()
        
        self.logger.info(f"Benchmark completed: {successful_queries}/{total_queries} queries successful")
        return successful_queries > 0
    
    def save_results(self) -> Dict[str, str]:
        """Save benchmark results."""
        self.logger.info("Saving benchmark results")
        
        files_saved = self.metrics_collector.save_results(
            filename_prefix=f"iceberg_benchmark_{self.config.name}"
        )
        
        # Generate and save report
        report = self.metrics_collector.generate_report()
        report_file = Path(self.config.output.results_dir) / f"report_{self.metrics_collector.get_summary()['benchmark_info']['timestamp']}.txt"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        files_saved['report'] = str(report_file)
        
        self.logger.info(f"Results saved: {list(files_saved.keys())}")
        return files_saved
    
    def run(self) -> bool:
        """Run the complete benchmark."""
        self.logger.info(f"Starting Iceberg benchmark: {self.config.name}")
        
        try:
            # Setup
            if not self.setup():
                return False
            
            # Generate data
            with Timer("Data generation"):
                if not self.generate_data():
                    return False
            
            # Create tables
            with Timer("Table creation"):
                if not self.create_tables():
                    return False
            
            # Run queries
            with Timer("Query execution"):
                if not self.run_queries():
                    return False
            
            # Save results
            with Timer("Results saving"):
                self.save_results()
            
            self.logger.info("Benchmark completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Benchmark failed: {str(e)}")
            return False
        
        finally:
            # Cleanup
            if self.spark:
                self.spark.stop()


if __name__ == "__main__":
    # Simple test
    from .config import get_default_config
    
    config = get_default_config()
    benchmark = IcebergBenchmark(config)
    
    print(f"Benchmark initialized for: {config.name}")
    print(f"TPC-DS scale factor: {config.tpcds.scale_factor}")
    print(f"Formats: {config.iceberg.formats}")
    print(f"Compressions: {config.iceberg.compressions}")
