#!/usr/bin/env python3
"""
Script para explorar contactos y encontrar el patrón de almacenamiento
"""
import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Contact, Conversation, Message
from django.db import models

def explore_contacts():
    print("🔍 EXPLORANDO TODOS LOS CONTACTOS")
    print("=" * 50)
    
    # Mostrar todos los contactos recientes
    recent_contacts = Contact.objects.all().order_by('-updated_at')[:20]
    
    print(f"📊 Total contactos: {Contact.objects.count()}")
    print(f"📋 Últimos 20 contactos:")
    
    for contact in recent_contacts:
        print(f"   ID: {contact.id:3d} | Phone: {contact.phone:15s} | Platform ID: {contact.platform_user_id:20s} | Name: {contact.display_name}")
    
    # Buscar específicamente números que contengan 5762295
    print(f"\n🔍 BUSCANDO NÚMEROS QUE CONTENGAN '5762295':")
    matching_contacts = Contact.objects.filter(
        models.Q(phone__icontains="5762295") |
        models.Q(platform_user_id__icontains="5762295") |
        models.Q(name__icontains="5762295")
    )
    
    for contact in matching_contacts:
        print(f"   ✅ ENCONTRADO: ID={contact.id}, Phone={contact.phone}, Platform_ID={contact.platform_user_id}, Name={contact.display_name}")
        
        # Mostrar conversaciones de este contacto
        convs = Conversation.objects.filter(contact=contact)
        print(f"      💬 Conversaciones: {convs.count()}")
        for conv in convs:
            print(f"         - Conv {conv.id}: {conv.status}")
    
    # Buscar patrones comunes en números
    print(f"\n📱 PATRONES DE NÚMEROS ENCONTRADOS:")
    all_contacts = Contact.objects.all()
    phone_patterns = {}
    
    for contact in all_contacts:
        if contact.phone:
            if contact.phone.startswith('+57'):
                phone_patterns['+57'] = phone_patterns.get('+57', 0) + 1
            elif contact.phone.startswith('57'):
                phone_patterns['57'] = phone_patterns.get('57', 0) + 1
            elif contact.phone.startswith('3'):
                phone_patterns['3xx'] = phone_patterns.get('3xx', 0) + 1
    
    for pattern, count in phone_patterns.items():
        print(f"   - {pattern}: {count} contactos")

if __name__ == "__main__":
    explore_contacts()