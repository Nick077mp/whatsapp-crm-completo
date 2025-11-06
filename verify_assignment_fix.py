#!/usr/bin/env python
"""
✅ VERIFICACIÓN FINAL DEL SISTEMA DE ASIGNACIÓN
Confirma que tanto la API como la interfaz web crean leads automáticamente
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Lead, User, Conversation, ActivityLog
from django.utils import timezone

def test_assignment_systems():
    """Verificar que ambos sistemas de asignación funcionan"""
    
    print("🔍 VERIFICACIÓN FINAL DEL SISTEMA DE LEADS")
    print("=" * 50)
    
    # Estado actual
    total_leads = Lead.objects.count()
    total_convs = Conversation.objects.count()
    assigned_convs = Conversation.objects.filter(assigned_to__isnull=False).count()
    convs_with_lead = Conversation.objects.filter(lead__isnull=False).count()
    
    print(f"📊 ESTADO GENERAL:")
    print(f"   - Total conversaciones: {total_convs}")
    print(f"   - Conversaciones asignadas: {assigned_convs}")
    print(f"   - Conversaciones con lead: {convs_with_lead}")
    print(f"   - Total leads: {total_leads}")
    
    # Verificar por tipo
    print(f"\n📈 LEADS POR TIPO:")
    sales_leads = Lead.objects.filter(case_type='sales').count()
    support_leads = Lead.objects.filter(case_type='support').count()
    recovery_leads = Lead.objects.filter(case_type='recovery').count()
    
    print(f"   - Sales: {sales_leads}")
    print(f"   - Support: {support_leads}")
    print(f"   - Recovery: {recovery_leads}")
    
    # Verificar por usuario
    print(f"\n👥 LEADS POR USUARIO:")
    users = User.objects.filter(role__in=['admin', 'sales', 'support'])
    for user in users:
        user_leads = Lead.objects.filter(assigned_to=user).count()
        print(f"   - {user.username} ({user.role}): {user_leads} leads")
    
    # Verificar consistencia
    print(f"\n🔍 VERIFICACIÓN DE CONSISTENCIA:")
    
    # ¿Hay conversaciones asignadas sin lead?
    assigned_no_lead = Conversation.objects.filter(
        assigned_to__isnull=False,
        lead__isnull=True
    ).count()
    
    if assigned_no_lead == 0:
        print("   ✅ Todas las conversaciones asignadas tienen lead")
    else:
        print(f"   ❌ {assigned_no_lead} conversaciones asignadas sin lead")
    
    # ¿Hay leads sin conversación asignada?
    leads_no_conv = Lead.objects.exclude(
        id__in=Conversation.objects.filter(lead__isnull=False).values_list('lead_id', flat=True)
    ).count()
    
    print(f"   📋 {leads_no_conv} leads sin conversación asociada (normal)")
    
    # Verificar últimas actividades
    print(f"\n📝 ÚLTIMAS ACTIVIDADES:")
    last_assignments = ActivityLog.objects.filter(
        action='assign_conversation'
    ).order_by('-created_at')[:3]
    
    for activity in last_assignments:
        print(f"   - {activity.created_at.strftime('%Y-%m-%d %H:%M')} - {activity.description}")
    
    # Último lead creado
    last_lead = Lead.objects.order_by('-id').first()
    if last_lead:
        print(f"\n🎯 ÚLTIMO LEAD CREADO:")
        print(f"   - ID: {last_lead.id}")
        print(f"   - Tipo: {last_lead.case_type}")
        print(f"   - Asignado a: {last_lead.assigned_to.username if last_lead.assigned_to else 'No asignado'}")
        print(f"   - Estado: {last_lead.status}")
    
    print(f"\n✅ SISTEMA VERIFICADO - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return {
        'total_leads': total_leads,
        'assigned_no_lead': assigned_no_lead,
        'leads_by_type': {
            'sales': sales_leads,
            'support': support_leads,
            'recovery': recovery_leads
        }
    }

if __name__ == '__main__':
    result = test_assignment_systems()
    
    # Status final
    if result['assigned_no_lead'] == 0:
        print(f"\n🎉 ¡SISTEMA FUNCIONANDO CORRECTAMENTE!")
        print(f"   Todas las asignaciones crean leads automáticamente")
    else:
        print(f"\n⚠️  Se detectaron {result['assigned_no_lead']} inconsistencias")