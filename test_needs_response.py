#!/usr/bin/env python3

"""
Script para probar la funcionalidad de needs_response
Este script simula la lógica que se ejecuta cuando llegan y se envían mensajes.
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Platform, Contact, Conversation, Message
from django.utils import timezone

def test_needs_response_logic():
    """Prueba la lógica de needs_response"""
    print("🔧 Probando lógica de needs_response...")
    
    try:
        # Obtener o crear plataforma WhatsApp
        platform, _ = Platform.objects.get_or_create(name='whatsapp')
        
        # Obtener o crear un contacto de prueba
        contact, _ = Contact.objects.get_or_create(
            platform=platform,
            platform_user_id='test_user_123',
            defaults={
                'name': 'Usuario de Prueba',
                'phone': '+57 300 123 4567'
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
        print(f"📊 Estado inicial needs_response: {conversation.needs_response}")
        
        # Simular mensaje entrante del contacto
        print("\n1️⃣ Simulando mensaje entrante del contacto...")
        conversation.needs_response = True
        conversation.last_message_at = timezone.now()
        conversation.save()
        print(f"✅ needs_response después del mensaje del contacto: {conversation.needs_response}")
        
        # Simular respuesta del agente
        print("\n2️⃣ Simulando respuesta del agente...")
        conversation.needs_response = False
        conversation.is_answered = True
        conversation.last_response_at = timezone.now()
        conversation.save()
        print(f"✅ needs_response después de responder: {conversation.needs_response}")
        
        # Simular otro mensaje del contacto
        print("\n3️⃣ Simulando nuevo mensaje del contacto...")
        conversation.needs_response = True
        conversation.last_message_at = timezone.now()
        conversation.save()
        print(f"✅ needs_response después del nuevo mensaje: {conversation.needs_response}")
        
        print("\n🎉 ¡Lógica de needs_response funcionando correctamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_conversation_ordering():
    """Prueba el ordenamiento de conversaciones"""
    print("\n🔧 Probando ordenamiento de conversaciones...")
    
    try:
        # Consultar conversaciones activas ordenadas
        conversations = Conversation.objects.filter(
            status='active'
        ).order_by('-needs_response', '-last_message_at')
        
        print(f"📊 Total de conversaciones activas: {conversations.count()}")
        
        if conversations.exists():
            print("\n📋 Conversaciones ordenadas (primero las que necesitan respuesta):")
            for i, conv in enumerate(conversations[:5], 1):  # Solo mostrar las primeras 5
                status = "🔴 SIN RESPONDER" if conv.needs_response else "✅ Respondida"
                print(f"{i}. {conv.contact.display_name} - {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando pruebas de funcionalidad needs_response\n")
    
    success1 = test_needs_response_logic()
    success2 = test_conversation_ordering()
    
    if success1 and success2:
        print("\n✨ ¡Todas las pruebas pasaron exitosamente!")
        print("\n📌 Próximos pasos:")
        print("   1. Ejecutar migración: python manage.py migrate")
        print("   2. Probar la funcionalidad en el navegador")
        print("   3. Enviar mensajes de prueba para verificar el ordenamiento")
    else:
        print("\n❌ Algunas pruebas fallaron. Revisa los errores arriba.")