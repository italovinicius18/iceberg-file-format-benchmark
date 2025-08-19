#!/bin/bash

# Setup Kind cluster for Iceberg benchmark
# Usage: ./setup-kind-cluster.sh [cluster-name]

set -euo pipefail

CLUSTER_NAME=${1:-"iceberg-benchmark"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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

check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    command -v docker >/dev/null 2>&1 || missing_deps+=("docker")
    command -v kind >/dev/null 2>&1 || missing_deps+=("kind")
    command -v kubectl >/dev/null 2>&1 || missing_deps+=("kubectl")
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install missing dependencies and try again"
        exit 1
    fi
    
    log_success "All dependencies are available"
}

cleanup_existing_cluster() {
    log_info "Checking for existing cluster: $CLUSTER_NAME"
    
    if kind get clusters | grep -q "^$CLUSTER_NAME$"; then
        log_warning "Cluster $CLUSTER_NAME already exists. Deleting..."
        kind delete cluster --name "$CLUSTER_NAME"
        log_success "Existing cluster deleted"
    fi
}

create_cluster() {
    log_info "Creating Kind cluster: $CLUSTER_NAME"
    
    # Ensure data and results directories exist
    mkdir -p "$PROJECT_ROOT/data"
    mkdir -p "$PROJECT_ROOT/results"
    
    # Create cluster with configuration
    kind create cluster \
        --name "$CLUSTER_NAME" \
        --config "$PROJECT_ROOT/configs/kind-cluster.yaml" \
        --wait 300s
    
    log_success "Cluster created successfully"
}

load_docker_image() {
    log_info "Loading Docker image into cluster..."
    
    # Build image if it doesn't exist
    if ! docker images | grep -q "iceberg-benchmark"; then
        log_info "Building Docker image..."
        cd "$PROJECT_ROOT"
        docker build -t iceberg-benchmark:latest .
    fi
    
    # Load image into Kind cluster
    kind load docker-image iceberg-benchmark:latest --name "$CLUSTER_NAME"
    log_success "Docker image loaded into cluster"
}

deploy_kubernetes_resources() {
    log_info "Deploying Kubernetes resources..."
    
    # Apply resources in order
    kubectl apply -f "$PROJECT_ROOT/deployment/kubernetes/namespace.yaml"
    kubectl apply -f "$PROJECT_ROOT/deployment/kubernetes/storage-services.yaml"
    kubectl apply -f "$PROJECT_ROOT/deployment/kubernetes/configmaps.yaml"
    
    # Wait for namespace to be ready
    kubectl wait --for=condition=Active namespace/iceberg-benchmark --timeout=60s
    
    # Deploy controller
    kubectl apply -f "$PROJECT_ROOT/deployment/kubernetes/jobs.yaml"
    
    log_success "Kubernetes resources deployed"
}

wait_for_pods() {
    log_info "Waiting for pods to be ready..."
    
    # Wait for controller deployment
    kubectl wait --for=condition=available deployment/benchmark-controller \
        -n iceberg-benchmark --timeout=300s
    
    log_success "All pods are ready"
}

setup_port_forwarding() {
    log_info "Setting up port forwarding..."
    
    # Kill any existing port forwards
    pkill -f "kubectl port-forward" 2>/dev/null || true
    
    # Setup port forwarding for Spark UI (background)
    kubectl port-forward -n iceberg-benchmark svc/spark-ui 4040:4040 >/dev/null 2>&1 &
    
    # Setup port forwarding for controller API (background)
    kubectl port-forward -n iceberg-benchmark svc/benchmark-service 8080:8080 >/dev/null 2>&1 &
    
    log_success "Port forwarding setup completed"
    log_info "Spark UI: http://localhost:4040"
    log_info "Controller API: http://localhost:8080"
}

display_cluster_info() {
    log_info "Cluster information:"
    echo ""
    echo "Cluster name: $CLUSTER_NAME"
    echo "Nodes:"
    kubectl get nodes
    echo ""
    echo "Pods:"
    kubectl get pods -n iceberg-benchmark
    echo ""
    echo "Services:"
    kubectl get svc -n iceberg-benchmark
    echo ""
    echo "Access URLs:"
    echo "  - Spark UI: http://localhost:4040"
    echo "  - Controller API: http://localhost:8080"
    echo ""
}

main() {
    log_info "Starting Kind cluster setup for Iceberg benchmark"
    echo ""
    
    check_dependencies
    cleanup_existing_cluster
    create_cluster
    load_docker_image
    deploy_kubernetes_resources
    wait_for_pods
    setup_port_forwarding
    
    log_success "Setup completed successfully!"
    echo ""
    display_cluster_info
    
    log_info "Next steps:"
    echo "  1. Run benchmark: make run CONFIG=small"
    echo "  2. Monitor cluster: make monitor"
    echo "  3. Check logs: make logs"
    echo "  4. Clean up: make clean"
}

# Trap to cleanup on exit
trap 'log_warning "Setup interrupted"' INT TERM

main "$@"
