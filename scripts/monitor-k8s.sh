#!/bin/bash

NAMESPACE="iceberg-benchmark"

echo "📊 Monitoramento do Iceberg Benchmark no Kubernetes"
echo "=================================================="

# Função para mostrar status
show_status() {
    echo ""
    echo "🔄 Status dos Jobs:"
    kubectl get jobs -n ${NAMESPACE} -o wide
    
    echo ""
    echo "🔄 Status dos Pods:"
    kubectl get pods -n ${NAMESPACE} -o wide
    
    echo ""
    echo "💾 Status do Storage:"
    kubectl get pvc -n ${NAMESPACE}
    
    echo ""
    echo "📈 Recursos utilizados:"
    kubectl top pods -n ${NAMESPACE} 2>/dev/null || echo "   (Metrics server não disponível)"
}

# Função para mostrar logs
show_logs() {
    local pod_name=$1
    echo ""
    echo "📋 Logs do pod: ${pod_name}"
    echo "================================"
    kubectl logs ${pod_name} -n ${NAMESPACE} --tail=50
}

# Função principal de monitoramento
monitor_continuously() {
    while true; do
        clear
        show_status
        
        echo ""
        echo "⏳ Próxima atualização em 30 segundos... (Ctrl+C para sair)"
        echo "💡 Comandos disponíveis:"
        echo "   1 - Ver logs do micro"
        echo "   2 - Ver logs do small" 
        echo "   3 - Ver logs do medium"
        echo "   4 - Ver status completo"
        echo "   q - Sair"
        
        read -t 30 -n 1 -s input 2>/dev/null || continue
        
        case $input in
            1)
                POD=$(kubectl get pods -n ${NAMESPACE} -l scale=micro -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
                if [ ! -z "$POD" ]; then
                    show_logs $POD
                    read -p "Pressione Enter para continuar..."
                fi
                ;;
            2)
                POD=$(kubectl get pods -n ${NAMESPACE} -l scale=small -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
                if [ ! -z "$POD" ]; then
                    show_logs $POD
                    read -p "Pressione Enter para continuar..."
                fi
                ;;
            3)
                POD=$(kubectl get pods -n ${NAMESPACE} -l scale=medium -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
                if [ ! -z "$POD" ]; then
                    show_logs $POD
                    read -p "Pressione Enter para continuar..."
                fi
                ;;
            4)
                show_status
                read -p "Pressione Enter para continuar..."
                ;;
            q|Q)
                echo ""
                echo "👋 Saindo do monitoramento..."
                exit 0
                ;;
        esac
    done
}

# Verificar se namespace existe
if ! kubectl get namespace ${NAMESPACE} &> /dev/null; then
    echo "❌ Namespace ${NAMESPACE} não encontrado."
    echo "Execute 'scripts/deploy-k8s.sh' primeiro."
    exit 1
fi

# Escolher modo
if [ "$1" = "--watch" ] || [ "$1" = "-w" ]; then
    monitor_continuously
else
    show_status
    echo ""
    echo "💡 Para monitoramento contínuo: $0 --watch"
    echo "💡 Para ver logs específicos:"
    echo "   kubectl logs -f <pod-name> -n ${NAMESPACE}"
fi
