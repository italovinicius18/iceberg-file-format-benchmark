# Iceberg Benchmark - Quick Start Example

## Overview

This example demonstrates how to run the Iceberg TPC-DS benchmark locally using Kind.

## Prerequisites

Make sure you have the required dependencies:
```bash
make check-deps
```

If dependencies are missing, install them:
```bash
make install-deps
```

## Step-by-Step Execution

### 1. Setup Environment

```bash
# This will:
# - Create Kind cluster with 1 master + 2 workers  
# - Build Docker image with Spark + Iceberg + PySpark TPC-DS generator
# - Deploy Kubernetes resources (Spark-based data generation)
# - Setup port forwarding
make setup
```

### 2. Run Small Benchmark (Quick Test)

```bash
# Run benchmark with small configuration:
# - TPC-DS scale factor: 0.1 (Spark-generated data)
# - Queries: q1, q3, q6, q7, q19, q42, q52, q55, q61, q68
# - Formats: Parquet, ORC  
# - Compressions: Snappy, ZSTD
make run CONFIG=small
```

### 3. Monitor Execution

```bash
# Interactive monitoring dashboard
make monitor

# Or check status
make status

# View logs
make logs
```

### 4. Access Spark UI

```bash
# Forward ports (if not already done)
make port-forward

# Open browser to http://localhost:4040
```

### 5. View Results

```bash
# Show latest results
make results

# Results are saved in results/ directory:
# - benchmark_summary_*.json: Summary statistics
# - benchmark_results_*.json: Detailed query results
# - benchmark_system_*.json: System metrics
# - report_*.txt: Human-readable report
```

### 6. Run Medium Benchmark (Comprehensive)

```bash
# Run with larger dataset and more queries
make run CONFIG=medium
```

### 7. Clean Up

```bash
# Remove cluster, images, and data
make clean
```

## Example Output

### Benchmark Summary
```
=================================================
ICEBERG BENCHMARK REPORT
=================================================

Benchmark completed at: 2024-08-19 14:30:45
Total runtime: 15m 32s

QUERY STATISTICS:
  Total queries: 40
  Successful: 38
  Failed: 2
  Average execution time: 23.5s
  Min execution time: 5.2s
  Max execution time: 67.1s

FORMAT COMPARISON:
  parquet_snappy:
    Queries: 20
    Avg time: 21.3s
    Avg bytes read: 45,231,892
    Avg bytes written: 8,934,234

  orc_zstd:
    Queries: 18
    Avg time: 25.8s
    Avg bytes read: 38,445,123
    Avg bytes written: 7,123,456

SYSTEM RESOURCES:
  Average CPU: 65.2%
  Peak CPU: 89.1%
  Average Memory: 78.4%
  Peak Memory: 92.3%
=================================================
```

### Performance Comparison
The benchmark automatically compares:

1. **Execution Time**: Query performance by format/compression
2. **Storage Efficiency**: File sizes and compression ratios
3. **I/O Performance**: Read/write throughput
4. **Resource Usage**: CPU and memory consumption

## Configuration Options

### Small Configuration (configs/small.yaml)
- **Dataset**: 0.1GB (100MB)
- **Queries**: 10 selected queries
- **Runtime**: ~10-15 minutes
- **Use Case**: Quick validation and testing

### Medium Configuration (configs/medium.yaml)
- **Dataset**: 1GB
- **Queries**: 20 comprehensive queries
- **Runtime**: ~30-45 minutes
- **Use Case**: Full performance evaluation

### Custom Configuration
Create your own configuration:

```bash
# Generate template
make create-config --name my-test --scale 0.5 --output configs/custom.yaml

# Edit configuration
vim configs/custom.yaml

# Validate
make validate CONFIG=custom

# Run
make run CONFIG=custom
```

## Troubleshooting

### Common Issues

1. **Pod Stuck in Pending**
   ```bash
   kubectl describe pods -n iceberg-benchmark
   # Check resource constraints and node capacity
   ```

2. **Out of Memory**
   - Reduce scale factor in configuration
   - Increase memory limits in Kubernetes resources

3. **Slow Execution**
   - Check resource allocation
   - Monitor with `make monitor`
   - Verify data partitioning

4. **Connection Issues**
   ```bash
   # Check cluster status
   kubectl cluster-info
   
   # Restart port forwarding
   make port-forward
   ```

### Debug Commands

```bash
# Get cluster information
make status

# Check pod logs
kubectl logs -n iceberg-benchmark -l app=iceberg-benchmark -f

# Access pod shell
kubectl exec -it <pod-name> -n iceberg-benchmark -- bash

# Check events
kubectl get events -n iceberg-benchmark --sort-by='.lastTimestamp'
```

## Advanced Usage

### Custom Queries
Add your own TPC-DS queries by editing:
`deployment/kubernetes/configmaps.yaml`

### Different Scale Factors
Modify the `tpcds.scale_factor` in configuration files:
- 0.01 = 10MB (testing)
- 0.1 = 100MB (small)
- 1.0 = 1GB (medium)
- 10.0 = 10GB (large)

### Additional Formats
Add new formats to `iceberg.formats` in configuration:
- parquet
- orc
- avro (experimental)

### More Compressions
Add to `iceberg.compressions`:
- snappy (fast)
- zstd (balanced)
- lz4 (fast)
- gzip (compatible)
- brotli (high compression)

## Results Analysis

### JSON Output
Results are saved in structured JSON format for analysis:

```python
import json
import pandas as pd

# Load results
with open('results/benchmark_results_*.json') as f:
    data = json.load(f)

# Convert to DataFrame
df = pd.DataFrame(data['query_results'])

# Analyze by format
format_comparison = df.groupby(['format', 'compression']).agg({
    'execution_time': ['mean', 'std'],
    'bytes_read': 'mean',
    'bytes_written': 'mean'
})

print(format_comparison)
```

### Visualization
Generate charts (if matplotlib is installed):

```python
import matplotlib.pyplot as plt

# Plot execution times
df.boxplot(column='execution_time', by=['format', 'compression'])
plt.title('Query Execution Time by Format/Compression')
plt.show()
```

## Next Steps

1. **Scale Up**: Try larger datasets with higher scale factors
2. **Tune Performance**: Optimize Spark and Iceberg configurations
3. **Add Metrics**: Extend monitoring with custom metrics
4. **Automate**: Integrate with CI/CD pipelines
5. **Compare**: Run against different Iceberg versions
