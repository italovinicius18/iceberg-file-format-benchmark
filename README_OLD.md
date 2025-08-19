# Iceberg File Format Benchmark

A comprehensive benchmark suite for Apache Iceberg using TPC-DS workload, optimized for local execution with Kind (Kubernetes in Docker).

## 🚀 Quick Start

```bash
# Setup complete environment
make setup

# Run small benchmark (quick test)
make run CONFIG=small

# Monitor cluster and jobs
make monitor

# Clean up everything
make clean
```

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🔍 Overview

This project provides a complete benchmarking solution for Apache Iceberg, focusing on:

- **File Format Comparison**: Parquet vs ORC vs Avro
- **Compression Analysis**: Snappy, ZSTD, LZ4, and more
- **Partitioning Strategies**: None, Date-based, Hash-based
- **Performance Metrics**: Query execution time, I/O, compression ratios
- **Local Development**: Runs on Kind with minimal resource requirements
- **Automation**: Complete CI/CD-style automation with Makefile

## ✨ Features

### 🎯 Benchmarking Capabilities
- **TPC-DS Workload**: Industry-standard decision support benchmark
- **Multiple Scale Factors**: 0.1GB to 10GB+ datasets
- **Format Comparison**: Side-by-side performance analysis
- **Detailed Metrics**: Execution time, I/O patterns, resource usage
- **Query Subset**: Configurable query selection for fast testing

### 🏗️ Infrastructure
- **Kind Cluster**: Lightweight Kubernetes for local development
- **Docker Containers**: Isolated, reproducible environments
- **Spark-based TPC-DS**: PySpark data generation (eliminates native binary issues)
- **Persistent Storage**: Shared data and results across pods
- **Port Forwarding**: Easy access to Spark UI and APIs

### 📊 Monitoring & Analysis
- **Real-time Metrics**: CPU, memory, disk, network monitoring
- **Performance Comparison**: Automated format/compression analysis
- **Result Visualization**: Charts and reports generation
- **Export Formats**: JSON, CSV, and text reports

## 📦 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu/Debian preferred), macOS
- **CPU**: 4+ cores (8+ recommended)
- **RAM**: 8GB+ (16GB+ recommended)
- **Disk**: 20GB+ free space
- **Docker**: 20.10+
- **Python**: 3.8+

### Required Tools
```bash
# Install dependencies automatically
make install-deps

# Or install manually:
# Docker, Kind, kubectl, Python 3.8+
```

### Resource Recommendations

| Configuration | CPU | RAM | Disk | Use Case |
|---------------|-----|-----|------|----------|
| Small         | 2 cores | 4GB | 10GB | Quick testing |
| Medium        | 4 cores | 8GB | 20GB | Development |
| Large         | 8+ cores | 16GB+ | 50GB+ | Full benchmarks |

### 🔧 TPC-DS Data Generation

This benchmark uses **Spark-based TPC-DS data generation** instead of native binaries:

- ✅ **No segmentation faults**: Eliminates native binary reliability issues
- ✅ **Pure PySpark**: Programmatic data generation using Spark SQL
- ✅ **Scalable**: Works with any scale factor and deployment environment  
- ✅ **Standard format**: Generates standard TPC-DS .dat files with pipe delimiters
- ✅ **Platform independent**: No compilation or native dependencies required

The approach generates realistic TPC-DS tables (call_center, store_sales, customer, item, date_dim, store) with proper relationships and data distribution patterns.

## 🛠️ Installation

### Option 1: Automated Setup (Recommended)

```bash
# Clone repository
git clone https://github.com/italovinicius18/iceberg-file-format-benchmark.git
cd iceberg-file-format-benchmark

# Install dependencies and setup environment
make install-deps
make setup
```

### Option 2: Manual Setup

```bash
# 1. Clone repository
git clone https://github.com/italovinicius18/iceberg-file-format-benchmark.git
cd iceberg-file-format-benchmark

# 2. Install dependencies
sudo apt-get update
sudo apt-get install docker.io python3 python3-pip

# Install Kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# 3. Build Docker image
docker build -t iceberg-benchmark:latest .

# 4. Create Kind cluster
./scripts/setup-kind-cluster.sh

# 5. Run benchmark
./scripts/run-benchmark.sh small
```

## 🎯 Usage

### Basic Commands

```bash
# Setup environment
make setup                    # Complete setup

# Run benchmarks
make run CONFIG=small        # Quick test (0.1GB)
make run CONFIG=medium       # Full test (1GB)

# Monitor and debug
make monitor                 # Interactive monitoring
make logs                    # Show pod logs
make status                  # Cluster status
make port-forward           # Forward Spark UI

# Cleanup
make clean                   # Remove everything
```

### Advanced Usage

