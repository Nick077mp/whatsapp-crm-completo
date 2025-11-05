#!/usr/bin/env python3
"""
Script para probar la API de auto-refresh de mensajes
"""

import requests
import json
import sys
import os

# Configurar el entorno Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from core.models import Conversation, Message, Contact, Platform, User

def test_api_endpoint():
    """Probar el endpoint de la API para obtener mensajes"""
    
    # Obtener una conversación existente
    conversations = Conversation.objects.all()[:1]
    
    if not conversations:
        print("❌ No hay conversaciones en la base de datos para probar")
        return False
        
    conversation = conversations[0]
    print(f"✅ Probando con conversación ID: {conversation.id}")
    print(f"📱 Contacto: {conversation.contact.display_name}")
    print(f"💬 Mensajes actuales: {conversation.messages.count()}")
    
    # Simular petición a la API (sin hacer request HTTP real)
    # En su lugar, llamar directamente a la vista
    from core.views import api_conversation_messages
    from django.http import HttpRequest
    from django.contrib.auth.models import AnonymousUser
    
    # Crear un request simulado
    request = HttpRequest()
    request.method = 'GET'
    request.user = User.objects.first()
    
    if not request.user:
        print("❌ No hay usuarios activos para probar")
        return False
    
    try:
        response = api_conversation_messages(request, conversation.id)
        
        if hasattr(response, 'content'):
            data = json.loads(response.content.decode())
            
            if data.get('success'):
                messages = data.get('messages', [])
                print(f"✅ API respondió correctamente")
                print(f"📊 Mensajes devueltos: {len(messages)}")
                
                if messages:
                    last_message = messages[-1]
                    print(f"🔤 Último mensaje: {last_message['content'][:50]}...")
                    print(f"👤 Remitente: {last_message['sender_name']}")
                    print(f"📅 Fecha: {last_message['created_at']}")
                
                return True
            else:
                print(f"❌ API devolvió error: {data.get('error', 'Error desconocido')}")
                return False
        else:
            print("❌ La respuesta no tiene contenido")
            return False
            
    except Exception as e:
        print(f"❌ Error al llamar a la API: {str(e)}")
        return False

def show_conversation_stats():
    """Mostrar estadísticas de conversaciones"""
    total_conversations = Conversation.objects.count()
    total_messages = Message.objects.count()
    total_contacts = Contact.objects.count()
    
    print(f"\n📊 Estadísticas del sistema:")
    print(f"   💬 Conversaciones totales: {total_conversations}")
    print(f"   📝 Mensajes totales: {total_messages}")
    print(f"   👥 Contactos totales: {total_contacts}")
    
    if total_conversations > 0:
        # Mostrar algunas conversaciones recientes
        recent_conversations = Conversation.objects.order_by('-updated_at')[:3]
        print(f"\n🕐 Conversaciones recientes:")
        for conv in recent_conversations:
            print(f"   • ID {conv.id}: {conv.contact.display_name} ({conv.messages.count()} mensajes)")

if __name__ == '__main__':
    print("🚀 Iniciando pruebas del sistema de auto-refresh\n")
    
    show_conversation_stats()
    
    print(f"\n🔧 Probando API de mensajes...")
    if test_api_endpoint():
        print(f"\n✅ ¡Todas las pruebas pasaron correctamente!")
        print(f"   El auto-refresh debería funcionar sin problemas.")
        print(f"\n📋 Para probar en el navegador:")
        print(f"   1. Abre una conversación en la web")
        print(f"   2. Abre las herramientas de desarrollador (F12)")
        print(f"   3. Ve a la consola y busca los logs: '✅ Auto-refresh activado'")
        print(f"   4. Los mensajes nuevos aparecerán automáticamente cada 3 segundos")
    else:
        print(f"\n❌ Hay problemas con la configuración")
        print(f"   Revisa la configuración de la base de datos y los modelos")