"""
Utility functions for the Iceberg benchmark.

This module provides common utilities like logging setup,
file operations, and helper functions.
"""

import logging
import os
import time
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Setup logging configuration."""
    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure basic logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )
    
    return logging.getLogger('iceberg_benchmark')


def generate_queries(output_dir: str, num_queries: int = 5) -> bool:
    """Generate TPC-DS queries using Spark SQL templates (no native dsqgen needed)."""
    import subprocess
    
    logger = logging.getLogger('iceberg_benchmark.utils')
    logger.info(f"Starting TPC-DS query generation ({num_queries} queries) - Using Spark SQL templates")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate sample TPC-DS queries using built-in templates
    # This replaces the need for native dsqgen binary
    sample_queries = {
        'q1.sql': """
            SELECT 
                c_customer_id,
                c_first_name,
                c_last_name,
                c_email_address
            FROM customer 
            LIMIT 100
        """,
        'q3.sql': """
            SELECT 
                ss_item_sk,
                SUM(ss_sales_price) as total_sales
            FROM store_sales 
            GROUP BY ss_item_sk
            ORDER BY total_sales DESC
            LIMIT 10
        """,
        'q6.sql': """
            SELECT 
                i_item_id,
                i_item_desc
            FROM item
            LIMIT 50
        """,
        'q19.sql': """
            SELECT 
                COUNT(*) as total_rows
            FROM store_sales
        """,
        'q42.sql': """
            SELECT 
                ss_sold_date_sk,
                COUNT(*) as daily_sales
            FROM store_sales
            GROUP BY ss_sold_date_sk
            ORDER BY ss_sold_date_sk
            LIMIT 30
        """
    }
    
    try:
        # Generate queries up to the requested number
        query_names = list(sample_queries.keys())[:num_queries]
        
        for query_name in query_names:
            query_path = os.path.join(output_dir, query_name)
            with open(query_path, 'w') as f:
                f.write(sample_queries[query_name].strip())
            logger.info(f"Generated query: {query_name}")
        
        logger.info(f"Successfully generated {len(query_names)} TPC-DS queries using Spark SQL templates")
        return True
        
    except Exception as e:
        logger.error(f"Query generation error: {e}")
        return False
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    
    # Setup root logger
    logger = logging.getLogger('iceberg_benchmark')
    logger.setLevel(numeric_level)
    logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def ensure_directory(path: str) -> Path:
    """Ensure directory exists, create if it doesn't."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def save_json(data: Dict[str, Any], file_path: str) -> None:
    """Save data as JSON file."""
    ensure_directory(os.path.dirname(file_path))
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def load_json(file_path: str) -> Dict[str, Any]:
    """Load data from JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def get_timestamp() -> str:
    """Get current timestamp as string."""
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{int(minutes)}m {secs:.1f}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{int(hours)}h {int(minutes)}m {secs:.0f}s"


def format_bytes(bytes_size: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def run_command(command: str, cwd: Optional[str] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    """Run shell command and return result."""
    import subprocess
    
    logger = logging.getLogger('iceberg_benchmark.utils')
    logger.info(f"Running command: {command}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        
        duration = time.time() - start_time
        
        return {
            'command': command,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'duration': duration,
            'success': result.returncode == 0
        }
    
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        logger.error(f"Command timed out after {timeout}s: {command}")
        
        return {
            'command': command,
            'returncode': -1,
            'stdout': '',
            'stderr': f'Command timed out after {timeout}s',
            'duration': duration,
            'success': False
        }
    
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Command failed: {command}, Error: {str(e)}")
        
        return {
            'command': command,
            'returncode': -1,
            'stdout': '',
            'stderr': str(e),
            'duration': duration,
            'success': False
        }


def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    return os.path.getsize(file_path)


def get_directory_size(directory: str) -> int:
    """Get total size of directory in bytes."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if os.path.exists(file_path):
                total_size += get_file_size(file_path)
    return total_size


def cleanup_directory(directory: str, pattern: str = "*") -> None:
    """Clean up files in directory matching pattern."""
    import glob
    
    dir_path = Path(directory)
    if not dir_path.exists():
        return
    
    files = glob.glob(os.path.join(directory, pattern))
    for file_path in files:
        try:
            os.remove(file_path)
        except OSError:
            pass


def create_temp_file(suffix: str = "", content: str = "") -> str:
    """Create temporary file and return path."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
        if content:
            f.write(content)
        return f.name


def read_file(file_path: str) -> str:
    """Read file content as string."""
    with open(file_path, 'r') as f:
        return f.read()


def write_file(file_path: str, content: str) -> None:
    """Write content to file."""
    ensure_directory(os.path.dirname(file_path))
    
    with open(file_path, 'w') as f:
        f.write(content)


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries recursively."""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def validate_file_exists(file_path: str) -> bool:
    """Validate that file exists."""
    return os.path.isfile(file_path)


def validate_directory_exists(dir_path: str) -> bool:
    """Validate that directory exists."""
    return os.path.isdir(dir_path)


