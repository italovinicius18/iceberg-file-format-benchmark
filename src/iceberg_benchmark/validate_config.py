"""
Configuration validation script for Iceberg benchmark.

This script validates benchmark configuration files and provides
detailed error reporting.
"""

import sys
import os
import yaml
import argparse
from pathlib import Path

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from iceberg_benchmark.config import BenchmarkConfig, load_config
except ImportError:
    print("Warning: Could not import benchmark modules")
    sys.exit(1)


def validate_yaml_syntax(config_path: str) -> bool:
    """Validate YAML syntax."""
    try:
        with open(config_path, 'r') as f:
            yaml.safe_load(f)
        return True
    except yaml.YAMLError as e:
        print(f"YAML syntax error: {e}")
        return False
    except Exception as e:
        print(f"Error reading file: {e}")
        return False


def validate_file_structure(config_path: str) -> bool:
    """Validate configuration file structure."""
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Check required top-level sections
        required_sections = ['benchmark', 'tpcds', 'iceberg', 'spark']
        missing_sections = []
        
        for section in required_sections:
            if section not in config_data:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"Missing required sections: {missing_sections}")
            return False
        
        # Check benchmark section
        benchmark = config_data.get('benchmark', {})
        if 'name' not in benchmark:
            print("Missing 'name' in benchmark section")
            return False
        
        # Check tpcds section
        tpcds = config_data.get('tpcds', {})
        required_tpcds = ['scale_factor', 'queries']
        missing_tpcds = [key for key in required_tpcds if key not in tpcds]
        if missing_tpcds:
            print(f"Missing required TPC-DS fields: {missing_tpcds}")
            return False
        
        # Check iceberg section
        iceberg = config_data.get('iceberg', {})
        required_iceberg = ['formats', 'compressions']
        missing_iceberg = [key for key in required_iceberg if key not in iceberg]
        if missing_iceberg:
            print(f"Missing required Iceberg fields: {missing_iceberg}")
            return False
        
        # Check spark section
        spark = config_data.get('spark', {})
        if 'driver' not in spark or 'executor' not in spark:
            print("Missing 'driver' or 'executor' in spark section")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error validating file structure: {e}")
        return False


def validate_values(config_path: str) -> bool:
    """Validate configuration values."""
    try:
        config = load_config(config_path)
        errors = config.validate()
        
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error validating configuration values: {e}")
        return False


def check_dependencies(config_path: str) -> bool:
    """Check if all dependencies are available."""
    print("Checking dependencies...")
    
    # Check required Python packages
    required_packages = [
        ('pyspark', 'PySpark'),
        ('yaml', 'PyYAML'),
        ('click', 'Click'),
    ]
    
    missing_packages = []
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} (missing)")
            missing_packages.append(name)
    
    # Check environment variables
    env_vars = ['SPARK_HOME', 'TPCDS_HOME']
    missing_env = []
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if os.path.exists(value):
                print(f"  ✓ {var}: {value}")
            else:
                print(f"  ⚠ {var}: {value} (path does not exist)")
                missing_env.append(var)
        else:
            print(f"  ✗ {var} (not set)")
            missing_env.append(var)
    
    if missing_packages or missing_env:
        print("\nMissing dependencies detected.")
        if missing_packages:
            print(f"Install missing packages: pip install {' '.join(missing_packages.lower() for missing_packages in missing_packages)}")
        if missing_env:
            print(f"Set missing environment variables: {', '.join(missing_env)}")
        return False
    
    return True


