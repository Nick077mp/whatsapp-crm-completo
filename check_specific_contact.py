#!/usr/bin/env python3
"""
Script para verificar conversaciones específicas del contacto
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Contact, Conversation, Platform

def check_specific_contact():
    """Verificar conversaciones del contacto específico"""
    print("🔍 Verificando contacto específico...")
    
    to_number = "+57 300 734 1192"
    whatsapp_platform = Platform.objects.get(name='whatsapp')
    
    # Buscar contacto
    contacts = Contact.objects.filter(platform=whatsapp_platform, platform_user_id=to_number)
    print(f"📞 Contactos encontrados con ID '{to_number}': {contacts.count()}")
    
    for contact in contacts:
        print(f"  - Contacto ID: {contact.id}, Name: {contact.name}, Phone: {contact.phone}")
        
        # Buscar conversaciones para este contacto
        conversations = Conversation.objects.filter(contact=contact)
        print(f"    💬 Total conversaciones: {conversations.count()}")
        
        active_conversations = conversations.filter(status='active')
        print(f"    ✅ Conversaciones activas: {active_conversations.count()}")
        
        for conv in active_conversations:
            print(f"      - Conv ID: {conv.id}, Status: {conv.status}, Answered: {conv.is_answered}")

if __name__ == "__main__":
    check_specific_contact()