.PHONY: help setup run monitor clean check-deps build-image setup-kind deploy-k8s monitor-k8s clean-kind run-benchmark
.DEFAULT_GOAL := help

# Configuration
CLUSTER_NAME := iceberg-benchmark
NAMESPACE := iceberg-benchmark
CONFIG := small
DOCKER_IMAGE := iceberg-benchmark:latest

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Iceberg TPC-DS Benchmark - Available Commands:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make setup                    # Setup complete environment"
	@echo "  make run CONFIG=small        # Run small benchmark"
	@echo "  make run CONFIG=medium       # Run medium benchmark"
	@echo "  make monitor                 # Monitor cluster and jobs"
	@echo "  make clean                   # Clean everything"

check-deps: ## Check if required dependencies are installed
	@echo "$(BLUE)Checking dependencies...$(NC)"
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)Error: docker is required but not installed.$(NC)" >&2; exit 1; }
	@command -v kind >/dev/null 2>&1 || { echo "$(RED)Error: kind is required but not installed.$(NC)" >&2; exit 1; }
	@command -v kubectl >/dev/null 2>&1 || { echo "$(RED)Error: kubectl is required but not installed.$(NC)" >&2; exit 1; }
	@echo "$(GREEN)All dependencies are installed!$(NC)"

build-image: check-deps ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	@docker build -t $(DOCKER_IMAGE) .
	@echo "$(GREEN)Docker image built successfully!$(NC)"

setup: check-deps build-image ## Setup complete environment (cluster + deploy)
	@echo "$(BLUE)Setting up Iceberg benchmark environment...$(NC)"
	@./scripts/setup-kind-cluster.sh $(CLUSTER_NAME)
	@echo "$(GREEN)Environment setup completed!$(NC)"

run: ## Run benchmark with specified config (CONFIG=small|medium)
	@echo "$(BLUE)Running benchmark with config: $(CONFIG)$(NC)"
	@./scripts/run-benchmark.sh $(CONFIG)
	@echo "$(GREEN)Benchmark completed!$(NC)"

monitor: ## Monitor cluster and running jobs
	@echo "$(BLUE)Opening monitoring dashboard...$(NC)"
	@./scripts/monitor.sh

clean: ## Clean up everything (cluster, images, data)
	@echo "$(YELLOW)Cleaning up environment...$(NC)"
	@./scripts/cleanup.sh $(CLUSTER_NAME)
	@echo "$(GREEN)Cleanup completed!$(NC)"

logs: ## Show logs from benchmark pods
	@echo "$(BLUE)Fetching logs...$(NC)"
	@kubectl logs -n $(NAMESPACE) -l app=iceberg-benchmark --tail=100

status: ## Show cluster and pod status
	@echo "$(BLUE)Cluster Status:$(NC)"
	@kind get clusters
	@echo ""
	@echo "$(BLUE)Pod Status:$(NC)"
	@kubectl get pods -n $(NAMESPACE) 2>/dev/null || echo "No pods found"
	@echo ""
	@echo "$(BLUE)Service Status:$(NC)"
	@kubectl get svc -n $(NAMESPACE) 2>/dev/null || echo "No services found"

port-forward: ## Forward Spark UI port
	@echo "$(BLUE)Forwarding Spark UI to http://localhost:4040$(NC)"
	@kubectl port-forward -n $(NAMESPACE) svc/spark-ui 4040:4040

install-deps: ## Install required dependencies (kind, kubectl)
	@echo "$(BLUE)Installing dependencies...$(NC)"
	@./scripts/install-deps.sh
	@echo "$(GREEN)Dependencies installed!$(NC)"

validate: ## Validate configuration files
	@echo "$(BLUE)Validating configurations...$(NC)"
	@python3 src/iceberg_benchmark/validate_config.py configs/$(CONFIG).yaml
	@echo "$(GREEN)Configuration is valid!$(NC)"

results: ## Show latest benchmark results
	@echo "$(BLUE)Latest benchmark results:$(NC)"
	@ls -la results/ | head -10

# Development targets
dev-build: ## Build image for development (with cache)
	@docker build --cache-from $(DOCKER_IMAGE) -t $(DOCKER_IMAGE) .

dev-run: ## Run benchmark in development mode
	@docker run --rm -it -v $(PWD):/app $(DOCKER_IMAGE) bash

# Kind/Kubernetes specific targets
setup-kind: check-deps build-image ## Setup Kind cluster for benchmarking
	@echo "$(BLUE)Setting up Kind cluster...$(NC)"
	@./scripts/setup-kind.sh
	@echo "$(GREEN)Kind cluster setup completed!$(NC)"

deploy-k8s: ## Deploy benchmark jobs to Kubernetes
	@echo "$(BLUE)Deploying to Kubernetes...$(NC)"
	@./scripts/deploy-k8s.sh
	@echo "$(GREEN)Deployment completed!$(NC)"

monitor-k8s: ## Monitor Kubernetes jobs and pods
	@echo "$(BLUE)Monitoring Kubernetes resources...$(NC)"
	@./scripts/monitor-k8s.sh

monitor-k8s-watch: ## Monitor Kubernetes continuously
	@echo "$(BLUE)Starting continuous monitoring...$(NC)"
	@./scripts/monitor-k8s.sh --watch

clean-kind: ## Clean up Kind cluster completely
	@echo "$(YELLOW)Cleaning up Kind cluster...$(NC)"
	@kind delete cluster --name $(CLUSTER_NAME) 2>/dev/null || echo "Cluster not found"
	@echo "$(GREEN)Kind cluster cleaned up!$(NC)"

run-benchmark: ## Run complete benchmark suite with Docker
	@echo "$(BLUE)Running complete benchmark suite...$(NC)"
	@mkdir -p data output metrics
	@docker run --rm \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/output:/app/output \
		-v $(PWD)/metrics:/app/metrics \
		-v $(PWD)/scripts:/app/scripts \
		$(DOCKER_IMAGE) \
		python3 /app/scripts/corrected_format_benchmark.py
	@echo "$(GREEN)Benchmark completed! Check metrics/ for results.$(NC)"

# Quick start commands
quick-start: setup-kind deploy-k8s ## Complete setup and deploy (one command)
	@echo "$(GREEN)🎉 Quick start completed! Use 'make monitor-k8s' to check progress.$(NC)"

full-benchmark: setup-kind deploy-k8s monitor-k8s ## Complete benchmark workflow
	@echo "$(GREEN)🎉 Full benchmark workflow completed!$(NC)"

extract-k8s-results: ## Extract benchmark results from Kubernetes pods
	@echo "$(BLUE)Extracting Kubernetes benchmark results...$(NC)"
	@./scripts/extract-k8s-results.sh
	@echo "$(GREEN)Results extracted successfully!$(NC)"

view-k8s-results: extract-k8s-results ## View extracted Kubernetes results
	@echo "$(BLUE)📊 KUBERNETES BENCHMARK RESULTS$(NC)"
	@echo "=================================="
	@echo ""
	@echo "🏆 Best overall combination found:"
	@grep -A 5 "MELHOR COMBINAÇÃO GERAL" ./k8s-results/*-analysis.txt | head -10
	@echo ""
	@echo "📁 Detailed results available in: ./k8s-results/"
