#!/bin/bash

# Monitor Iceberg benchmark cluster
# Usage: ./monitor.sh

set -euo pipefail

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
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "Kubernetes cluster not accessible"
        exit 1
    fi
    
    if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        log_error "Namespace $NAMESPACE not found"
        exit 1
    fi
}

show_cluster_overview() {
    echo "========================================"
    echo "         CLUSTER OVERVIEW"
    echo "========================================"
    echo ""
    
    echo "Cluster Info:"
    kubectl cluster-info
    echo ""
    
    echo "Nodes:"
    kubectl get nodes -o wide
    echo ""
    
    echo "Namespace Resources:"
    kubectl get all -n "$NAMESPACE"
    echo ""
}

show_pod_details() {
    echo "========================================"
    echo "          POD DETAILS"
    echo "========================================"
    echo ""
    
    local pods=$(kubectl get pods -n "$NAMESPACE" --no-headers -o custom-columns=":metadata.name")
    
    if [ -z "$pods" ]; then
        log_warning "No pods found in namespace $NAMESPACE"
        return
    fi
    
    for pod in $pods; do
        echo "Pod: $pod"
        echo "Status: $(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.phase}')"
        echo "Ready: $(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].ready}')"
        echo "Restarts: $(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].restartCount}')"
        
        # Show resource usage if metrics server is available
        if kubectl top pod "$pod" -n "$NAMESPACE" >/dev/null 2>&1; then
            echo "Resource Usage:"
            kubectl top pod "$pod" -n "$NAMESPACE" --no-headers
        fi
        
        echo "Events:"
        kubectl get events -n "$NAMESPACE" --field-selector involvedObject.name="$pod" --sort-by='.lastTimestamp' | tail -3
        echo ""
        echo "----------------------------------------"
    done
}

show_job_status() {
    echo "========================================"
    echo "         JOB STATUS"
    echo "========================================"
    echo ""
    
    local jobs=$(kubectl get jobs -n "$NAMESPACE" --no-headers -o custom-columns=":metadata.name")
    
    if [ -z "$jobs" ]; then
        log_warning "No jobs found in namespace $NAMESPACE"
        return
    fi
    
    for job in $jobs; do
        echo "Job: $job"
        echo "Status:"
        kubectl describe job "$job" -n "$NAMESPACE" | grep -A 10 "Conditions:"
        echo ""
        
        # Show job logs
        local pod_name=$(kubectl get pods -n "$NAMESPACE" -l job-name="$job" \
            -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [ -n "$pod_name" ]; then
            echo "Recent logs from $pod_name:"
            kubectl logs "$pod_name" -n "$NAMESPACE" --tail=10 2>/dev/null || echo "No logs available"
        fi
        
        echo "----------------------------------------"
    done
}

show_storage_status() {
    echo "========================================"
    echo "        STORAGE STATUS"
    echo "========================================"
    echo ""
    
    echo "Persistent Volume Claims:"
    kubectl get pvc -n "$NAMESPACE"
    echo ""
    
    echo "Persistent Volumes:"
    kubectl get pv | grep "$NAMESPACE" || echo "No PVs found for namespace $NAMESPACE"
    echo ""
}

show_network_status() {
    echo "========================================"
    echo "        NETWORK STATUS"
    echo "========================================"
    echo ""
    
    echo "Services:"
    kubectl get svc -n "$NAMESPACE"
    echo ""
    
    echo "Endpoints:"
    kubectl get endpoints -n "$NAMESPACE"
    echo ""
    
    # Check port forwarding
    if pgrep -f "kubectl port-forward" >/dev/null; then
        echo "Active port forwards:"
        ps aux | grep "kubectl port-forward" | grep -v grep
    else
        log_warning "No active port forwards detected"
        log_info "To setup port forwarding: kubectl port-forward -n $NAMESPACE svc/spark-ui 4040:4040"
    fi
    echo ""
}

show_access_urls() {
    echo "========================================"
    echo "        ACCESS URLS"
    echo "========================================"
    echo ""
    
    # Check if services are accessible
    if kubectl get svc spark-ui -n "$NAMESPACE" >/dev/null 2>&1; then
        echo "Spark UI: http://localhost:4040"
        echo "  (requires: kubectl port-forward -n $NAMESPACE svc/spark-ui 4040:4040)"
    fi
    
    if kubectl get svc benchmark-service -n "$NAMESPACE" >/dev/null 2>&1; then
        echo "Controller API: http://localhost:8080"
        echo "  (requires: kubectl port-forward -n $NAMESPACE svc/benchmark-service 8080:8080)"
    fi
    
    echo ""
    echo "To access services:"
    echo "  make port-forward    # Setup all port forwards"
    echo ""
}

show_recent_logs() {
    echo "========================================"
    echo "        RECENT LOGS"
    echo "========================================"
    echo ""
    
    local benchmark_pods=$(kubectl get pods -n "$NAMESPACE" -l component=benchmark \
        --no-headers -o custom-columns=":metadata.name" 2>/dev/null)
    
    if [ -n "$benchmark_pods" ]; then
        for pod in $benchmark_pods; do
            echo "Recent logs from $pod:"
            kubectl logs "$pod" -n "$NAMESPACE" --tail=20 2>/dev/null || echo "No logs available"
            echo "----------------------------------------"
        done
    else
        log_info "No benchmark pods found"
    fi
}

interactive_mode() {
    while true; do
        clear
        echo ""
        echo "ICEBERG BENCHMARK MONITOR"
        echo "========================="
        echo ""
        echo "1) Cluster Overview"
        echo "2) Pod Details"
        echo "3) Job Status"
        echo "4) Storage Status"
        echo "5) Network Status"
        echo "6) Recent Logs"
        echo "7) Refresh All"
        echo "8) Shell Access"
        echo "q) Quit"
        echo ""
        read -p "Select option: " choice
        
        case $choice in
            1) show_cluster_overview ;;
            2) show_pod_details ;;
            3) show_job_status ;;
            4) show_storage_status ;;
            5) show_network_status ;;
            6) show_recent_logs ;;
            7) 
                show_cluster_overview
                show_pod_details
                show_job_status
                show_storage_status
                show_network_status
                show_access_urls
                ;;
            8)
                echo "Available pods for shell access:"
                kubectl get pods -n "$NAMESPACE" --no-headers -o custom-columns=":metadata.name"
                read -p "Enter pod name: " pod_name
                if [ -n "$pod_name" ]; then
                    kubectl exec -it "$pod_name" -n "$NAMESPACE" -- bash
                fi
                ;;
            q|Q) break ;;
            *) echo "Invalid option" ;;
        esac
        
        if [ "$choice" != "7" ] && [ "$choice" != "8" ]; then
            echo ""
            read -p "Press Enter to continue..."
        fi
    done
}

main() {
    check_cluster
    
    if [ "${1:-}" = "--interactive" ] || [ "${1:-}" = "-i" ]; then
        interactive_mode
    else
        # Show all information once
        show_cluster_overview
        show_pod_details
        show_job_status
        show_storage_status
        show_network_status
        show_access_urls
        show_recent_logs
        
        echo ""
        log_info "For interactive monitoring, run: $0 --interactive"
        log_info "For continuous monitoring, run: watch -n 5 $0"
    fi
}

main "$@"
