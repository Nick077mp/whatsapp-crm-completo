#!/usr/bin/env python3
"""
Script para probar el sistema de leads después de las mejoras
"""
import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Lead, User, Conversation, Contact

def test_leads_system():
    print("🧪 PROBANDO SISTEMA DE LEADS")
    print("=" * 50)
    
    # 1. Verificar usuarios
    print("\n👥 USUARIOS DISPONIBLES:")
    users = User.objects.all()
    for user in users:
        print(f"   - {user.username} ({user.role})")
    
    # 2. Verificar leads totales
    print(f"\n📊 LEADS TOTALES EN SISTEMA:")
    all_leads = Lead.objects.all()
    print(f"   Total: {all_leads.count()}")
    
    for case_type in ['sales', 'support', 'recovery']:
        count = all_leads.filter(case_type=case_type).count()
        print(f"   - {case_type.capitalize()}: {count}")
    
    # 3. Verificar leads por usuario
    print(f"\n👤 LEADS POR USUARIO:")
    for user in users:
        user_leads = all_leads.filter(assigned_to=user)
        if user_leads.exists():
            print(f"   - {user.username} ({user.role}): {user_leads.count()} leads")
            for lead in user_leads:
                print(f"      * {lead.contact.display_name} - {lead.case_type}")
    
    # 4. Verificar conversaciones asignadas
    print(f"\n💬 CONVERSACIONES ASIGNADAS:")
    assigned_conversations = Conversation.objects.filter(
        assigned_to__isnull=False,
        status='active'
    ).select_related('contact', 'assigned_to')
    
    print(f"   Total conversaciones asignadas: {assigned_conversations.count()}")
    
    for conv in assigned_conversations:
        lead_info = f" (Lead: {conv.lead.id})" if conv.lead else " (SIN LEAD!)"
        print(f"   - {conv.contact.display_name} → {conv.assigned_to.username} - {conv.funnel_type}{lead_info}")
    
    # 5. Verificar filtros por rol
    print(f"\n🎯 SIMULACIÓN DE FILTROS POR ROL:")
    
    # Admin - debe ver todos
    admin_leads = all_leads  # Sin filtro
    print(f"   Admin ve: {admin_leads.count()} leads (todos)")
    
    # Ventas - solo sales y recovery
    sales_leads = all_leads.filter(case_type__in=['sales', 'recovery'])
    print(f"   Ventas ve: {sales_leads.count()} leads (sales + recovery)")
    
    # Support - no debería tener acceso a leads
    support_leads = all_leads.filter(case_type='support')
    print(f"   Support vería: {support_leads.count()} leads (pero no tiene acceso)")
    
    print("\n✅ Prueba completada!")

if __name__ == "__main__":
    test_leads_system()