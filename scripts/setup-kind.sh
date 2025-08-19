#!/bin/bash
set -e

echo "🚀 Configurando cluster Kind para Iceberg Benchmark"

# Configuração do cluster
CLUSTER_NAME="iceberg-benchmark"
NAMESPACE="iceberg-benchmark"

# Verificar se cluster já existe
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "📋 Cluster ${CLUSTER_NAME} já existe"
    read -p "Deseja recriar o cluster? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️ Removendo cluster existente..."
        kind delete cluster --name ${CLUSTER_NAME}
    else
        echo "✅ Usando cluster existente"
        exit 0
    fi
fi

# Criar configuração do cluster
cat > /tmp/kind-config.yaml << EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ${CLUSTER_NAME}
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
- role: worker
  extraMounts:
  - hostPath: $(pwd)/data
    containerPath: /data
  - hostPath: $(pwd)/output
    containerPath: /output
  - hostPath: $(pwd)/metrics
    containerPath: /metrics
EOF

echo "🔧 Criando cluster Kind..."
kind create cluster --config /tmp/kind-config.yaml

echo "📦 Carregando imagem Docker no Kind..."
if docker images | grep -q iceberg-benchmark; then
    kind load docker-image iceberg-benchmark:latest --name ${CLUSTER_NAME}
else
    echo "⚠️ Imagem iceberg-benchmark não encontrada. Execute 'make build-image' primeiro."
fi

echo "🔧 Configurando kubectl context..."
kubectl cluster-info --context kind-${CLUSTER_NAME}

echo "📝 Criando namespace..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Cluster Kind configurado com sucesso!"
echo ""
echo "📋 Próximos passos:"
echo "   1. kubectl get nodes"
echo "   2. make deploy-k8s"
echo "   3. make monitor-k8s"
echo ""
echo "🗑️ Para remover: kind delete cluster --name ${CLUSTER_NAME}"
