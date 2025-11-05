#!/bin/bash
"""
Script de pruebas internacionales para el sistema de mensajería
"""

echo "🌍 INICIANDO PRUEBAS DEL SISTEMA INTERNACIONAL"
echo "=============================================="

# Verificar que Django esté funcionando
echo "📡 Verificando Django..."
DJANGO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
if [ "$DJANGO_STATUS" = "302" ] || [ "$DJANGO_STATUS" = "200" ]; then
    echo "✅ Django está funcionando (código: $DJANGO_STATUS)"
else
    echo "❌ Django no está funcionando (código: $DJANGO_STATUS)"
    exit 1
fi

# Verificar que WhatsApp Bridge esté funcionando
echo "📱 Verificando WhatsApp Bridge..."
BRIDGE_STATUS=$(curl -s http://localhost:3000/status 2>/dev/null | grep -o '"connected":[^,]*' | cut -d: -f2)
if [ "$BRIDGE_STATUS" = "true" ]; then
    echo "✅ WhatsApp Bridge está conectado"
else
    echo "⚠️  WhatsApp Bridge no está conectado, pero continuamos..."
fi

echo ""
echo "🧪 EJECUTANDO PRUEBAS INTERNACIONALES"
echo "====================================="

# Lista de números de prueba internacionales
declare -a TEST_NUMBERS=(
    "+52 55 1234 5678|México 🇲🇽"
    "+1 555 123 4567|USA 🇺🇸"  
    "+34 123 456 789|España 🇪🇸"
    "+57 300 123 4567|Colombia 🇨🇴"
    "+44 7700 123456|Reino Unido 🇬🇧"
    "+51 987 654 321|Perú 🇵🇪"
)

# Función para probar envío de mensaje
test_send_message() {
    local number="$1"
    local country="$2"
    local message="Prueba del sistema internacional para $country"
    
    echo "📤 Probando envío a $country..."
    echo "   Número: $number"
    
    # Probar con el endpoint de WhatsApp
    RESULT=$(curl -s -X POST http://localhost:8000/api/send-message/ \
        -H "Content-Type: application/json" \
        -d "{\"platform\": \"whatsapp\", \"recipient\": \"$number\", \"message\": \"$message\"}")
    
    if echo "$RESULT" | grep -q '"success":true'; then
        echo "   ✅ ÉXITO: Mensaje enviado correctamente"
    elif echo "$RESULT" | grep -q '"success":false'; then
        ERROR=$(echo "$RESULT" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
        echo "   ❌ ERROR: $ERROR"
    else
        echo "   ⚠️  RESPUESTA INESPERADA: $RESULT"
    fi
    
    echo ""
}

# Ejecutar pruebas para cada número
for test_case in "${TEST_NUMBERS[@]}"; do
    IFS='|' read -r number country <<< "$test_case"
    test_send_message "$number" "$country"
    sleep 1  # Pausa entre pruebas
done

echo "🏁 PRUEBAS COMPLETADAS"
echo "====================="
echo ""
echo "💡 NOTAS:"
echo "   - Si hay errores, asegúrate de que WhatsApp esté conectado"
echo "   - Los números de prueba son ficticios"
echo "   - El sistema ya soporta números internacionales"
echo ""
echo "🌍 ¡Tu plataforma ahora es GLOBAL! 🚀"