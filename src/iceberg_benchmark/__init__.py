# Iceberg TPC-DS Benchmark Package
"""
A comprehensive benchmark suite for Apache Iceberg using TPC-DS workload.

This package provides tools to:
- Generate TPC-DS data at various scales
- Test different file formats (Parquet, ORC)
- Compare compression algorithms
- Evaluate partitioning strategies
- Collect performance metrics
- Run on Kubernetes with Kind
"""

__version__ = "1.0.0"
__author__ = "Iceberg Benchmark Team"
__email__ = "benchmark@iceberg.apache.org"

from .benchmark import IcebergBenchmark
from .config import BenchmarkConfig
from .metrics import MetricsCollector
from .utils import setup_logging

__all__ = [
    "IcebergBenchmark",
    "BenchmarkConfig", 
    "MetricsCollector",
    "setup_logging"
]
