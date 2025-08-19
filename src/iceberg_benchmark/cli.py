"""
Command Line Interface for Iceberg TPC-DS Benchmark.

This module provides the main CLI for running benchmarks, validating configurations,
and managing the benchmark environment.
"""

import sys
import os
import click
import logging
from pathlib import Path
from typing import Optional

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from iceberg_benchmark.config import load_config, BenchmarkConfig
from iceberg_benchmark.benchmark import IcebergBenchmark
from iceberg_benchmark.utils import setup_logging


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--log-file', type=str, help='Log file path')
@click.pass_context
def cli(ctx, verbose, log_file):
    """Iceberg TPC-DS Benchmark CLI."""
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    logger = setup_logging(level=log_level, log_file=log_file)
    
    # Store logger in context for other commands
    ctx.ensure_object(dict)
    ctx.obj['logger'] = logger


@cli.command()
@click.option('--config', '-c', required=True, help='Path to benchmark configuration file')
@click.option('--dry-run', is_flag=True, help='Validate configuration without running benchmark')
@click.pass_context
def run(ctx, config, dry_run):
    """Run the Iceberg benchmark."""
    logger = ctx.obj['logger']
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from: {config}")
        benchmark_config = load_config(config)
        
        logger.info(f"Benchmark: {benchmark_config.name}")
        logger.info(f"Description: {benchmark_config.description}")
        logger.info(f"TPC-DS Scale Factor: {benchmark_config.tpcds.scale_factor}")
        logger.info(f"Formats: {benchmark_config.iceberg.formats}")
        logger.info(f"Compressions: {benchmark_config.iceberg.compressions}")
        logger.info(f"Queries: {len(benchmark_config.tpcds.queries)}")
        
        if dry_run:
            logger.info("Dry run mode - configuration is valid")
            return
        
        # Create and run benchmark
        benchmark = IcebergBenchmark(benchmark_config)
        
        success = benchmark.run()
        
        if success:
            logger.info("Benchmark completed successfully")
            sys.exit(0)
        else:
            logger.error("Benchmark failed")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Benchmark execution failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', required=True, help='Path to configuration file to validate')
@click.pass_context
def validate(ctx, config):
    """Validate benchmark configuration."""
    logger = ctx.obj['logger']
    
    try:
        logger.info(f"Validating configuration: {config}")
        
        # Check if file exists
        if not os.path.exists(config):
            logger.error(f"Configuration file not found: {config}")
            sys.exit(1)
        
        # Load and validate configuration
        benchmark_config = load_config(config)
        errors = benchmark_config.validate()
        
        if errors:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            sys.exit(1)
        else:
            logger.info("Configuration is valid")
            
            # Print configuration summary
            click.echo("\nConfiguration Summary:")
            click.echo(f"  Name: {benchmark_config.name}")
            click.echo(f"  Description: {benchmark_config.description}")
            click.echo(f"  TPC-DS Scale Factor: {benchmark_config.tpcds.scale_factor}")
            click.echo(f"  Parallel Jobs: {benchmark_config.tpcds.parallel_jobs}")
            click.echo(f"  Formats: {', '.join(benchmark_config.iceberg.formats)}")
            click.echo(f"  Compressions: {', '.join(benchmark_config.iceberg.compressions)}")
            click.echo(f"  Queries: {len(benchmark_config.tpcds.queries)}")
            click.echo(f"  Results Directory: {benchmark_config.output.results_dir}")
            click.echo(f"  Monitoring Enabled: {benchmark_config.monitoring.enabled}")
    
    except Exception as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', required=True, help='Path to benchmark configuration file')
@click.pass_context
def generate_data(ctx, config):
    """Generate TPC-DS data only."""
    logger = ctx.obj['logger']
    
    try:
        # Load configuration
        benchmark_config = load_config(config)
        
        # Create benchmark instance
        benchmark = IcebergBenchmark(benchmark_config)
        
        # Setup and generate data
        if not benchmark.setup():
            logger.error("Benchmark setup failed")
            sys.exit(1)
        
        logger.info("Generating TPC-DS data...")
        if benchmark.generate_data():
            logger.info("Data generation completed successfully")
        else:
            logger.error("Data generation failed")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Data generation failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', required=True, help='Path to benchmark configuration file')
@click.pass_context
def create_tables(ctx, config):
    """Create Iceberg tables only."""
    logger = ctx.obj['logger']
    
    try:
        # Load configuration
        benchmark_config = load_config(config)
        
        # Create benchmark instance
        benchmark = IcebergBenchmark(benchmark_config)
        
        # Setup
        if not benchmark.setup():
            logger.error("Benchmark setup failed")
            sys.exit(1)
        
        logger.info("Creating Iceberg tables...")
        if benchmark.create_tables():
            logger.info("Table creation completed successfully")
        else:
            logger.error("Table creation failed")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Table creation failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--results-dir', '-r', default='/app/results', help='Results directory to analyze')
