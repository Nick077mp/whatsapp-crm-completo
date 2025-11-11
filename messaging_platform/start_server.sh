#!/bin/bash

# Script para iniciar el servidor Django con variables de entorno automáticas
echo "🚀 Iniciando servidor Django con Google OAuth2..."

# Cambiar al directorio del proyecto
cd "$(dirname "$0")"

# Activar entorno virtual si existe
if [ -d "../../.venv" ]; then
    echo "📦 Activando entorno virtual..."
    source ../../.venv/bin/activate
else
    echo "⚠️ Entorno virtual no encontrado en ../../.venv"
fi

# Las variables se cargan automáticamente desde .env en settings.py
echo "🔧 Variables de entorno se cargarán desde .env"

# Aplicar migraciones si es necesario
echo "🗃️ Verificando migraciones..."
python3 manage.py migrate --check || python3 manage.py migrate

# Iniciar servidor
echo "🌐 Iniciando servidor en http://0.0.0.0:8000"
echo "📱 También accesible en http://192.168.1.176:8000"
echo ""
echo "⏹️ Presiona Ctrl+C para detener el servidor"
echo ""

python3 manage.py runserver 0.0.0.0:8000