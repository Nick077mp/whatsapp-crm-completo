#!/usr/bin/env python3
"""
Script para probar el envío de mensajes desde Django sin depender del bridge
"""
import os
import sys
import django
import json

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Contact, Platform, Conversation
from core.services.whatsapp_service import WhatsAppService

User = get_user_model()

def test_django_message_sending():
    """Prueba el envío de mensajes a través del servicio de Django"""
    print("🔍 Probando envío de mensaje desde Django...")
    
    # Crear o obtener plataforma
    platform, _ = Platform.objects.get_or_create(
        name='whatsapp',
        defaults={'display_name': 'WhatsApp', 'is_active': True}
    )
    
    # Crear contacto de prueba
    contact, _ = Contact.objects.get_or_create(
        platform=platform,
        platform_user_id='WA-test-user',
        defaults={
            'name': 'Usuario de Prueba',
            'phone': '+573000000000'
        }
    )
    
    # Crear conversación de prueba
    conversation, _ = Conversation.objects.get_or_create(
        contact=contact,
        platform=platform,
        defaults={'status': 'active'}
    )
    
    # Probar servicio de WhatsApp
    wa_service = WhatsAppService()
    
    print(f"📡 Bridge URL: {wa_service.bridge_url}")
    print(f"⚙️ ¿Configurado?: {wa_service.is_configured()}")
    print(f"📱 ¿Conectado?: {wa_service.is_connected()}")
    
    # Intentar enviar mensaje
    result = wa_service.send_message(
        to_number='+573000000000',
        message_text='Mensaje de prueba desde Django',
        conversation=conversation
    )
    
    print(f"📋 Resultado del envío:")
    print(json.dumps(result, indent=2))
    
    return result.get('success', False)

if __name__ == "__main__":
    test_django_message_sending()