def print_config_summary(config_path: str) -> None:
    """Print configuration summary."""
    try:
        config = load_config(config_path)
        
        print("\n" + "="*50)
        print("CONFIGURATION SUMMARY")
        print("="*50)
        
        print(f"Name: {config.name}")
        print(f"Description: {config.description}")
        
        print(f"\nTPC-DS Configuration:")
        print(f"  Scale Factor: {config.tpcds.scale_factor}")
        print(f"  Queries: {len(config.tpcds.queries)} ({', '.join(config.tpcds.queries[:5])}{'...' if len(config.tpcds.queries) > 5 else ''})")
        print(f"  Parallel Jobs: {config.tpcds.parallel_jobs}")
        
        print(f"\nIceberg Configuration:")
        print(f"  Formats: {', '.join(config.iceberg.formats)}")
        print(f"  Compressions: {', '.join(config.iceberg.compressions)}")
        print(f"  Partitioning Strategies: {len(config.iceberg.partitioning)}")
        
        print(f"\nSpark Configuration:")
        print(f"  Driver Memory: {config.spark.driver_memory}")
        print(f"  Driver Cores: {config.spark.driver_cores}")
        print(f"  Executor Memory: {config.spark.executor_memory}")
        print(f"  Executor Cores: {config.spark.executor_cores}")
        print(f"  Executor Instances: {config.spark.executor_instances}")
        
        print(f"\nKubernetes Configuration:")
        print(f"  Namespace: {config.kubernetes.namespace}")
        
        print(f"\nOutput Configuration:")
        print(f"  Results Directory: {config.output.results_dir}")
        print(f"  Format: {config.output.format}")
        print(f"  Include Raw Metrics: {config.output.include_raw_metrics}")
        
        print(f"\nMonitoring:")
        print(f"  Enabled: {config.monitoring.enabled}")
        print(f"  Metrics Interval: {config.monitoring.metrics_interval}s")
        print(f"  Metrics to Collect: {len(config.monitoring.collect)}")
        
        # Estimate runtime
        total_combinations = (
            len(config.iceberg.formats) * 
            len(config.iceberg.compressions) * 
            len(config.iceberg.partitioning) * 
            len(config.tpcds.queries)
        )
        
        print(f"\nEstimated Execution:")
        print(f"  Total Query Combinations: {total_combinations}")
        print(f"  Estimated Runtime: ~{total_combinations * 30}s (assuming 30s per query)")
        
    except Exception as e:
        print(f"Error generating summary: {e}")


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description='Validate Iceberg benchmark configuration')
    parser.add_argument('config', help='Path to configuration file')
    parser.add_argument('--check-deps', action='store_true', help='Check dependencies')
    parser.add_argument('--summary', action='store_true', help='Show configuration summary')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    config_path = args.config
    
    # Check if file exists
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    
    print(f"Validating configuration: {config_path}")
    print("-" * 50)
    
    # Validation steps
    all_valid = True
    
    # 1. Validate YAML syntax
    print("1. Validating YAML syntax...")
    if validate_yaml_syntax(config_path):
        print("   ✓ YAML syntax is valid")
    else:
        print("   ✗ YAML syntax is invalid")
        all_valid = False
    
    # 2. Validate file structure
    print("2. Validating file structure...")
    if validate_file_structure(config_path):
        print("   ✓ File structure is valid")
    else:
        print("   ✗ File structure is invalid")
        all_valid = False
    
    # 3. Validate configuration values
    print("3. Validating configuration values...")
    if validate_values(config_path):
        print("   ✓ Configuration values are valid")
    else:
        print("   ✗ Configuration values are invalid")
        all_valid = False
    
    # 4. Check dependencies (optional)
    if args.check_deps:
        print("4. Checking dependencies...")
        if check_dependencies(config_path):
            print("   ✓ All dependencies are available")
        else:
            print("   ⚠ Some dependencies are missing")
            # Don't fail validation for missing deps
    
    # 5. Show summary (optional)
    if args.summary and all_valid:
        print_config_summary(config_path)
    
    # Final result
    print("\n" + "="*50)
    if all_valid:
        print("✓ CONFIGURATION IS VALID")
        print("\nYou can now run the benchmark with:")
        print(f"  python3 src/iceberg_benchmark/cli.py run --config {config_path}")
        sys.exit(0)
    else:
        print("✗ CONFIGURATION IS INVALID")
        print("\nPlease fix the errors above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
