"""
Configuration management for Iceberg benchmark.

This module handles loading and validating benchmark configurations
from YAML files and environment variables.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path


@dataclass
class SparkConfig:
    """Spark configuration settings."""
    driver_memory: str = "2g"
    driver_cores: int = 1
    executor_memory: str = "2g" 
    executor_cores: int = 1
    executor_instances: int = 2
    config: Dict[str, str] = field(default_factory=dict)


@dataclass
class TpcdsConfig:
    """TPC-DS configuration settings."""
    scale_factor: float = 0.1
    queries: List[str] = field(default_factory=list)
    parallel_jobs: int = 2


@dataclass
class IcebergConfig:
    """Iceberg configuration settings."""
    formats: List[str] = field(default_factory=lambda: ["parquet"])
    compressions: List[str] = field(default_factory=lambda: ["snappy"])
    partitioning: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class KubernetesConfig:
    """Kubernetes configuration settings."""
    namespace: str = "iceberg-benchmark"
    resources: Dict[str, Any] = field(default_factory=dict)
    storage: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringConfig:
    """Monitoring configuration settings."""
    enabled: bool = True
    metrics_interval: int = 30
    collect: List[str] = field(default_factory=list)


@dataclass
class OutputConfig:
    """Output configuration settings."""
    results_dir: str = "/app/results"
    format: str = "json"
    include_raw_metrics: bool = True
    generate_charts: bool = False


@dataclass
class BenchmarkConfig:
    """Main benchmark configuration class."""
    name: str = "iceberg-benchmark"
    description: str = "Iceberg benchmark"
    
    # Component configurations
    tpcds: TpcdsConfig = field(default_factory=TpcdsConfig)
    iceberg: IcebergConfig = field(default_factory=IcebergConfig)
    spark: SparkConfig = field(default_factory=SparkConfig)
    kubernetes: KubernetesConfig = field(default_factory=KubernetesConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    
    @classmethod
    def from_yaml(cls, config_path: str) -> "BenchmarkConfig":
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls.from_dict(config_data)
    
    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> "BenchmarkConfig":
        """Create configuration from dictionary."""
        # Extract benchmark info
        benchmark_info = config_data.get('benchmark', {})
        name = benchmark_info.get('name', 'iceberg-benchmark')
        description = benchmark_info.get('description', 'Iceberg benchmark')
        
        # Parse TPC-DS config
        tpcds_data = config_data.get('tpcds', {})
        tpcds_config = TpcdsConfig(
            scale_factor=tpcds_data.get('scale_factor', 0.1),
            queries=tpcds_data.get('queries', []),
            parallel_jobs=tpcds_data.get('parallel_jobs', 2)
        )
        
        # Parse Iceberg config
        iceberg_data = config_data.get('iceberg', {})
        iceberg_config = IcebergConfig(
            formats=iceberg_data.get('formats', ['parquet']),
            compressions=iceberg_data.get('compressions', ['snappy']),
            partitioning=iceberg_data.get('partitioning', [])
        )
        
        # Parse Spark config
        spark_data = config_data.get('spark', {})
        driver_data = spark_data.get('driver', {})
        executor_data = spark_data.get('executor', {})
        
        spark_config = SparkConfig(
            driver_memory=driver_data.get('memory', '2g'),
            driver_cores=driver_data.get('cores', 1),
            executor_memory=executor_data.get('memory', '2g'),
            executor_cores=executor_data.get('cores', 1),
            executor_instances=executor_data.get('instances', 2),
            config=spark_data.get('config', {})
        )
        
        # Parse Kubernetes config
        k8s_data = config_data.get('kubernetes', {})
        k8s_config = KubernetesConfig(
            namespace=k8s_data.get('namespace', 'iceberg-benchmark'),
            resources=k8s_data.get('resources', {}),
            storage=k8s_data.get('storage', {})
        )
        
        # Parse monitoring config
        monitoring_data = config_data.get('monitoring', {})
        monitoring_config = MonitoringConfig(
            enabled=monitoring_data.get('enabled', True),
            metrics_interval=monitoring_data.get('metrics_interval', 30),
            collect=monitoring_data.get('collect', [])
        )
        
        # Parse output config
        output_data = config_data.get('output', {})
        output_config = OutputConfig(
            results_dir=output_data.get('results_dir', '/app/results'),
            format=output_data.get('format', 'json'),
            include_raw_metrics=output_data.get('include_raw_metrics', True),
            generate_charts=output_data.get('generate_charts', False)
        )
        
        return cls(
            name=name,
            description=description,
            tpcds=tpcds_config,
            iceberg=iceberg_config,
            spark=spark_config,
            kubernetes=k8s_config,
            monitoring=monitoring_config,
            output=output_config
        )
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate TPC-DS config
        if self.tpcds.scale_factor <= 0:
            errors.append("TPC-DS scale factor must be positive")
        
        if not self.tpcds.queries:
            errors.append("No TPC-DS queries specified")
        
        if self.tpcds.parallel_jobs <= 0:
            errors.append("TPC-DS parallel jobs must be positive")
        
        # Validate Iceberg config
        valid_formats = {'parquet', 'orc', 'avro'}
        if not all(fmt in valid_formats for fmt in self.iceberg.formats):
            errors.append(f"Invalid formats. Supported: {valid_formats}")
        
        valid_compressions = {'snappy', 'gzip', 'lz4', 'zstd', 'brotli'}
        if not all(comp in valid_compressions for comp in self.iceberg.compressions):
            errors.append(f"Invalid compressions. Supported: {valid_compressions}")
        
        # Validate Spark config
        if not self.spark.driver_memory.endswith(('m', 'g')):
            errors.append("Spark driver memory must end with 'm' or 'g'")
        
        if not self.spark.executor_memory.endswith(('m', 'g')):
            errors.append("Spark executor memory must end with 'm' or 'g'")
        
        if self.spark.driver_cores <= 0:
            errors.append("Spark driver cores must be positive")
        
        if self.spark.executor_cores <= 0:
            errors.append("Spark executor cores must be positive")
        
        if self.spark.executor_instances <= 0:
            errors.append("Spark executor instances must be positive")
        
        # Validate paths
        if not self.output.results_dir:
            errors.append("Output results directory cannot be empty")
        
        return errors
    
    def get_spark_conf(self) -> Dict[str, str]:
        """Get Spark configuration as dictionary."""
        conf = {
            'spark.driver.memory': self.spark.driver_memory,
            'spark.driver.cores': str(self.spark.driver_cores),
            'spark.executor.memory': self.spark.executor_memory,
            'spark.executor.cores': str(self.spark.executor_cores),
            'spark.executor.instances': str(self.spark.executor_instances),
        }
        
        # Add custom Spark config
        conf.update(self.spark.config)
        
        return conf
    
    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables for the benchmark."""
        return {
            'BENCHMARK_NAME': self.name,
            'TPCDS_SCALE_FACTOR': str(self.tpcds.scale_factor),
            'RESULTS_DIR': self.output.results_dir,
            'KUBERNETES_NAMESPACE': self.kubernetes.namespace,
            'MONITORING_ENABLED': str(self.monitoring.enabled).lower(),
        }


def load_config(config_path: Optional[str] = None) -> BenchmarkConfig:
    """Load benchmark configuration from file or environment."""
    if config_path is None:
        config_path = os.getenv('BENCHMARK_CONFIG', '/app/configs/small.yaml')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    config = BenchmarkConfig.from_yaml(config_path)
    
    # Validate configuration
    errors = config.validate()
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
    
    return config


def get_default_config() -> BenchmarkConfig:
    """Get default benchmark configuration."""
    return BenchmarkConfig()


if __name__ == "__main__":
    # Simple test
    config = get_default_config()
    print(f"Default config: {config.name}")
    print(f"Validation errors: {config.validate()}")
