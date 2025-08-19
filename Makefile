.PHONY: help setup run monitor clean check-deps build-image
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
