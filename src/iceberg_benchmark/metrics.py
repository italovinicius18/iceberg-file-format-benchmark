"""
Metrics collection and monitoring for Iceberg benchmark.

This module handles collection of performance metrics, system metrics,
and benchmark results.
"""

import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path

from .utils import setup_logging, save_json, get_timestamp, format_duration


@dataclass
class BenchmarkMetric:
    """Individual benchmark metric."""
    name: str
    value: Any
    unit: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


@dataclass
class QueryResult:
    """Query execution result."""
    query_name: str
    format: str
    compression: str
    partitioning: str
    execution_time: float
    rows_read: int
    bytes_read: int
    rows_written: int
    bytes_written: int
    shuffle_read: int = 0
    shuffle_write: int = 0
    cpu_time: float = 0.0
    memory_peak: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'query_name': self.query_name,
            'format': self.format,
            'compression': self.compression,
            'partitioning': self.partitioning,
            'execution_time': self.execution_time,
            'rows_read': self.rows_read,
            'bytes_read': self.bytes_read,
            'rows_written': self.rows_written,
            'bytes_written': self.bytes_written,
            'shuffle_read': self.shuffle_read,
            'shuffle_write': self.shuffle_write,
            'cpu_time': self.cpu_time,
            'memory_peak': self.memory_peak,
            'error': self.error,
            'metadata': self.metadata
        }


