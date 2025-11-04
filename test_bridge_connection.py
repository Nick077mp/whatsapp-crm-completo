#!/usr/bin/env python3
"""
Script de prueba para verificar la conectividad del bridge de WhatsApp
"""
import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.services.whatsapp_service import WhatsAppService

def test_whatsapp_bridge():
    print("🔍 Probando conexión con el bridge de WhatsApp...")
    
    # Crear instancia del servicio
    wa_service = WhatsAppService()
    
    # Verificar configuración
    print(f"📡 URL del bridge: {wa_service.bridge_url}")
    
    # Verificar si está configurado
    is_configured = wa_service.is_configured()
    print(f"⚙️  ¿Está configurado? {is_configured}")
    
    # Verificar si está conectado
    is_connected = wa_service.is_connected()
    print(f"📱 ¿Está conectado? {is_connected}")
    
    if is_configured and is_connected:
        print("✅ ¡El bridge de WhatsApp está funcionando correctamente!")
        return True
    else:
        print("❌ Hay problemas con el bridge de WhatsApp")
        return False

if __name__ == "__main__":
    test_whatsapp_bridge()