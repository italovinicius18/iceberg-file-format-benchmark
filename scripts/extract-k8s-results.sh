#!/bin/bash

NAMESPACE="iceberg-benchmark"

echo "📊 Extraindo resultados dos benchmarks Kubernetes"
echo "================================================"

# Criar diretório local para resultados
mkdir -p ./k8s-results

echo "🔍 Verificando jobs completados..."
kubectl get jobs -n ${NAMESPACE}

echo ""
echo "📋 Extraindo logs dos jobs..."

# Extrair logs de cada job
for scale in micro small medium; do
    echo "📊 Extraindo resultados: ${scale}"
    
    # Buscar pod do job
    POD=$(kubectl get pods -n ${NAMESPACE} -l scale=${scale} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ ! -z "$POD" ]; then
        # Extrair logs completos
        kubectl logs ${POD} -n ${NAMESPACE} > ./k8s-results/${scale}-benchmark-results.log
        
        # Extrair apenas os resultados finais
        kubectl logs ${POD} -n ${NAMESPACE} | grep -A 100 "ANÁLISE DOS RESULTADOS" > ./k8s-results/${scale}-analysis.txt
        
        echo "   ✅ ${scale}: ${POD}"
    else
        echo "   ❌ ${scale}: Pod não encontrado"
    fi
done

echo ""
echo "🎯 Resumo dos resultados extraídos:"
ls -la ./k8s-results/

echo ""
echo "📈 Top resultados de cada escala:"

for scale in micro small medium; do
    if [ -f "./k8s-results/${scale}-analysis.txt" ]; then
        echo ""
        echo "🔍 ${scale^^} (Top compressão):"
        grep -A 5 "Top 3 compressão" "./k8s-results/${scale}-analysis.txt" | head -8
    fi
done

echo ""
echo "🏆 Melhor combinação geral encontrada:"
grep -A 10 "MELHOR COMBINAÇÃO GERAL" ./k8s-results/*-analysis.txt | head -15

echo ""
echo "✅ Resultados extraídos com sucesso!"
echo "📁 Arquivos disponíveis em: ./k8s-results/"
