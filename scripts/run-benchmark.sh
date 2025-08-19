#!/bin/bash

# Run Iceberg benchmark
# Usage: ./run-benchmark.sh [config-name]

set -euo pipefail

CONFIG=${1:-"small"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NAMESPACE="iceberg-benchmark"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_cluster() {
    log_info "Checking cluster status..."
    
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "Kubernetes cluster not accessible"
        log_info "Please run: make setup"
        exit 1
    fi
    
    if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        log_error "Namespace $NAMESPACE not found"
        log_info "Please run: make setup"
        exit 1
    fi
    
    log_success "Cluster is ready"
}

validate_config() {
    log_info "Validating configuration: $CONFIG"
    
    local config_file="$PROJECT_ROOT/configs/$CONFIG.yaml"
    
    if [ ! -f "$config_file" ]; then
        log_error "Configuration file not found: $config_file"
        log_info "Available configurations:"
        ls -1 "$PROJECT_ROOT/configs/"*.yaml 2>/dev/null | xargs -n1 basename | sed 's/.yaml$//' || echo "  None found"
        exit 1
    fi
    
    # Validate YAML syntax
    if ! python3 -c "import yaml; yaml.safe_load(open('$config_file'))" 2>/dev/null; then
        log_error "Invalid YAML syntax in configuration file"
        exit 1
    fi
    
    log_success "Configuration is valid"
}

cleanup_previous_jobs() {
    log_info "Cleaning up previous benchmark jobs..."
    
    # Delete existing benchmark jobs
    kubectl delete jobs -n "$NAMESPACE" -l component=benchmark --ignore-not-found=true
    
    # Wait for job deletion
    while kubectl get jobs -n "$NAMESPACE" -l component=benchmark 2>/dev/null | grep -q benchmark; do
        log_info "Waiting for previous jobs to be deleted..."
        sleep 5
    done
    
    log_success "Previous jobs cleaned up"
}

create_benchmark_job() {
    log_info "Creating benchmark job for configuration: $CONFIG"
    
    # Create a temporary job manifest with the specific config
    local temp_job_file=$(mktemp)
    
    cat > "$temp_job_file" << EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: iceberg-benchmark-$CONFIG-$(date +%s)
  namespace: $NAMESPACE
  labels:
    app: iceberg-benchmark
    component: benchmark
    config: $CONFIG
spec:
  ttlSecondsAfterFinished: 3600
  backoffLimit: 1
  template:
    metadata:
      labels:
        app: iceberg-benchmark
        component: benchmark
        config: $CONFIG
    spec:
      serviceAccountName: iceberg-benchmark-sa
      restartPolicy: Never
      containers:
        - name: benchmark
          image: iceberg-benchmark:latest
          imagePullPolicy: Never
          command: ["python3"]
          args: ["/app/src/iceberg_benchmark/cli.py", "run", "--config", "/app/configs/$CONFIG.yaml"]
          env:
            - name: SPARK_HOME
              value: "/opt/spark"
            # Note: TPC-DS data generation is now Spark-based (no TPCDS_HOME needed)
            - name: PYTHONPATH
              value: "/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip"
            - name: KUBERNETES_NAMESPACE
              value: "$NAMESPACE"
            - name: BENCHMARK_CONFIG
              value: "$CONFIG"
          resources:
            requests:
              memory: "2Gi"
              cpu: "1"
            limits:
              memory: "4Gi"
              cpu: "2"
          volumeMounts:
            - name: benchmark-data
              mountPath: /data
            - name: benchmark-results
              mountPath: /app/results
            - name: benchmark-config
              mountPath: /etc/spark/conf
            - name: tpcds-queries
              mountPath: /app/queries
      volumes:
        - name: benchmark-data
          persistentVolumeClaim:
            claimName: benchmark-data-pvc
        - name: benchmark-results
          persistentVolumeClaim:
            claimName: benchmark-results-pvc
        - name: benchmark-config
          configMap:
            name: benchmark-config
        - name: tpcds-queries
          configMap:
            name: tpcds-queries
EOF

    # Apply the job
    kubectl apply -f "$temp_job_file"
    rm "$temp_job_file"
    
    log_success "Benchmark job created"
}

monitor_job() {
    log_info "Monitoring benchmark job..."
    
    # Get the most recent benchmark job
    local job_name=$(kubectl get jobs -n "$NAMESPACE" -l component=benchmark,config="$CONFIG" \
        --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}' 2>/dev/null)
    
    if [ -z "$job_name" ]; then
        log_error "No benchmark job found"
        exit 1
    fi
    
    log_info "Following job: $job_name"
    
    # Wait for job to start
    kubectl wait --for=condition=Progressing job/"$job_name" -n "$NAMESPACE" --timeout=300s || true
    
    # Get pod name
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l job-name="$job_name" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -n "$pod_name" ]; then
        log_info "Following logs from pod: $pod_name"
        
        # Stream logs
        kubectl logs -n "$NAMESPACE" "$pod_name" -f || true
        
        # Check final status
        if kubectl wait --for=condition=Complete job/"$job_name" -n "$NAMESPACE" --timeout=1800s; then
            log_success "Benchmark completed successfully"
        else
            log_warning "Benchmark may have failed or timed out"
            kubectl describe job "$job_name" -n "$NAMESPACE"
        fi
    else
        log_error "Could not find benchmark pod"
        kubectl describe job "$job_name" -n "$NAMESPACE"
    fi
}

show_results() {
    log_info "Benchmark results:"
    
    # Show recent results
    if [ -d "$PROJECT_ROOT/results" ]; then
        echo ""
        echo "Recent result files:"
        ls -la "$PROJECT_ROOT/results/" | tail -10
        
        # Show latest result summary if available
        local latest_result=$(ls -t "$PROJECT_ROOT/results/"*summary*.json 2>/dev/null | head -1)
        if [ -n "$latest_result" ]; then
            echo ""
            echo "Latest result summary:"
            cat "$latest_result" | python3 -m json.tool 2>/dev/null || cat "$latest_result"
        fi
    else
        log_warning "Results directory not found"
    fi
}

cleanup_on_exit() {
    log_info "Cleaning up..."
    # Add any cleanup logic here
}

main() {
    log_info "Starting Iceberg benchmark with configuration: $CONFIG"
    echo ""
    
    check_cluster
    validate_config
    cleanup_previous_jobs
    create_benchmark_job
    monitor_job
    show_results
    
    log_success "Benchmark run completed!"
    echo ""
    log_info "To view detailed results:"
    echo "  - Check results directory: ls -la results/"
    echo "  - View Spark UI: http://localhost:4040"
    echo "  - Check pod logs: kubectl logs -n $NAMESPACE -l config=$CONFIG"
}

# Trap to cleanup on exit
trap cleanup_on_exit INT TERM

main "$@"
