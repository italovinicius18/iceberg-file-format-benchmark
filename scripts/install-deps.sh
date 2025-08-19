#!/bin/bash

# Install dependencies for Iceberg benchmark
# Usage: ./install-deps.sh

set -euo pipefail

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

check_os() {
    log_info "Detecting operating system..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            OS="debian"
            log_info "Detected: Debian/Ubuntu"
        elif [ -f /etc/redhat-release ]; then
            OS="redhat"
            log_info "Detected: RedHat/CentOS/Fedora"
        else
            OS="linux"
            log_info "Detected: Generic Linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log_info "Detected: macOS"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
}

install_docker() {
    if command -v docker >/dev/null 2>&1; then
        log_success "Docker is already installed"
        docker --version
        return
    fi
    
    log_info "Installing Docker..."
    
    case $OS in
        "debian")
            # Update package index
            sudo apt-get update
            
            # Install required packages
            sudo apt-get install -y \
                ca-certificates \
                curl \
                gnupg \
                lsb-release
            
            # Add Docker's official GPG key
            sudo mkdir -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            
            # Set up repository
            echo \
                "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
                $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # Install Docker Engine
            sudo apt-get update
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        "redhat")
            sudo yum install -y yum-utils
            sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            sudo systemctl start docker
            sudo systemctl enable docker
            ;;
        "macos")
            log_warning "Please install Docker Desktop for Mac from: https://docs.docker.com/desktop/mac/install/"
            read -p "Press Enter after installing Docker Desktop..."
            ;;
    esac
    
    # Add user to docker group (Linux only)
    if [[ "$OS" != "macos" ]]; then
        sudo usermod -aG docker $USER
        log_warning "You need to log out and log back in for Docker group changes to take effect"
    fi
    
    log_success "Docker installed successfully"
}

install_kubectl() {
    if command -v kubectl >/dev/null 2>&1; then
        log_success "kubectl is already installed"
        kubectl version --client
        return
    fi
    
    log_info "Installing kubectl..."
    
    case $OS in
        "debian")
            sudo apt-get update
            sudo apt-get install -y apt-transport-https ca-certificates curl
            
            curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-archive-keyring.gpg
            echo "deb [signed-by=/etc/apt/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list
            
            sudo apt-get update
            sudo apt-get install -y kubectl
            ;;
        "redhat")
            cat <<EOF | sudo tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-\$basearch
enabled=1
gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOF
            sudo yum install -y kubectl
            ;;
        "macos")
            if command -v brew >/dev/null 2>&1; then
                brew install kubectl
            else
                curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
                chmod +x kubectl
                sudo mv kubectl /usr/local/bin/
            fi
            ;;
    esac
    
    log_success "kubectl installed successfully"
}

install_kind() {
    if command -v kind >/dev/null 2>&1; then
        log_success "Kind is already installed"
        kind version
        return
    fi
    
    log_info "Installing Kind..."
    
    # Download latest Kind release
    local kind_version=$(curl -s https://api.github.com/repos/kubernetes-sigs/kind/releases/latest | grep tag_name | cut -d '"' -f 4)
    
    case $OS in
        "linux"|"debian"|"redhat")
            curl -Lo ./kind https://kind.sigs.k8s.io/dl/${kind_version}/kind-linux-amd64
            chmod +x ./kind
            sudo mv ./kind /usr/local/bin/kind
            ;;
        "macos")
            if command -v brew >/dev/null 2>&1; then
                brew install kind
            else
                curl -Lo ./kind https://kind.sigs.k8s.io/dl/${kind_version}/kind-darwin-amd64
                chmod +x ./kind
                sudo mv ./kind /usr/local/bin/kind
            fi
            ;;
    esac
    
    log_success "Kind installed successfully"
}

install_python_deps() {
    log_info "Installing Python dependencies..."
    
    # Check Python version
    if command -v python3 >/dev/null 2>&1; then
        local python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
        log_info "Found Python version: $python_version"
        
        if [[ "$python_version" < "3.8" ]]; then
            log_warning "Python 3.8+ is recommended. Current version: $python_version"
        fi
    else
        log_error "Python 3 is not installed"
        case $OS in
            "debian")
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip
                ;;
            "redhat")
                sudo yum install -y python3 python3-pip
                ;;
            "macos")
                if command -v brew >/dev/null 2>&1; then
                    brew install python3
                else
                    log_error "Please install Python 3.8+ manually"
                    exit 1
                fi
                ;;
        esac
    fi
    
    # Install pip packages
    pip3 install --user --upgrade pip
    pip3 install --user pyyaml click
    
    log_success "Python dependencies installed"
}

verify_installation() {
    log_info "Verifying installation..."
    
    local all_good=true
    
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker not found in PATH"
        all_good=false
    else
        log_success "Docker: $(docker --version)"
    fi
    
    if ! command -v kubectl >/dev/null 2>&1; then
        log_error "kubectl not found in PATH"
        all_good=false
    else
        log_success "kubectl: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
    fi
    
    if ! command -v kind >/dev/null 2>&1; then
        log_error "Kind not found in PATH"
        all_good=false
    else
        log_success "Kind: $(kind version)"
    fi
    
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "Python 3 not found in PATH"
        all_good=false
    else
        log_success "Python: $(python3 --version)"
    fi
    
    if [ "$all_good" = true ]; then
        log_success "All dependencies are properly installed!"
        echo ""
        echo "Next steps:"
        echo "  1. If you installed Docker, you may need to log out and log back in"
        echo "  2. Run: make setup"
        echo "  3. Run: make run CONFIG=small"
    else
        log_error "Some dependencies are missing. Please check the errors above."
        exit 1
    fi
}

main() {
    log_info "Installing dependencies for Iceberg benchmark..."
    echo ""
    
    check_os
    install_docker
    install_kubectl
    install_kind
    install_python_deps
    verify_installation
    
    log_success "Dependency installation completed!"
}

main "$@"
