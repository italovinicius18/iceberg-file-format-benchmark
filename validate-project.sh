#!/bin/bash

# Quick validation script to demonstrate the project structure
# Usage: ./validate-project.sh

set -e

echo "🚀 Iceberg File Format Benchmark - Project Validation"
echo "======================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}1. Project Structure Validation${NC}"
echo "--------------------------------------"

# Check directories
directories=("configs" "deployment/kubernetes" "scripts" "src/iceberg_benchmark" "data" "results")
for dir in "${directories[@]}"; do
    if [ -d "$dir" ]; then
        echo "✓ Directory: $dir"
    else
        echo "✗ Missing directory: $dir"
    fi
done

echo ""
echo -e "${BLUE}2. Configuration Files Validation${NC}"
echo "--------------------------------------"

# Check configuration files
configs=("configs/small.yaml" "configs/medium.yaml" "configs/kind-cluster.yaml")
for config in "${configs[@]}"; do
    if [ -f "$config" ]; then
        echo "✓ Configuration: $config"
        # Basic YAML syntax check
        if python3 -c "import yaml; yaml.safe_load(open('$config'))" 2>/dev/null; then
            echo "  ✓ Valid YAML syntax"
        else
            echo "  ✗ Invalid YAML syntax"
        fi
    else
        echo "✗ Missing configuration: $config"
    fi
done

echo ""
echo -e "${BLUE}3. Scripts Validation${NC}"
echo "--------------------------------------"

# Check scripts
scripts=("scripts/setup-kind-cluster.sh" "scripts/run-benchmark.sh" "scripts/monitor.sh" "scripts/cleanup.sh" "scripts/install-deps.sh")
for script in "${scripts[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo "✓ Script: $script (executable)"
        else
            echo "⚠ Script: $script (not executable)"
        fi
    else
        echo "✗ Missing script: $script"
    fi
done

echo ""
echo -e "${BLUE}4. Python Package Validation${NC}"
echo "--------------------------------------"

# Check Python modules
python_modules=("src/iceberg_benchmark/__init__.py" "src/iceberg_benchmark/config.py" "src/iceberg_benchmark/benchmark.py" "src/iceberg_benchmark/metrics.py" "src/iceberg_benchmark/utils.py" "src/iceberg_benchmark/cli.py")
for module in "${python_modules[@]}"; do
    if [ -f "$module" ]; then
        echo "✓ Python module: $module"
    else
        echo "✗ Missing module: $module"
    fi
done

echo ""
echo -e "${BLUE}5. Kubernetes Manifests Validation${NC}"
echo "--------------------------------------"

# Check Kubernetes manifests
manifests=("deployment/kubernetes/namespace.yaml" "deployment/kubernetes/configmaps.yaml" "deployment/kubernetes/storage-services.yaml" "deployment/kubernetes/jobs.yaml")
for manifest in "${manifests[@]}"; do
    if [ -f "$manifest" ]; then
        echo "✓ Kubernetes manifest: $manifest"
    else
        echo "✗ Missing manifest: $manifest"
    fi
done

echo ""
echo -e "${BLUE}6. Core Files Validation${NC}"
echo "--------------------------------------"

# Check core files
core_files=("Dockerfile" "Makefile" "README.md" "requirements.txt" "LICENSE" ".gitignore")
for file in "${core_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ Core file: $file"
    else
        echo "✗ Missing file: $file"
    fi
done

echo ""
echo -e "${BLUE}7. Quick Functionality Test${NC}"
echo "--------------------------------------"

# Test Makefile
echo "Testing Makefile help command:"
if make help >/dev/null 2>&1; then
    echo "✓ Makefile is functional"
else
    echo "✗ Makefile has issues"
fi

# Test configuration parsing
echo "Testing configuration parsing:"
if python3 -c "import yaml; config = yaml.safe_load(open('configs/small.yaml')); print(f\"Config name: {config.get('benchmark', {}).get('name', 'Unknown')}\")" 2>/dev/null; then
    echo "✓ Configuration parsing works"
else
    echo "✗ Configuration parsing failed"
fi

echo ""
echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}Project validation completed!${NC}"
echo ""
echo -e "${YELLOW}Next steps to run the benchmark:${NC}"
echo "1. Install dependencies: make install-deps"
echo "2. Setup environment: make setup"
echo "3. Run benchmark: make run CONFIG=small"
echo "4. Monitor execution: make monitor"
echo "5. Clean up: make clean"
echo ""
echo "For detailed usage, see README.md"