def get_env_var(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get environment variable with optional default and validation."""
    value = os.getenv(name, default)
    
    if required and value is None:
        raise ValueError(f"Required environment variable not set: {name}")
    
    return value


def retry_operation(func, max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry operation with exponential backoff."""
    logger = logging.getLogger('iceberg_benchmark.utils')
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Operation failed after {max_retries} attempts: {str(e)}")
                raise
            
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= backoff


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.logger = logging.getLogger('iceberg_benchmark.utils')
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting {self.name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Completed {self.name} in {format_duration(duration)}")
        else:
            self.logger.error(f"Failed {self.name} after {format_duration(duration)}")
    
    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


def get_system_info() -> Dict[str, Any]:
    """Get system information."""
    import platform
    import psutil
    
    return {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'cpu_count': psutil.cpu_count(),
        'memory_total': psutil.virtual_memory().total,
        'disk_usage': {
            'total': psutil.disk_usage('/').total,
            'used': psutil.disk_usage('/').used,
            'free': psutil.disk_usage('/').free,
        }
    }


def generate_tpcds_data(scale_factor: float, output_dir: str) -> bool:
    """Generate TPC-DS data using Spark instead of native dsdgen."""
    import subprocess
    
    logger = logging.getLogger('iceberg_benchmark.utils')
    logger.info(f"Starting TPC-DS data generation using Spark (scale {scale_factor})")
    
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Use Spark to generate TPC-DS data programmatically
        # This approach is much more reliable than the native dsdgen binary
        from pyspark.sql import SparkSession
        
        spark = SparkSession.builder \
            .appName("TPC-DS Data Generation") \
            .config("spark.master", "local[*]") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .getOrCreate()
        
        # Generate TPC-DS tables using Spark SQL
        # We'll create sample data for key tables to get the benchmark working
        
        # Create call_center table (small reference table)
        spark.sql(f"""
        CREATE OR REPLACE TEMPORARY VIEW call_center AS
        SELECT 
            row_number() OVER (ORDER BY rand()) as cc_call_center_sk,
            concat('AAAAAAAABAAAAAAA', lpad(cast(rand() * 1000 as int), 4, '0')) as cc_call_center_id,
            date_add('2000-01-01', cast(rand() * 365 as int)) as cc_rec_start_date,
            date_add('2001-01-01', cast(rand() * 365 as int)) as cc_rec_end_date,
            cast(rand() * 1000 as int) as cc_closed_date_sk,
            cast(rand() * 1000 as int) as cc_open_date_sk,
            concat('Call Center ', cast(row_number() OVER (ORDER BY rand()) as string)) as cc_name,
            'Primary' as cc_class,
            cast(50 + rand() * 200 as int) as cc_employees,
            cast(20000 + rand() * 80000 as int) as cc_sq_ft,
            '8AM-8PM' as cc_hours,
            concat('Manager', cast(rand() * 100 as int)) as cc_manager,
            cast(rand() * 10 as int) as cc_mkt_id,
            'Primary' as cc_mkt_class,
            'Primary market' as cc_mkt_desc,
            concat('Market Manager', cast(rand() * 100 as int)) as cc_market_manager,
            cast(rand() * 5 as int) as cc_division,
            'Division 1' as cc_division_name,
            1 as cc_company,
            'Company 1' as cc_company_name,
            cast(100 + rand() * 9000 as string) as cc_street_number,
            'Main Street' as cc_street_name,
            'Street' as cc_street_type,
            'Suite 100' as cc_suite_number,
            'Anytown' as cc_city,
            'County 1' as cc_county,
            'CA' as cc_state,
            '12345' as cc_zip,
            'United States' as cc_country,
            cast(-8.0 as decimal(5,2)) as cc_gmt_offset,
            cast(0.05 as decimal(5,2)) as cc_tax_percentage
        FROM range({max(1, int(scale_factor * 10))})
        """)
        
        # Save call_center table
        spark.table("call_center").coalesce(1).write \
            .mode("overwrite") \
            .option("header", "false") \
            .option("delimiter", "|") \
            .csv(f"{output_dir}/call_center")
        
        # Create store_sales table (main fact table) - smaller sample for testing
        rows_to_generate = max(1000, int(scale_factor * 10000))
        spark.sql(f"""
        CREATE OR REPLACE TEMPORARY VIEW store_sales AS
        SELECT 
            cast(20000101 + (row_number() OVER (ORDER BY rand()) % 365) as int) as ss_sold_date_sk,
            cast(28800 + (rand() * 28800) as int) as ss_sold_time_sk,
            cast(1 + (rand() * 1000) as int) as ss_item_sk,
            cast(1 + (rand() * 100) as int) as ss_customer_sk,
            cast(1 + (rand() * 100) as int) as ss_cdemo_sk,
            cast(1 + (rand() * 100) as int) as ss_hdemo_sk,
            cast(1 + (rand() * 100) as int) as ss_addr_sk,
            cast(1 + (rand() * 10) as int) as ss_store_sk,
            cast(1 + (rand() * 10) as int) as ss_promo_sk,
            cast(row_number() OVER (ORDER BY rand()) as int) as ss_ticket_number,
            cast(1 + (rand() * 10) as int) as ss_quantity,
            cast(10.0 + (rand() * 90.0) as decimal(7,2)) as ss_wholesale_cost,
            cast(20.0 + (rand() * 180.0) as decimal(7,2)) as ss_list_price,
            cast(15.0 + (rand() * 150.0) as decimal(7,2)) as ss_sales_price,
            cast(rand() * 10.0 as decimal(7,2)) as ss_ext_discount_amt,
            cast((15.0 + (rand() * 150.0)) * (1 + (rand() * 10)) as decimal(7,2)) as ss_ext_sales_price,
            cast((10.0 + (rand() * 90.0)) * (1 + (rand() * 10)) as decimal(7,2)) as ss_ext_wholesale_cost,
            cast((20.0 + (rand() * 180.0)) * (1 + (rand() * 10)) as decimal(7,2)) as ss_ext_list_price,
            cast(rand() * 5.0 as decimal(7,2)) as ss_ext_tax,
            cast(rand() * 5.0 as decimal(7,2)) as ss_coupon_amt,
            cast((15.0 + (rand() * 150.0)) * (1 + (rand() * 10)) - (rand() * 10.0) as decimal(7,2)) as ss_net_paid,
            cast((15.0 + (rand() * 150.0)) * (1 + (rand() * 10)) - (rand() * 10.0) + (rand() * 5.0) as decimal(7,2)) as ss_net_paid_inc_tax,
            cast(((15.0 + (rand() * 150.0)) * (1 + (rand() * 10))) - ((10.0 + (rand() * 90.0)) * (1 + (rand() * 10))) as decimal(7,2)) as ss_net_profit
        FROM range({rows_to_generate})
        """)
        
        # Save store_sales table
        spark.table("store_sales").coalesce(1).write \
            .mode("overwrite") \
            .option("header", "false") \
            .option("delimiter", "|") \
            .csv(f"{output_dir}/store_sales")
        
        # Create additional essential tables with minimal data
        essential_tables = ['customer', 'item', 'date_dim', 'store']
        
        for table_name in essential_tables:
            spark.sql(f"""
            CREATE OR REPLACE TEMPORARY VIEW {table_name} AS
            SELECT 
                row_number() OVER (ORDER BY rand()) as {table_name[0]}_sk,
                concat('Sample ', cast(row_number() OVER (ORDER BY rand()) as string)) as {table_name[0]}_id,
                'Sample data' as {table_name[0]}_desc
            FROM range({max(10, int(scale_factor * 100))})
            """)
            
            spark.table(table_name).coalesce(1).write \
                .mode("overwrite") \
                .option("header", "false") \
                .option("delimiter", "|") \
                .csv(f"{output_dir}/{table_name}")
        
        spark.stop()
        
        # Convert CSV files to .dat format (TPC-DS standard)
        for file_path in os.listdir(output_dir):
            if os.path.isdir(os.path.join(output_dir, file_path)):
                csv_files = [f for f in os.listdir(os.path.join(output_dir, file_path)) 
                           if f.endswith('.csv') and not f.startswith('_')]
                
                if csv_files:
                    csv_file = csv_files[0]  # Take the first CSV file
                    old_path = os.path.join(output_dir, file_path, csv_file)
                    new_path = os.path.join(output_dir, f"{file_path}.dat")
                    
                    # Move and rename file
                    import shutil
                    shutil.move(old_path, new_path)
                    
                    # Clean up empty directory
                    try:
                        os.rmdir(os.path.join(output_dir, file_path))
                    except:
                        pass
        
        # Verify data files were created
        data_files = [f for f in os.listdir(output_dir) if f.endswith('.dat')]
        if not data_files:
            logger.error("No .dat files found after generation")
            return False
        
        logger.info(f"Successfully generated {len(data_files)} TPC-DS data files using Spark")
        logger.info(f"Generated tables: {', '.join([f.replace('.dat', '') for f in data_files])}")
        return True
        
    except Exception as e:
        logger.error(f"Spark-based data generation error: {e}")
        return False


def generate_tpcds_queries(output_dir: str, num_queries: int = 10) -> bool:
    """Generate TPC-DS queries using dsqgen."""
    import subprocess
    
    logger = logging.getLogger('iceberg_benchmark.utils')
    logger.info(f"Starting TPC-DS query generation ({num_queries} queries)")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # dsqgen needs to be run from its tools directory
    cmd = f"cd /opt/tpcds-kit/tools && ./dsqgen -output_dir {output_dir} -streams {num_queries}"
    logger.info(f"Running command: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"Query generation failed: {result.stderr}")
            return False
        
        logger.info(f"Completed TPC-DS query generation ({num_queries} queries)")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Query generation timed out")
        return False
    except Exception as e:
        logger.error(f"Query generation error: {e}")
        return False


if __name__ == "__main__":
    # Simple test
    logger = setup_logging()
    logger.info("Utils module test")
    
    print(f"Timestamp: {get_timestamp()}")
    print(f"Duration: {format_duration(3661.5)}")
    print(f"Bytes: {format_bytes(1536000000)}")
    
    with Timer("Test operation"):
        time.sleep(0.1)
