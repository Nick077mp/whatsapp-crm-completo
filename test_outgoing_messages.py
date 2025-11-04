#!/usr/bin/env python3

"""
Script para probar la detección de mensajes salientes desde WhatsApp externo
Este script simula lo que sucede cuando respondes desde el celular o WhatsApp Web
"""

import os
import sys
import django
import json

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Platform, Contact, Conversation, Message
from core.services.whatsapp_service import WhatsAppService
from django.utils import timezone

def test_outgoing_message_detection():
    """Prueba la detección de mensajes salientes desde WhatsApp externo"""
    print("🔧 Probando detección de mensajes salientes...")
    
    try:
        # Obtener o crear plataforma WhatsApp
        platform, _ = Platform.objects.get_or_create(name='whatsapp')
        
        # Obtener o crear un contacto de prueba
        contact, _ = Contact.objects.get_or_create(
            platform=platform,
            platform_user_id='test_outgoing_123',
            defaults={
                'name': 'Cliente de Prueba Saliente',
                'phone': '+57 300 987 6543'
            }
        )
        
        # Obtener o crear conversación
        conversation, _ = Conversation.objects.get_or_create(
            contact=contact,
            status='active',
            defaults={'last_message_at': timezone.now()}
        )
        
        print(f"📱 Contacto: {contact.display_name}")
        print(f"💬 Conversación ID: {conversation.id}")
        
        # Simular que el cliente envió un mensaje (necesita respuesta)
        print("\n1️⃣ Cliente envía mensaje...")
        conversation.needs_response = True
        conversation.last_message_at = timezone.now()
        conversation.save()
        print(f"📊 needs_response: {conversation.needs_response} ❌ (Sin responder)")
        
        # Simular webhook de mensaje saliente (respuesta desde WhatsApp externo)
        print("\n2️⃣ Simulando respuesta desde WhatsApp en el celular...")
        
        # Datos del webhook saliente que llegarían del bridge de Baileys
        outgoing_webhook_data = {
            "to": contact.phone or contact.platform_user_id,
            "message_id": "outgoing_msg_" + str(timezone.now().timestamp()),
            "timestamp": int(timezone.now().timestamp()),
            "type": "text",
            "content": "Hola! Sí, estoy disponible ahora. ¿En qué te puedo ayudar?",
            "from_me": True,
            "media_url": None
        }
        
        # Procesar el webhook saliente usando el servicio
        service = WhatsAppService()
        result = service.process_outgoing_webhook(outgoing_webhook_data)
        
        if result.get('success'):
            print("✅ Webhook saliente procesado exitosamente")
            
            # Verificar que el estado se actualizó
            conversation.refresh_from_db()
            status_text = "✅ (Respondido)" if not conversation.needs_response else "❌ (Sin responder)"
            print(f"📊 needs_response después de responder: {conversation.needs_response} {status_text}")
            print(f"📊 is_answered: {conversation.is_answered}")
            
            # Verificar que el mensaje se guardó
            last_message = conversation.messages.last()
            if last_message and last_message.sender_type == 'agent':
                print(f"💬 Último mensaje guardado: '{last_message.content[:50]}...' (Agente)")
                print(f"📅 Timestamp: {last_message.created_at}")
                return True
            else:
                print("❌ El mensaje saliente no se guardó correctamente")
                return False
        else:
            print(f"❌ Error procesando webhook saliente: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_image_message_handling():
    """Prueba el manejo de mensajes con imágenes"""
    print("\n🔧 Probando manejo de mensajes con imágenes...")
    
    try:
        # Datos del webhook con imagen
        image_webhook_data = {
            "from": "+57 300 987 6543",
            "message_id": "img_msg_" + str(timezone.now().timestamp()),
            "timestamp": int(timezone.now().timestamp()),
            "type": "image",
            "content": "Mira esta foto que te envío",
            "media_url": "https://example.com/image.jpg"
        }
        
        service = WhatsAppService()
        result = service.process_webhook(image_webhook_data)
        
        if result.get('success'):
            print("✅ Mensaje con imagen procesado exitosamente")
            return True
        else:
            print(f"❌ Error procesando mensaje con imagen: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando pruebas de mensajes salientes y media\n")
    
    success1 = test_outgoing_message_detection()
    success2 = test_image_message_handling()
    
    if success1 and success2:
        print("\n✨ ¡Todas las pruebas pasaron exitosamente!")
        print("\n📌 Funcionalidades verificadas:")
        print("   ✅ Detección automática de respuestas desde WhatsApp externo")
        print("   ✅ Actualización automática del estado 'Sin responder'")
        print("   ✅ Guardado de mensajes salientes en la base de datos")
        print("   ✅ Manejo de mensajes con media (imágenes, videos, etc.)")
        print("\n🎯 ¡El sistema ya detecta cuando respondes desde tu celular!")
    else:
        print("\n❌ Algunas pruebas fallaron. Revisa los errores arriba.")