class MetricsCollector:
    """Collects and manages benchmark metrics."""
    
    def __init__(self, output_dir: str = "/app/results", interval: int = 30):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.interval = interval
        self.logger = setup_logging()
        
        # Storage for metrics
        self.metrics: List[BenchmarkMetric] = []
        self.query_results: List[QueryResult] = []
        self.system_metrics: List[Dict[str, Any]] = []
        
        # Control flags
        self._collecting = False
        self._collection_thread: Optional[threading.Thread] = None
        
        # Start time
        self.start_time = time.time()
        
    def start_collection(self) -> None:
        """Start collecting system metrics."""
        if self._collecting:
            return
            
        self._collecting = True
        self._collection_thread = threading.Thread(target=self._collect_system_metrics)
        self._collection_thread.daemon = True
        self._collection_thread.start()
        
        self.logger.info("Started metrics collection")
    
    def stop_collection(self) -> None:
        """Stop collecting system metrics."""
        if not self._collecting:
            return
            
        self._collecting = False
        
        if self._collection_thread and self._collection_thread.is_alive():
            self._collection_thread.join(timeout=5)
        
        self.logger.info("Stopped metrics collection")
    
    def _collect_system_metrics(self) -> None:
        """Collect system metrics in background thread."""
        import psutil
        
        while self._collecting:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Network stats
                network = psutil.net_io_counters()
                
                metric = {
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used': memory.used,
                    'memory_available': memory.available,
                    'disk_percent': (disk.used / disk.total) * 100,
                    'disk_used': disk.used,
                    'disk_free': disk.free,
                    'network_bytes_sent': network.bytes_sent,
                    'network_bytes_recv': network.bytes_recv,
                }
                
                self.system_metrics.append(metric)
                
                # Sleep until next collection
                time.sleep(self.interval)
                
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {str(e)}")
                time.sleep(self.interval)
    
    def add_metric(self, name: str, value: Any, unit: str, metadata: Dict[str, Any] = None) -> None:
        """Add a custom metric."""
        metric = BenchmarkMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        self.metrics.append(metric)
        self.logger.debug(f"Added metric: {name} = {value} {unit}")
    
    def add_query_result(self, result: QueryResult) -> None:
        """Add a query execution result."""
        self.query_results.append(result)
        
        self.logger.info(
            f"Query {result.query_name} ({result.format}/{result.compression}) "
            f"completed in {format_duration(result.execution_time)}"
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get benchmark summary statistics."""
        total_runtime = time.time() - self.start_time
        
        # Query statistics
        query_stats = {
            'total_queries': len(self.query_results),
            'successful_queries': len([r for r in self.query_results if r.error is None]),
            'failed_queries': len([r for r in self.query_results if r.error is not None]),
            'total_execution_time': sum(r.execution_time for r in self.query_results),
            'avg_execution_time': 0,
            'min_execution_time': 0,
            'max_execution_time': 0,
        }
        
        if self.query_results:
            execution_times = [r.execution_time for r in self.query_results if r.error is None]
            if execution_times:
                query_stats.update({
                    'avg_execution_time': sum(execution_times) / len(execution_times),
                    'min_execution_time': min(execution_times),
                    'max_execution_time': max(execution_times),
                })
        
        # Format comparison
        format_stats = {}
        for result in self.query_results:
            if result.error is None:
                key = f"{result.format}_{result.compression}"
                if key not in format_stats:
                    format_stats[key] = {
                        'count': 0,
                        'total_time': 0,
                        'total_bytes_read': 0,
                        'total_bytes_written': 0,
                    }
                
                format_stats[key]['count'] += 1
                format_stats[key]['total_time'] += result.execution_time
                format_stats[key]['total_bytes_read'] += result.bytes_read
                format_stats[key]['total_bytes_written'] += result.bytes_written
        
        # Calculate averages for formats
        for stats in format_stats.values():
            if stats['count'] > 0:
                stats['avg_time'] = stats['total_time'] / stats['count']
                stats['avg_bytes_read'] = stats['total_bytes_read'] / stats['count']
                stats['avg_bytes_written'] = stats['total_bytes_written'] / stats['count']
        
        # System resource usage
        system_stats = {}
        if self.system_metrics:
            cpu_values = [m['cpu_percent'] for m in self.system_metrics]
            memory_values = [m['memory_percent'] for m in self.system_metrics]
            
            system_stats = {
                'avg_cpu_percent': sum(cpu_values) / len(cpu_values),
                'max_cpu_percent': max(cpu_values),
                'avg_memory_percent': sum(memory_values) / len(memory_values),
                'max_memory_percent': max(memory_values),
                'samples_collected': len(self.system_metrics),
            }
        
        return {
            'benchmark_info': {
                'start_time': self.start_time,
                'end_time': time.time(),
                'total_runtime': total_runtime,
                'timestamp': get_timestamp(),
            },
            'query_statistics': query_stats,
            'format_comparison': format_stats,
            'system_resources': system_stats,
            'custom_metrics': len(self.metrics),
        }
    
    def save_results(self, filename_prefix: str = "benchmark") -> Dict[str, str]:
        """Save all collected results to files."""
        timestamp = get_timestamp()
        files_saved = {}
        
        # Save summary
        summary_file = self.output_dir / f"{filename_prefix}_summary_{timestamp}.json"
        summary = self.get_summary()
        save_json(summary, str(summary_file))
        files_saved['summary'] = str(summary_file)
        
        # Save detailed query results
        results_file = self.output_dir / f"{filename_prefix}_results_{timestamp}.json"
        results_data = {
            'query_results': [r.to_dict() for r in self.query_results],
            'custom_metrics': [m.to_dict() for m in self.metrics],
        }
        save_json(results_data, str(results_file))
        files_saved['results'] = str(results_file)
        
        # Save system metrics
        if self.system_metrics:
            system_file = self.output_dir / f"{filename_prefix}_system_{timestamp}.json"
            save_json({'system_metrics': self.system_metrics}, str(system_file))
            files_saved['system'] = str(system_file)
        
        # Save raw data for analysis
        raw_file = self.output_dir / f"{filename_prefix}_raw_{timestamp}.json"
        raw_data = {
            'summary': summary,
            'query_results': [r.to_dict() for r in self.query_results],
            'custom_metrics': [m.to_dict() for m in self.metrics],
            'system_metrics': self.system_metrics,
        }
        save_json(raw_data, str(raw_file))
        files_saved['raw'] = str(raw_file)
        
        self.logger.info(f"Results saved to {len(files_saved)} files")
        return files_saved
    
    def generate_report(self) -> str:
        """Generate a text report of the benchmark results."""
        summary = self.get_summary()
        
        report_lines = [
            "=" * 60,
            "ICEBERG BENCHMARK REPORT",
            "=" * 60,
            "",
            f"Benchmark completed at: {datetime.fromtimestamp(summary['benchmark_info']['end_time'])}",
            f"Total runtime: {format_duration(summary['benchmark_info']['total_runtime'])}",
            "",
            "QUERY STATISTICS:",
            f"  Total queries: {summary['query_statistics']['total_queries']}",
            f"  Successful: {summary['query_statistics']['successful_queries']}",
            f"  Failed: {summary['query_statistics']['failed_queries']}",
            f"  Average execution time: {format_duration(summary['query_statistics']['avg_execution_time'])}",
            f"  Min execution time: {format_duration(summary['query_statistics']['min_execution_time'])}",
            f"  Max execution time: {format_duration(summary['query_statistics']['max_execution_time'])}",
            "",
            "FORMAT COMPARISON:",
        ]
        
        # Add format comparison
        for format_name, stats in summary['format_comparison'].items():
            report_lines.extend([
                f"  {format_name}:",
                f"    Queries: {stats['count']}",
                f"    Avg time: {format_duration(stats['avg_time'])}",
                f"    Avg bytes read: {stats['avg_bytes_read']:,}",
                f"    Avg bytes written: {stats['avg_bytes_written']:,}",
                "",
            ])
        
        # Add system resources
        if summary['system_resources']:
            report_lines.extend([
                "SYSTEM RESOURCES:",
                f"  Average CPU: {summary['system_resources']['avg_cpu_percent']:.1f}%",
                f"  Peak CPU: {summary['system_resources']['max_cpu_percent']:.1f}%",
                f"  Average Memory: {summary['system_resources']['avg_memory_percent']:.1f}%",
                f"  Peak Memory: {summary['system_resources']['max_memory_percent']:.1f}%",
                "",
            ])
        
        # Add failed queries if any
        failed_queries = [r for r in self.query_results if r.error is not None]
        if failed_queries:
            report_lines.extend([
                "FAILED QUERIES:",
            ])
            for result in failed_queries:
                report_lines.append(f"  {result.query_name}: {result.error}")
            report_lines.append("")
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def get_performance_comparison(self) -> Dict[str, Any]:
        """Get detailed performance comparison between formats."""
        comparison = {}
        
        # Group results by format/compression
        groups = {}
        for result in self.query_results:
            if result.error is None:
                key = f"{result.format}_{result.compression}"
                if key not in groups:
                    groups[key] = []
                groups[key].append(result)
        
        # Calculate statistics for each group
        for group_name, results in groups.items():
            if not results:
                continue
                
            execution_times = [r.execution_time for r in results]
            bytes_read = [r.bytes_read for r in results]
            bytes_written = [r.bytes_written for r in results]
            
            comparison[group_name] = {
                'count': len(results),
                'execution_time': {
                    'avg': sum(execution_times) / len(execution_times),
                    'min': min(execution_times),
                    'max': max(execution_times),
                    'total': sum(execution_times),
                },
                'bytes_read': {
                    'avg': sum(bytes_read) / len(bytes_read),
                    'min': min(bytes_read),
                    'max': max(bytes_read),
                    'total': sum(bytes_read),
                },
                'bytes_written': {
                    'avg': sum(bytes_written) / len(bytes_written),
                    'min': min(bytes_written),
                    'max': max(bytes_written),
                    'total': sum(bytes_written),
                },
                'queries': [r.query_name for r in results],
            }
        
        return comparison


if __name__ == "__main__":
    # Simple test
    collector = MetricsCollector()
    
    # Add some test metrics
    collector.add_metric("test_metric", 42, "count")
    
    # Add test query result
    result = QueryResult(
        query_name="q1",
        format="parquet",
        compression="snappy",
        partitioning="none",
        execution_time=10.5,
        rows_read=1000,
        bytes_read=50000,
        rows_written=100,
        bytes_written=5000
    )
    collector.add_query_result(result)
    
    # Print summary
    summary = collector.get_summary()
    print(json.dumps(summary, indent=2, default=str))