@click.option('--output', '-o', help='Output file for analysis report')
@click.pass_context
def analyze(ctx, results_dir, output):
    """Analyze benchmark results."""
    logger = ctx.obj['logger']
    
    try:
        import json
        import glob
        
        logger.info(f"Analyzing results in: {results_dir}")
        
        # Find result files
        result_files = glob.glob(os.path.join(results_dir, "*_summary_*.json"))
        
        if not result_files:
            logger.error(f"No result files found in {results_dir}")
            sys.exit(1)
        
        # Load and analyze results
        all_results = []
        for result_file in result_files:
            with open(result_file, 'r') as f:
                result_data = json.load(f)
                all_results.append(result_data)
        
        # Generate analysis report
        report_lines = [
            "=" * 60,
            "BENCHMARK ANALYSIS REPORT",
            "=" * 60,
            "",
            f"Total benchmark runs: {len(all_results)}",
            ""
        ]
        
        # Analyze each result
        for i, result in enumerate(all_results, 1):
            report_lines.extend([
                f"Run {i}:",
                f"  Runtime: {result['benchmark_info']['total_runtime']:.2f}s",
                f"  Queries: {result['query_statistics']['total_queries']}",
                f"  Success Rate: {result['query_statistics']['successful_queries']}/{result['query_statistics']['total_queries']}",
                ""
            ])
        
        # Save or print report
        report_text = "\n".join(report_lines)
        
        if output:
            with open(output, 'w') as f:
                f.write(report_text)
            logger.info(f"Analysis report saved to: {output}")
        else:
            click.echo(report_text)
    
    except Exception as e:
        logger.error(f"Results analysis failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--name', '-n', default='benchmark', help='Benchmark name')
@click.option('--scale', '-s', type=float, default=0.1, help='TPC-DS scale factor')
@click.option('--output', '-o', required=True, help='Output configuration file')
@click.pass_context
def create_config(ctx, name, scale, output):
    """Create a new benchmark configuration file."""
    logger = ctx.obj['logger']
    
    try:
        import yaml
        
        # Create default configuration
        config_data = {
            'benchmark': {
                'name': name,
                'description': f'Iceberg benchmark with scale factor {scale}'
            },
            'tpcds': {
                'scale_factor': scale,
                'queries': ['q1', 'q3', 'q6', 'q7', 'q19'],
                'parallel_jobs': 2
            },
            'iceberg': {
                'formats': ['parquet'],
                'compressions': ['snappy'],
                'partitioning': [{'type': 'none'}]
            },
            'spark': {
                'driver': {
                    'memory': '2g',
                    'cores': 1
                },
                'executor': {
                    'memory': '2g',
                    'cores': 1,
                    'instances': 2
                },
                'config': {
                    'spark.sql.adaptive.enabled': 'true',
                    'spark.sql.adaptive.coalescePartitions.enabled': 'true',
                    'spark.sql.extensions': 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions',
                    'spark.sql.catalog.local': 'org.apache.iceberg.spark.SparkCatalog',
                    'spark.sql.catalog.local.type': 'hadoop',
                    'spark.sql.catalog.local.warehouse': '/tmp/iceberg-warehouse'
                }
            },
            'kubernetes': {
                'namespace': 'iceberg-benchmark',
                'resources': {
                    'driver': {
                        'requests': {'memory': '2Gi', 'cpu': '1'},
                        'limits': {'memory': '3Gi', 'cpu': '2'}
                    },
                    'executor': {
                        'requests': {'memory': '2Gi', 'cpu': '1'},
                        'limits': {'memory': '3Gi', 'cpu': '2'}
                    }
                },
                'storage': {
                    'size': '10Gi',
                    'class': 'standard'
                }
            },
            'monitoring': {
                'enabled': True,
                'metrics_interval': 30,
                'collect': ['cpu_usage', 'memory_usage', 'query_duration']
            },
            'output': {
                'results_dir': '/app/results',
                'format': 'json',
                'include_raw_metrics': True
            }
        }
        
        # Save configuration
        with open(output, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)
        
        logger.info(f"Configuration created: {output}")
        
    except Exception as e:
        logger.error(f"Configuration creation failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.pass_context
def version(ctx):
    """Show version information."""
    from iceberg_benchmark import __version__
    click.echo(f"Iceberg TPC-DS Benchmark v{__version__}")


@cli.command()
@click.pass_context
def info(ctx):
    """Show environment information."""
    logger = ctx.obj['logger']
    
    try:
        import platform
        import sys
        
        click.echo("Environment Information:")
        click.echo(f"  Python: {sys.version}")
        click.echo(f"  Platform: {platform.platform()}")
        click.echo(f"  Architecture: {platform.architecture()}")
        
        # Check for required dependencies
        dependencies = [
            ('pyspark', 'PySpark'),
            ('yaml', 'PyYAML'),
            ('click', 'Click'),
            ('psutil', 'psutil'),
        ]
        
        click.echo("\nDependencies:")
        for module, name in dependencies:
            try:
                __import__(module)
                click.echo(f"  ✓ {name}")
            except ImportError:
                click.echo(f"  ✗ {name} (missing)")
        
        # Check environment variables
        env_vars = [
            'SPARK_HOME',
            'TPCDS_HOME',
            'KUBERNETES_NAMESPACE',
        ]
        
        click.echo("\nEnvironment Variables:")
        for var in env_vars:
            value = os.getenv(var, 'Not set')
            click.echo(f"  {var}: {value}")
    
    except Exception as e:
        logger.error(f"Failed to get environment info: {str(e)}")


if __name__ == "__main__":
    cli()
