#!/bin/bash
set -e

echo "🚀 Deploy do Iceberg Benchmark no Kubernetes"

NAMESPACE="iceberg-benchmark"
CLUSTER_NAME="iceberg-benchmark"

# Verificar se kubectl está configurado
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl não está configurado. Execute 'scripts/setup-kind.sh' primeiro."
    exit 1
fi

echo "📦 Verificando imagem Docker..."
if ! docker images | grep -q iceberg-benchmark; then
    echo "⚠️ Imagem iceberg-benchmark não encontrada. Fazendo build..."
    make build-image
fi

echo "📦 Carregando imagem no Kind..."
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    kind load docker-image iceberg-benchmark:latest --name ${CLUSTER_NAME}
else
    echo "⚠️ Cluster Kind não encontrado. Execute 'scripts/setup-kind.sh' primeiro."
    exit 1
fi

echo "📝 Aplicando manifestos Kubernetes..."

# Aplicar na ordem correta
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/storage.yaml
kubectl apply -f k8s/configmap.yaml

# Aguardar PVCs
echo "⏳ Aguardando PVCs..."
kubectl wait --for=condition=Bound pvc/benchmark-data-pvc -n ${NAMESPACE} --timeout=120s
kubectl wait --for=condition=Bound pvc/benchmark-output-pvc -n ${NAMESPACE} --timeout=120s
kubectl wait --for=condition=Bound pvc/benchmark-metrics-pvc -n ${NAMESPACE} --timeout=120s

echo "🎯 Deploy de Jobs..."
kubectl apply -f k8s/jobs.yaml

echo "✅ Deploy concluído!"
echo ""
echo "📋 Status do cluster:"
kubectl get pods -n ${NAMESPACE}
echo ""
echo "📊 Comandos úteis:"
echo "   kubectl get jobs -n ${NAMESPACE}"
echo "   kubectl get pods -n ${NAMESPACE}"
echo "   kubectl logs -f <pod-name> -n ${NAMESPACE}"
echo "   make monitor-k8s"
echo ""
echo "🗑️ Para limpar: kubectl delete namespace ${NAMESPACE}"
