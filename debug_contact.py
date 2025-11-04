#!/usr/bin/env python3
"""
Script para debugear el proceso de búsqueda del contacto
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Contact, Conversation, Platform

def debug_contact_search():
    """Debugear la búsqueda de contactos"""
    print("🔍 Debugeando búsqueda de contactos...")
    
    to_number = "+57 300 734 1192"
    clean_to_number = to_number.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '').replace('@g.us', '')
    
    print(f"📞 Número original: {to_number}")
    print(f"🧹 Número limpio: {clean_to_number}")
    
    # Buscar por platform_user_id
    whatsapp_platform = Platform.objects.get(name='whatsapp')
    
    print(f"\n🔍 Buscando por platform_user_id = '{clean_to_number}'...")
    contacts_by_id = Contact.objects.filter(platform=whatsapp_platform, platform_user_id=clean_to_number)
    print(f"📋 Encontrados por ID: {contacts_by_id.count()}")
    
    print(f"\n🔍 Buscando por phone = '{clean_to_number}'...")
    contacts_by_phone = Contact.objects.filter(platform=whatsapp_platform, phone=clean_to_number)
    print(f"📋 Encontrados por teléfono: {contacts_by_phone.count()}")
    
    # Mostrar todos los contactos para ver qué formatos existen
    print(f"\n📋 Todos los contactos de WhatsApp:")
    all_contacts = Contact.objects.filter(platform=whatsapp_platform)
    for contact in all_contacts:
        print(f"  - ID: '{contact.platform_user_id}' | Phone: '{contact.phone}' | Name: '{contact.name}'")
    
    # Intentar con diferentes formatos
    formats_to_try = [
        clean_to_number,
        to_number,
        "573007341192",  # Sin espacios ni símbolos
        "57 300 734 1192",  # Con espacios pero sin +
        "+573007341192",  # Sin espacios
    ]
    
    print(f"\n🧪 Probando diferentes formatos de búsqueda:")
    for format_attempt in formats_to_try:
        # Por platform_user_id
        found_by_id = Contact.objects.filter(platform=whatsapp_platform, platform_user_id=format_attempt).exists()
        found_by_phone = Contact.objects.filter(platform=whatsapp_platform, phone=format_attempt).exists()
        print(f"  - '{format_attempt}': ID={found_by_id}, Phone={found_by_phone}")

if __name__ == "__main__":
    debug_contact_search()