```bash
# Validate configuration
make validate CONFIG=small

# Build development image
make dev-build

# Run in development mode
make dev-run

# Custom configuration
python3 src/iceberg_benchmark/cli.py run --config custom.yaml

# Generate new configuration
python3 src/iceberg_benchmark/cli.py create-config \
  --name my-benchmark \
  --scale 0.5 \
  --output configs/custom.yaml
```

## ⚙️ Configuration

### Configuration Files

The project uses YAML configuration files in the `configs/` directory:

- `small.yaml` - Quick testing (0.1GB, 10 queries)
- `medium.yaml` - Comprehensive testing (1GB, 20 queries)

### Sample Configuration

```yaml
benchmark:
  name: "my-iceberg-benchmark"
  description: "Custom benchmark configuration"

tpcds:
  scale_factor: 0.5  # Dataset size in GB
  queries: ["q1", "q3", "q6", "q7"]  # TPC-DS queries to run
  parallel_jobs: 2

iceberg:
  formats: ["parquet", "orc"]
  compressions: ["snappy", "zstd"]
  partitioning:
    - type: "none"
    - type: "date"
      columns: ["d_date"]

spark:
  driver:
    memory: "2g"
    cores: 1
  executor:
    memory: "2g"
    cores: 1
    instances: 2

kubernetes:
  namespace: "iceberg-benchmark"
  resources:
    driver:
      requests: {memory: "2Gi", cpu: "1"}
      limits: {memory: "3Gi", cpu: "2"}

monitoring:
  enabled: true
  metrics_interval: 30
  collect: ["cpu_usage", "memory_usage", "query_duration"]

output:
  results_dir: "/app/results"
  format: "json"
  include_raw_metrics: true
```

### Environment Variables

```bash
# Kubernetes configuration
export KUBERNETES_NAMESPACE=iceberg-benchmark

# Benchmark configuration
export BENCHMARK_CONFIG=/app/configs/small.yaml
export RESULTS_DIR=/app/results

# Spark configuration
export SPARK_HOME=/opt/spark
# Note: TPC-DS data generation is now Spark-based (no tpcds-kit needed)
```

## 🏗️ Architecture

### System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Kind Cluster   │    │  Docker Images  │    │ Local Storage   │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Control     │ │    │ │ Benchmark   │ │    │ │ TPC-DS Data │ │
│ │ Plane       │ │    │ │ Runner      │ │    │ │             │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Worker      │ │    │ │ Spark +     │ │    │ │ Results     │ │
│ │ Node 1      │ │◄───┤ │ Iceberg     │ ├────┤ │ Storage     │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │                 │    │                 │
│ │ Worker      │ │    │                 │    │                 │
│ │ Node 2      │ │    │                 │    │                 │
│ └─────────────┘ │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Overview

- **Kind Cluster**: Lightweight Kubernetes cluster running in Docker
- **Benchmark Runner**: Main application orchestrating the benchmark
- **Spark Cluster**: Distributed processing engine running on Kubernetes
- **Iceberg Tables**: Apache Iceberg tables with different configurations
- **TPC-DS Data**: Generated test datasets at various scales
- **Metrics Collector**: System and application metrics collection
- **Results Storage**: Persistent storage for benchmark results

### Data Flow

1. **Data Generation**: TPC-DS toolkit generates test data
2. **Table Creation**: Iceberg tables created with different formats/compression
3. **Query Execution**: TPC-DS queries executed against all table variants
4. **Metrics Collection**: Performance metrics collected during execution
5. **Results Analysis**: Automated comparison and reporting

## 🔧 Development

### Project Structure

```
iceberg-file-format-benchmark/
├── deployment/kubernetes/    # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmaps.yaml
│   ├── storage-services.yaml
│   └── jobs.yaml
├── scripts/                  # Automation scripts
│   ├── setup-kind-cluster.sh
│   ├── run-benchmark.sh
│   ├── monitor.sh
│   ├── cleanup.sh
│   └── install-deps.sh
├── src/iceberg_benchmark/    # Python package
│   ├── __init__.py
│   ├── benchmark.py          # Main benchmark logic
│   ├── config.py             # Configuration management
│   ├── metrics.py            # Metrics collection
│   ├── utils.py              # Utility functions
│   ├── cli.py                # Command line interface
│   ├── controller.py         # Kubernetes controller
│   └── validate_config.py    # Configuration validation
├── configs/                  # Configuration files
│   ├── small.yaml
│   ├── medium.yaml
│   └── kind-cluster.yaml
├── data/                     # Generated TPC-DS data
├── results/                  # Benchmark results
├── Dockerfile               # Container image definition
├── Makefile                 # Automation commands
└── README.md               # This file
```

### Adding New Configurations

1. Create new YAML file in `configs/`
2. Validate with `make validate CONFIG=new-config`
3. Test with `make run CONFIG=new-config`

### Extending Functionality

- **New File Formats**: Add to `iceberg.formats` in config
- **New Compression**: Add to `iceberg.compressions` in config
- **New Queries**: Add SQL files to `deployment/kubernetes/configmaps.yaml`
- **Custom Metrics**: Extend `MetricsCollector` class

