#!/bin/bash

echo "🔄 REINICIANDO WHATSAPP BRIDGE CON SOPORTE MULTIMEDIA MEJORADO"
echo "=============================================================="

# Navegar al directorio del bridge
cd /home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/whatsapp_bridge

echo "📱 Verificando estado actual..."
CURRENT_STATUS=$(curl -s http://localhost:3000/status 2>/dev/null || echo "No conectado")
echo "Estado actual: $CURRENT_STATUS"

echo ""
echo "🛑 Deteniendo proceso actual..."
# Encontrar y matar el proceso de Node.js del bridge
pkill -f "node app.js" 2>/dev/null || echo "No hay proceso anterior para detener"

# Esperar un momento
sleep 2

echo "🚀 Iniciando bridge actualizado..."
echo "   - Soporte internacional ✅"
echo "   - Procesamiento multimedia mejorado ✅"
echo ""

# Iniciar el bridge
npm start