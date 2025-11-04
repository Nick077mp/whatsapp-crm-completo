#!/usr/bin/env python3

"""
Script simple para probar la función process_outgoing_webhook
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Platform, Contact, Conversation, Message
from core.services.whatsapp_service import WhatsAppService
from django.utils import timezone

def test_direct():
    """Prueba directa de la función"""
    print("🔧 Prueba directa de process_outgoing_webhook...")
    
    try:
        # Obtener plataforma
        platform, _ = Platform.objects.get_or_create(name='whatsapp')
        
        # Crear contacto nuevo para prueba limpia
        contact = Contact.objects.create(
            platform=platform,
            platform_user_id='test_clean_' + str(int(timezone.now().timestamp())),
            name='Test Limpio',
            phone='+57 300 111 2222'
        )
        
        # Crear conversación nueva
        conversation = Conversation.objects.create(
            contact=contact,
            status='active',
            last_message_at=timezone.now(),
            needs_response=True  # Inicialmente necesita respuesta
        )
        
        print(f"📱 Contacto nuevo: {contact.display_name}")
        print(f"💬 Conversación ID: {conversation.id}")
        print(f"📊 Estado inicial needs_response: {conversation.needs_response}")
        
        # Datos del webhook saliente
        webhook_data = {
            "to": contact.platform_user_id,
            "message_id": "test_msg_123",
            "timestamp": int(timezone.now().timestamp()),
            "type": "text",
            "content": "Respuesta de prueba desde WhatsApp externo",
            "from_me": True,
            "media_url": None
        }
        
        # Procesar webhook
        service = WhatsAppService()
        result = service.process_outgoing_webhook(webhook_data)
        
        print(f"\n🔄 Resultado del webhook: {result}")
        
        # Verificar estado actualizado
        conversation.refresh_from_db()
        print(f"📊 needs_response después del webhook: {conversation.needs_response}")
        print(f"📊 is_answered después del webhook: {conversation.is_answered}")
        
        # Verificar mensaje creado
        messages = conversation.messages.filter(sender_type='agent')
        if messages.exists():
            last_msg = messages.last()
            print(f"💬 Mensaje creado: '{last_msg.content}' (Tipo: {last_msg.sender_type})")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct()
    if success:
        print("\n✅ ¡Prueba exitosa!")
    else:
        print("\n❌ Prueba falló")