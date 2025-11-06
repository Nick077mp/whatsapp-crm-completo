#!/usr/bin/env python3
"""
Script para probar la creación automática de leads
"""
import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Lead, User, Conversation, Contact, Platform
from django.utils import timezone

def test_auto_lead_creation():
    print("🧪 PROBANDO CREACIÓN AUTOMÁTICA DE LEADS")
    print("=" * 50)
    
    # Obtener usuarios
    admin_user = User.objects.filter(role='admin').first()
    sales_user = User.objects.filter(role='sales').first()
    support_user = User.objects.filter(role='support').first()
    
    # Obtener plataforma
    platform = Platform.objects.filter(name='whatsapp').first()
    
    # Crear un contacto de prueba
    test_contact = Contact.objects.create(
        platform=platform,
        platform_user_id='+57300999888777',
        name='Test Contact Auto Lead',
        whatsapp_number='+57300999888777'
    )
    
    print(f"👤 Contacto de prueba creado: {test_contact.display_name}")
    
    # Crear conversación de prueba
    test_conversation = Conversation.objects.create(
        contact=test_contact,
        status='active',
        funnel_type='none',  # Sin clasificar inicialmente
        funnel_stage='none'
    )
    
    print(f"💬 Conversación de prueba creada: {test_conversation.id}")
    
    # Probar asignación a usuario de ventas (debería crear lead de ventas)
    print(f"\n🎯 PROBANDO ASIGNACIÓN A VENTAS:")
    test_conversation.assigned_to = sales_user
    test_conversation.funnel_type = 'sales'
    test_conversation.funnel_stage = 'sales_initial'
    test_conversation.save()
    
    # Verificar si se crea lead automáticamente
    lead = Lead.objects.filter(contact=test_contact, case_type='sales').first()
    if lead:
        print(f"   ✅ Lead creado automáticamente: {lead.id} - Tipo: {lead.case_type}")
    else:
        print(f"   ❌ No se creó lead automáticamente")
    
    # Limpiar datos de prueba
    if lead:
        lead.delete()
    test_conversation.delete()
    test_contact.delete()
    
    print(f"\n🧹 Datos de prueba limpiados")
    print(f"✅ Prueba completada!")

if __name__ == "__main__":
    test_auto_lead_creation()