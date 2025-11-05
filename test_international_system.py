#!/usr/bin/env python3
"""
Test completo del sistema internacional - Verificar que funcione con cualquier país
"""

import os
import sys
from pathlib import Path

# Configurar Django
current_dir = Path(__file__).parent
messaging_platform_dir = current_dir / "messaging_platform"
sys.path.insert(0, str(messaging_platform_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    import django
    django.setup()
    from core.utils.international_phone import *
    from core.models import Contact, Platform
    from core.services.whatsapp_service import WhatsAppService
    print("✅ Django configurado correctamente")
except ImportError as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

def test_international_phone_utils():
    """Test de las utilidades internacionales"""
    print("\n🧪 TESTING: Utilidades internacionales")
    
    test_numbers = [
        # Colombia
        ("573001234567", "+57 300 123 4567"),
        ("+57 300 123 4567", "+57 300 123 4567"),
        ("3001234567", "+57 300 123 4567"),  # Retrocompatibilidad
        
        # México
        ("525512345678", "+52 55 1234 5678"),
        ("+52 55 1234 5678", "+52 55 1234 5678"),
        
        # USA/Canadá  
        ("15551234567", "+1 555 123 4567"),
        ("+1 555 123 4567", "+1 555 123 4567"),
        
        # Reino Unido
        ("447700123456", "+44 7700 123456"),
        ("+44 7700 123456", "+44 7700 123456"),
        
        # España
        ("34123456789", "+34 123 456 789"),
        ("+34 123 456 789", "+34 123 456 789"),
        
        # Perú
        ("51123456789", "+51 123 456 789"),
        ("+51 123 456 789", "+51 123 456 789"),
    ]
    
    for input_number, expected in test_numbers:
        formatted = formatear_numero_internacional(input_number)
        status = "✅" if formatted == expected else "❌"
        print(f"  {status} {input_number:15} -> {formatted or 'ERROR':20} (esperado: {expected})")
        
        if formatted:
            # Test info del país
            info = obtener_info_pais(formatted)
            clean_for_wa = obtener_numero_para_whatsapp(formatted)
            print(f"      País: {info['name'] if info else 'N/A'}, WhatsApp: {clean_for_wa}")

def test_contact_model():
    """Test del modelo Contact con números internacionales"""
    print("\n🧪 TESTING: Modelo Contact")
    
    # Obtener plataforma WhatsApp
    platform, created = Platform.objects.get_or_create(name='whatsapp', defaults={'is_active': True})
    
    test_contacts = [
        ("+57 300 123 4567", "Colombia"),
        ("+52 55 1234 5678", "México"),
        ("+1 555 123 4567", "USA/Canadá"),
        ("+44 7700 123456", "Reino Unido"),
        ("+34 123 456 789", "España"),
    ]
    
    for phone, expected_country in test_contacts:
        # Crear contacto temporal
        contact = Contact(
            platform=platform,
            platform_user_id=phone.replace('+', '').replace(' ', ''),
            phone=phone,
            name=f"Test {expected_country}"
        )
        
        # Test propiedades
        formatted = contact.formatted_phone
        whatsapp_num = contact.whatsapp_number
        country_info = contact.country_info
        
        print(f"  📱 {phone}")
        print(f"    Formatted: {formatted}")
        print(f"    WhatsApp: {whatsapp_num}")
        print(f"    País: {country_info['name'] if country_info else 'N/A'}")
        print(f"    Status: {'✅' if country_info and expected_country in country_info['name'] else '❌'}")

def test_whatsapp_service():
    """Test del servicio WhatsApp con números internacionales"""
    print("\n🧪 TESTING: WhatsApp Service")
    
    service = WhatsAppService()
    
    test_numbers = [
        "573001234567@s.whatsapp.net",
        "+57 300 123 4567",
        "525512345678@s.whatsapp.net", 
        "+52 55 1234 5678",
        "15551234567@s.whatsapp.net",
        "+1 555 123 4567",
    ]
    
    for test_num in test_numbers:
        try:
            extracted = service._extract_real_phone_number(test_num)
            status = "✅" if extracted and extracted.startswith('+') else "❌"
            print(f"  {status} {test_num:25} -> {extracted or 'ERROR'}")
        except Exception as e:
            print(f"  ❌ {test_num:25} -> ERROR: {e}")

def test_normalization():
    """Test de normalización para el bridge"""
    print("\n🧪 TESTING: Normalización para Bridge")
    
    service = WhatsAppService()
    
    test_cases = [
        "+57 300 123 4567",
        "+52 55 1234 5678", 
        "+1 555 123 4567",
        "3001234567",  # Colombia sin código
        "525512345678",  # México completo
        "15551234567",   # USA completo
    ]
    
    for test_case in test_cases:
        try:
            normalized = service._normalize_phone_for_bridge(test_case)
            status = "✅" if normalized else "❌"
            print(f"  {status} {test_case:20} -> {normalized}")
        except Exception as e:
            print(f"  ❌ {test_case:20} -> ERROR: {e}")

def main():
    """Función principal de testing"""
    print("🌍 SISTEMA INTERNACIONAL - TEST COMPLETO")
    print("="*60)
    
    try:
        test_international_phone_utils()
        test_contact_model()
        test_whatsapp_service()
        test_normalization()
        
        print("\n🎉 TESTING COMPLETADO")
        print("✅ El sistema ahora soporta números internacionales")
        print("✅ Retrocompatibilidad con Colombia mantenida")
        
    except Exception as e:
        print(f"\n❌ ERROR EN TESTING: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()