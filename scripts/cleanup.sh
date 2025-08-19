#!/bin/bash

# Cleanup Iceberg benchmark environment
# Usage: ./cleanup.sh [cluster-name]

set -euo pipefail

CLUSTER_NAME=${1:-"iceberg-benchmark"}
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

confirm_cleanup() {
    echo ""
    log_warning "This will delete:"
    echo "  - Kind cluster: $CLUSTER_NAME"
    echo "  - All Kubernetes resources"
    echo "  - Docker images (optional)"
    echo "  - Generated data (optional)"
    echo ""
    
    read -p "Are you sure you want to proceed? (y/N): " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "Cleanup cancelled"
        exit 0
    fi
}

stop_port_forwards() {
    log_info "Stopping port forwards..."
    
    # Kill any kubectl port-forward processes
    pkill -f "kubectl port-forward" 2>/dev/null || true
    
    log_success "Port forwards stopped"
}

cleanup_kubernetes_resources() {
    log_info "Cleaning up Kubernetes resources..."
    
    if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        # Delete all resources in namespace
        kubectl delete all --all -n "$NAMESPACE" --ignore-not-found=true
        
        # Delete PVCs (they might not be deleted with 'all')
        kubectl delete pvc --all -n "$NAMESPACE" --ignore-not-found=true
        
        # Delete configmaps and secrets
        kubectl delete configmaps --all -n "$NAMESPACE" --ignore-not-found=true
        kubectl delete secrets --all -n "$NAMESPACE" --ignore-not-found=true
        
        # Delete the namespace
        kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
        
        log_success "Kubernetes resources cleaned up"
    else
        log_info "Namespace $NAMESPACE not found, skipping K8s cleanup"
    fi
}

delete_kind_cluster() {
    log_info "Deleting Kind cluster: $CLUSTER_NAME"
    
    if kind get clusters | grep -q "^$CLUSTER_NAME$"; then
        kind delete cluster --name "$CLUSTER_NAME"
        log_success "Kind cluster deleted"
    else
        log_info "Kind cluster $CLUSTER_NAME not found"
    fi
}

cleanup_docker_images() {
    echo ""
    read -p "Do you want to remove Docker images? (y/N): " remove_images
    
    if [ "$remove_images" = "y" ] || [ "$remove_images" = "Y" ]; then
        log_info "Removing Docker images..."
        
        # Remove benchmark image
        if docker images | grep -q "iceberg-benchmark"; then
            docker rmi iceberg-benchmark:latest 2>/dev/null || true
            log_success "Benchmark image removed"
        fi
        
        # Optionally remove unused images
        read -p "Remove all unused Docker images? (y/N): " remove_unused
        if [ "$remove_unused" = "y" ] || [ "$remove_unused" = "Y" ]; then
            docker system prune -f
            log_success "Unused Docker images removed"
        fi
    else
        log_info "Keeping Docker images"
    fi
}

cleanup_data_directories() {
    echo ""
    read -p "Do you want to remove generated data and results? (y/N): " remove_data
    
    if [ "$remove_data" = "y" ] || [ "$remove_data" = "Y" ]; then
        log_info "Removing data and results..."
        
        # Backup results if they exist
        if [ -d "results" ] && [ "$(ls -A results)" ]; then
            local backup_dir="results-backup-$(date +%Y%m%d-%H%M%S)"
            mv results "$backup_dir"
            log_info "Results backed up to: $backup_dir"
        fi
        
        # Clean directories
        rm -rf data/* 2>/dev/null || true
        mkdir -p data results
        
        log_success "Data directories cleaned"
    else
        log_info "Keeping data and results"
    fi
}

cleanup_temporary_files() {
    log_info "Cleaning up temporary files..."
    
    # Remove any temporary files
    rm -f /tmp/iceberg-benchmark-* 2>/dev/null || true
    rm -f /tmp/benchmark-job-* 2>/dev/null || true
    
    # Clean kubectl cache if needed
    kubectl cache flush 2>/dev/null || true
    
    log_success "Temporary files cleaned"
}

show_cleanup_summary() {
    echo ""
    echo "========================================"
    echo "         CLEANUP SUMMARY"
    echo "========================================"
    echo ""
    
    # Check what's left
    if kind get clusters 2>/dev/null | grep -q "$CLUSTER_NAME"; then
        log_warning "Kind cluster still exists: $CLUSTER_NAME"
    else
        log_success "Kind cluster removed: $CLUSTER_NAME"
    fi
    
    if docker images | grep -q "iceberg-benchmark"; then
        log_info "Docker image still exists: iceberg-benchmark:latest"
    else
        log_success "Docker image removed: iceberg-benchmark:latest"
    fi
    
    if [ -d "data" ] && [ "$(ls -A data 2>/dev/null)" ]; then
        log_info "Data directory contains files: $(ls data | wc -l) files"
    else
        log_success "Data directory is clean"
    fi
    
    if [ -d "results" ] && [ "$(ls -A results 2>/dev/null)" ]; then
        log_info "Results directory contains files: $(ls results | wc -l) files"
    else
        log_success "Results directory is clean"
    fi
    
    echo ""
    log_success "Cleanup completed!"
    echo ""
    echo "To restart the benchmark:"
    echo "  make setup    # Setup new environment"
    echo "  make run      # Run benchmark"
}

main() {
    log_info "Starting cleanup of Iceberg benchmark environment"
    
    confirm_cleanup
    
    stop_port_forwards
    cleanup_kubernetes_resources
    delete_kind_cluster
    cleanup_docker_images
    cleanup_data_directories
    cleanup_temporary_files
    
    show_cleanup_summary
}

main "$@"
