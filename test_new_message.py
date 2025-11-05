#!/usr/bin/env python3
"""
Script para simular la llegada de un nuevo mensaje y probar el auto-refresh
"""

import sys
import os
import time
from datetime import datetime

# Configurar el entorno Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from core.models import Conversation, Message, Contact, Platform, User

def simulate_new_message():
    """Simular la llegada de un nuevo mensaje"""
    
    # Obtener una conversación existente
    conversations = Conversation.objects.all()[:1]
    
    if not conversations:
        print("❌ No hay conversaciones en la base de datos para probar")
        return False
        
    conversation = conversations[0]
    
    # Crear un nuevo mensaje simulado
    new_message = Message.objects.create(
        conversation=conversation,
        content=f"🧪 Mensaje de prueba auto-refresh - {datetime.now().strftime('%H:%M:%S')}",
        sender_type='contact',
        message_type='text',
        platform_message_id=f"test_{int(time.time())}"
    )
    
    print(f"✅ Mensaje de prueba creado:")
    print(f"   📱 Conversación: {conversation.contact.display_name}")
    print(f"   💬 Mensaje: {new_message.content}")
    print(f"   🕐 Hora: {new_message.created_at}")
    print(f"   🆔 ID conversación: {conversation.id}")
    
    print(f"\n📋 Para probar el auto-refresh:")
    print(f"   1. Abre la conversación ID {conversation.id} en tu navegador")
    print(f"   2. Abre las herramientas de desarrollador (F12)")
    print(f"   3. En máximo 3 segundos deberías ver el mensaje aparecer automáticamente")
    print(f"   4. En la consola deberías ver: '🔄 ¡1 nuevos mensajes detectados!'")
    
    return True

def show_recent_messages():
    """Mostrar mensajes recientes para verificación"""
    recent_messages = Message.objects.order_by('-created_at')[:5]
    
    print("\n📝 Últimos 5 mensajes en el sistema:")
    for msg in recent_messages:
        print(f"   • {msg.conversation.contact.display_name}: {msg.content[:50]}... ({msg.created_at.strftime('%H:%M:%S')})")

if __name__ == '__main__':
    print("🧪 Simulador de mensajes para probar auto-refresh\n")
    
    show_recent_messages()
    
    print(f"\n🚀 Creando nuevo mensaje de prueba...")
    if simulate_new_message():
        show_recent_messages()
        print(f"\n✅ ¡Mensaje de prueba creado exitosamente!")
        print(f"   El auto-refresh debería detectarlo automáticamente en el navegador.")
    else:
        print(f"\n❌ No se pudo crear el mensaje de prueba")