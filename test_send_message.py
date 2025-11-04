#!/usr/bin/env python3
"""
Script de prueba para enviar un mensaje de WhatsApp
"""
import os
import sys
import django
import json

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.services.whatsapp_service import WhatsAppService

def test_send_message():
    print("🔍 Probando envío de mensaje...")
    
    wa_service = WhatsAppService()
    
    # Número de prueba (reemplaza con un número válido)
    test_number = "573123456789"  # Formato internacional
    test_message = "Mensaje de prueba desde la consola"
    
    print(f"📱 Enviando a: {test_number}")
    print(f"💬 Mensaje: {test_message}")
    
    result = wa_service.send_message(test_number, test_message)
    
    print(f"📋 Resultado: {json.dumps(result, indent=2)}")
    
    return result

if __name__ == "__main__":
    test_send_message()