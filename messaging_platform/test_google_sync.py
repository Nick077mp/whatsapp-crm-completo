#!/usr/bin/env python
"""
Script para probar la sincronización automática con Google Contacts
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Contact, GoogleContactsAuth, Platform
from core.services.google_contacts_service import GoogleContactsService

def test_google_sync():
    print("=== PRUEBA DE SINCRONIZACIÓN CON GOOGLE CONTACTS ===")
    
    # Verificar autorización
    auths = GoogleContactsAuth.objects.all()
    if not auths:
        print("❌ No hay autorización OAuth. Completa primero el OAuth en el navegador.")
        return
    
    auth = auths.first()
    print(f"✅ Autorización encontrada para usuario: {auth.user.username}")
    
    # Crear un contacto de prueba
    platform = Platform.objects.get_or_create(name='whatsapp')[0]
    
    # Usa un número que tengas en Google Contacts para probar
    test_numbers = [
        "+573001234567",  # Reemplaza con tu número real
        "+57300",  # Prefijo para probar búsqueda parcial
        "3001234567"  # Formato local
    ]
    
    print("\n=== PROBANDO NÚMEROS DE PRUEBA ===")
    for number in test_numbers:
        print(f"\n🔍 Probando número: {number}")
        
        # Crear o buscar contacto
        contact, created = Contact.objects.get_or_create(
            platform=platform,
            platform_user_id=number.replace('+', ''),
            defaults={
                'name': number,
                'phone': number
            }
        )
        
        if created:
            print(f"   📱 Contacto creado: ID {contact.id}")
        else:
            print(f"   📱 Contacto existente: ID {contact.id}")
        
        # Intentar sincronización
        print("   🔄 Intentando sincronización con Google...")
        success = contact.sync_with_google_contacts(auth.user)
        
        if success:
            contact.refresh_from_db()
            print(f"   ✅ Sincronizado! Nombre Google: {contact.google_contact_name}")
        else:
            print("   ❌ No encontrado en Google Contacts")
    
    print("\n=== CONTACTOS CON NOMBRES DE GOOGLE ===")
    google_contacts = Contact.objects.filter(google_contact_name__isnull=False)
    
    if google_contacts:
        for contact in google_contacts:
            print(f"📞 {contact.phone} -> {contact.google_contact_name}")
    else:
        print("❌ Ningún contacto sincronizado con Google")
    
    print("\n=== PROBANDO SERVICIO DIRECTO ===")
    try:
        service = GoogleContactsService(auth.user)
        # Prueba con tu número real
        test_phone = "+573001234567"  # Cambia por tu número
        result = service.search_contact_by_phone(test_phone)
        
        if result:
            print(f"✅ Encontrado en Google: {result['name']} ({result['phone']})")
        else:
            print(f"❌ No encontrado en Google: {test_phone}")
            
    except Exception as e:
        print(f"❌ Error en servicio: {e}")

if __name__ == "__main__":
    test_google_sync()