#!/usr/bin/env python3
"""
Script para verificar contactos y conversaciones en la base de datos
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Contact, Conversation, Platform

def check_database():
    """Verificar el estado actual de la base de datos"""
    print("🔍 Verificando estado de la base de datos...")
    
    # Verificar plataformas
    platforms = Platform.objects.all()
    print(f"📱 Plataformas disponibles: {[p.name for p in platforms]}")
    
    # Verificar contactos
    contacts = Contact.objects.all()
    print(f"👥 Total de contactos: {contacts.count()}")
    
    for contact in contacts[:5]:  # Mostrar solo los primeros 5
        print(f"  - {contact.name} ({contact.platform.name}): {contact.phone} | ID: {contact.platform_user_id}")
    
    # Verificar conversaciones activas
    active_conversations = Conversation.objects.filter(status='active')
    print(f"💬 Conversaciones activas: {active_conversations.count()}")
    
    for conv in active_conversations[:5]:  # Mostrar solo las primeras 5
        print(f"  - Conversación {conv.id}: {conv.contact.name} | Respondida: {conv.is_answered}")
    
    # Crear un contacto y conversación de prueba si no existe
    whatsapp_platform = Platform.objects.filter(name='whatsapp').first()
    if whatsapp_platform:
        test_contact, created = Contact.objects.get_or_create(
            platform=whatsapp_platform,
            platform_user_id="573007341192",  # Número de prueba sin formato
            defaults={
                'name': '+57 300 734 1192',
                'phone': '+57 300 734 1192'
            }
        )
        
        if created:
            print(f"✅ Contacto de prueba creado: {test_contact.name}")
        else:
            print(f"📋 Contacto de prueba ya existe: {test_contact.name}")
        
        # Crear conversación activa si no existe
        test_conversation, created = Conversation.objects.get_or_create(
            contact=test_contact,
            status='active',
            defaults={
                'is_answered': False  # Sin responder inicialmente
            }
        )
        
        if created:
            print(f"✅ Conversación de prueba creada: ID {test_conversation.id}")
        else:
            print(f"📋 Conversación de prueba ya existe: ID {test_conversation.id} | Respondida: {test_conversation.is_answered}")

if __name__ == "__main__":
    check_database()