### Building and Testing

```bash
# Build Docker image
make build-image

# Run tests
python3 -m pytest tests/

# Validate configurations
make validate CONFIG=small
make validate CONFIG=medium

# Run development server
make dev-run
```

## 🔍 Monitoring

### Spark UI Access

```bash
# Forward Spark UI port
make port-forward

# Access Spark UI
open http://localhost:4040
```

### Real-time Monitoring

```bash
# Interactive monitoring dashboard
make monitor

# Continuous monitoring
watch -n 5 'make status'

# Pod logs
make logs
kubectl logs -n iceberg-benchmark -l app=iceberg-benchmark -f
```

### Metrics Collection

The benchmark automatically collects:

- **Query Metrics**: Execution time, rows processed, bytes read/written
- **System Metrics**: CPU usage, memory usage, disk I/O
- **Spark Metrics**: Task distribution, shuffle operations, cache usage
- **Compression Metrics**: Compression ratios, decompression time

## 🐛 Troubleshooting

### Common Issues

#### 1. Kind Cluster Creation Fails

```bash
# Check Docker is running
sudo systemctl status docker

# Clean up and retry
make clean
make setup
```

#### 2. Pod Stuck in Pending State

```bash
# Check resource constraints
kubectl describe pods -n iceberg-benchmark

# Check node resources
kubectl top nodes
```

#### 3. Out of Memory Errors

```bash
# Reduce scale factor in configuration
tpcds:
  scale_factor: 0.1  # Smaller dataset

# Increase memory limits
kubernetes:
  resources:
    executor:
      limits:
        memory: "4Gi"  # More memory
```

#### 4. Slow Query Execution

```bash
# Check if data is properly partitioned
# Verify Spark configuration
# Monitor resource usage with make monitor
```

### Debug Commands

```bash
# Check cluster status
make status

# Get detailed pod information
kubectl describe pods -n iceberg-benchmark

# Check events
kubectl get events -n iceberg-benchmark --sort-by='.lastTimestamp'

# Access pod shell
kubectl exec -it <pod-name> -n iceberg-benchmark -- bash

# View all logs
kubectl logs -n iceberg-benchmark --all-containers=true -f
```

### Performance Tuning

1. **Adjust Resource Limits**: Increase CPU/memory in config
2. **Optimize Spark Settings**: Tune parallelism and memory settings
3. **Use SSD Storage**: Better I/O performance for data processing
4. **Scale Cluster**: Add more worker nodes for larger datasets

## 📈 Results Analysis

### Output Files

Results are saved in the `results/` directory:

```
results/
├── iceberg_benchmark_summary_20241219_143022.json
├── iceberg_benchmark_results_20241219_143022.json
├── iceberg_benchmark_system_20241219_143022.json
├── iceberg_benchmark_raw_20241219_143022.json
└── report_20241219_143022.txt
```

### Analysis Tools

```bash
# View latest results
make results

# Analyze specific results
python3 src/iceberg_benchmark/cli.py analyze \
  --results-dir results/ \
  --output analysis_report.txt

# Generate custom analysis
python3 -c "
import json
with open('results/iceberg_benchmark_summary_*.json') as f:
    data = json.load(f)
    print(f'Total queries: {data[\"query_statistics\"][\"total_queries\"]}')
    print(f'Success rate: {data[\"query_statistics\"][\"successful_queries\"]}')
"
```

### Key Metrics

- **Execution Time**: Query completion time by format/compression
- **Compression Ratio**: Storage savings achieved
- **I/O Performance**: Read/write throughput
- **Resource Usage**: CPU and memory consumption
- **Success Rate**: Query completion percentage

## 🤝 Contributing

### Development Setup

```bash
# Fork and clone repository
git clone https://github.com/yourusername/iceberg-file-format-benchmark.git
cd iceberg-file-format-benchmark

# Create development branch
git checkout -b feature/your-feature

# Install development dependencies
pip install -r requirements-dev.txt

# Make changes and test
make validate CONFIG=small
make run CONFIG=small

# Submit pull request
```

### Guidelines

- Follow Python PEP 8 style guidelines
- Add tests for new functionality
- Update documentation for new features
- Validate configurations before submitting
- Test with multiple scale factors

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Apache Iceberg](https://iceberg.apache.org/) community
- [TPC-DS](http://www.tpc.org/tpcds/) benchmark specification
- [Kind](https://kind.sigs.k8s.io/) project for local Kubernetes
- [Apache Spark](https://spark.apache.org/) for distributed processing

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/italovinicius18/iceberg-file-format-benchmark/issues)
- **Discussions**: [GitHub Discussions](https://github.com/italovinicius18/iceberg-file-format-benchmark/discussions)
- **Documentation**: This README and inline code documentation

---

Made with ❤️ for the Apache Iceberg community
