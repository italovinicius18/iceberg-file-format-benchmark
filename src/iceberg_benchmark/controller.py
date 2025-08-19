"""
Kubernetes controller for managing Iceberg benchmark jobs.

This module provides a simple web API for monitoring and controlling
benchmark jobs running on Kubernetes.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    from flask import Flask, jsonify, request
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
except ImportError:
    print("Warning: Flask or Kubernetes client not available")


class BenchmarkController:
    """Controller for managing benchmark jobs on Kubernetes."""
    
    def __init__(self, namespace: str = "iceberg-benchmark"):
        self.namespace = namespace
        self.results_dir = Path("/app/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Kubernetes client
        try:
            # Try to load in-cluster config first
            config.load_incluster_config()
        except:
            try:
                # Fallback to local kubeconfig
                config.load_kube_config()
            except:
                print("Warning: Could not load Kubernetes configuration")
        
        self.k8s_batch = client.BatchV1Api()
        self.k8s_core = client.CoreV1Api()
        
    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get list of benchmark jobs."""
        try:
            jobs_list = self.k8s_batch.list_namespaced_job(
                namespace=self.namespace,
                label_selector="app=iceberg-benchmark"
            )
            
            jobs = []
            for job in jobs_list.items:
                job_info = {
                    'name': job.metadata.name,
                    'status': self._get_job_status(job),
                    'created': job.metadata.creation_timestamp.isoformat() if job.metadata.creation_timestamp else None,
                    'labels': job.metadata.labels or {},
                    'spec': {
                        'parallelism': job.spec.parallelism,
                        'completions': job.spec.completions,
                        'backoff_limit': job.spec.backoff_limit,
                    }
                }
                
                if job.status:
                    job_info['status_info'] = {
                        'active': job.status.active or 0,
                        'succeeded': job.status.succeeded or 0,
                        'failed': job.status.failed or 0,
                        'start_time': job.status.start_time.isoformat() if job.status.start_time else None,
                        'completion_time': job.status.completion_time.isoformat() if job.status.completion_time else None,
                    }
                
                jobs.append(job_info)
            
            return jobs
            
        except ApiException as e:
            print(f"Error getting jobs: {e}")
            return []
    
    def _get_job_status(self, job) -> str:
        """Get human-readable job status."""
        if not job.status:
            return "Unknown"
        
        if job.status.succeeded and job.status.succeeded > 0:
            return "Completed"
        elif job.status.failed and job.status.failed > 0:
            return "Failed"
        elif job.status.active and job.status.active > 0:
            return "Running"
        else:
            return "Pending"
    
    def get_job_logs(self, job_name: str) -> Dict[str, Any]:
        """Get logs for a specific job."""
        try:
            # Get pods for this job
            pods = self.k8s_core.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=f"job-name={job_name}"
            )
            
            logs_data = {}
            for pod in pods.items:
                pod_name = pod.metadata.name
                
                try:
                    logs = self.k8s_core.read_namespaced_pod_log(
                        name=pod_name,
                        namespace=self.namespace,
                        tail_lines=100
                    )
                    logs_data[pod_name] = logs
                except ApiException as e:
                    logs_data[pod_name] = f"Error getting logs: {e}"
            
            return {
                'job_name': job_name,
                'pod_logs': logs_data
            }
            
        except ApiException as e:
            return {
                'job_name': job_name,
                'error': str(e)
            }
    
    def get_results(self) -> List[Dict[str, Any]]:
        """Get list of available results."""
        results = []
        
        try:
            for result_file in self.results_dir.glob("*_summary_*.json"):
                try:
                    with open(result_file, 'r') as f:
                        result_data = json.load(f)
                    
                    result_info = {
                        'filename': result_file.name,
                        'path': str(result_file),
                        'size': result_file.stat().st_size,
                        'modified': datetime.fromtimestamp(result_file.stat().st_mtime).isoformat(),
                        'benchmark_info': result_data.get('benchmark_info', {}),
                        'query_statistics': result_data.get('query_statistics', {}),
                    }
                    
                    results.append(result_info)
                    
                except Exception as e:
                    print(f"Error reading result file {result_file}: {e}")
        
        except Exception as e:
            print(f"Error listing results: {e}")
        
        return sorted(results, key=lambda x: x['modified'], reverse=True)
    
    def get_result_details(self, filename: str) -> Dict[str, Any]:
        """Get detailed results from a specific file."""
        result_file = self.results_dir / filename
        
        if not result_file.exists():
            return {'error': 'Result file not found'}
        
        try:
            with open(result_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            return {'error': f'Error reading result file: {str(e)}'}
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status information."""
        try:
            # Get nodes
            nodes = self.k8s_core.list_node()
            node_info = []
            
            for node in nodes.items:
                node_data = {
                    'name': node.metadata.name,
                    'status': 'Ready' if any(
                        condition.type == 'Ready' and condition.status == 'True'
                        for condition in node.status.conditions or []
                    ) else 'NotReady',
                    'roles': list(node.metadata.labels.get('node-role.kubernetes.io', {}).keys()),
                    'version': node.status.node_info.kubelet_version if node.status.node_info else None,
                }
                node_info.append(node_data)
            
            # Get pods in namespace
            pods = self.k8s_core.list_namespaced_pod(namespace=self.namespace)
            pod_info = []
            
            for pod in pods.items:
                pod_data = {
                    'name': pod.metadata.name,
                    'status': pod.status.phase,
                    'node': pod.spec.node_name,
                    'created': pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                }
                pod_info.append(pod_data)
            
            return {
                'namespace': self.namespace,
                'nodes': node_info,
                'pods': pod_info,
                'timestamp': datetime.now().isoformat(),
            }
            
        except ApiException as e:
            return {'error': f'Error getting cluster status: {str(e)}'}


# Flask web application
app = Flask(__name__)
controller = BenchmarkController(
    namespace=os.getenv('KUBERNETES_NAMESPACE', 'iceberg-benchmark')
)


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/jobs')
def get_jobs():
    """Get list of benchmark jobs."""
    jobs = controller.get_jobs()
    return jsonify({
        'jobs': jobs,
        'count': len(jobs),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/jobs/<job_name>/logs')
def get_job_logs(job_name):
    """Get logs for a specific job."""
    logs = controller.get_job_logs(job_name)
    return jsonify(logs)


@app.route('/results')
def get_results():
    """Get list of available results."""
    results = controller.get_results()
    return jsonify({
        'results': results,
        'count': len(results),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/results/<filename>')
def get_result_details(filename):
    """Get detailed results from a specific file."""
    result = controller.get_result_details(filename)
    return jsonify(result)


@app.route('/cluster')
def get_cluster_status():
    """Get cluster status."""
    status = controller.get_cluster_status()
    return jsonify(status)


@app.route('/metrics')
def get_metrics():
    """Get current metrics."""
    # This could be extended to collect real-time metrics
    return jsonify({
        'jobs': len(controller.get_jobs()),
        'results': len(controller.get_results()),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/')
def index():
    """Simple status page."""
    return jsonify({
        'service': 'Iceberg Benchmark Controller',
        'version': '1.0.0',
        'namespace': controller.namespace,
        'endpoints': [
            '/health',
            '/jobs',
            '/jobs/<job_name>/logs',
            '/results',
            '/results/<filename>',
            '/cluster',
            '/metrics'
        ],
        'timestamp': datetime.now().isoformat()
    })


if __name__ == "__main__":
    # Run the Flask application
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    print(f"Starting Iceberg Benchmark Controller on port {port}")
    print(f"Namespace: {controller.namespace}")
    print(f"Results directory: {controller.results_dir}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
