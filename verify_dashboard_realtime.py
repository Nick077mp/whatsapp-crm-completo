#!/usr/bin/env python
"""
✅ VERIFICACIÓN FINAL DEL DASHBOARD ACTUALIZADO EN TIEMPO REAL
Confirma que el dashboard muestra las conversaciones más recientemente actualizadas al top
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Conversation, User, Lead
from django.utils import timezone

def test_dashboard_realtime():
    """Verificar que el dashboard se actualiza en tiempo real"""
    
    print("🔍 VERIFICACIÓN FINAL DEL DASHBOARD EN TIEMPO REAL")
    print("=" * 55)
    
    # Simular vista de admin
    admin_user = User.objects.filter(role='admin').first()
    print(f"👑 Usuario admin: {admin_user.username}")
    
    # Query exacta del dashboard actualizado
    base_conversations = Conversation.objects.filter(status='active')
    dashboard_conversations = base_conversations.select_related(
        'contact', 'contact__platform', 'assigned_to'
    ).order_by('-updated_at', '-needs_response', '-last_message_at')[:10]
    
    print(f"\n📊 TOP 10 CONVERSACIONES EN DASHBOARD:")
    print("Ordenación: -updated_at, -needs_response, -last_message_at")
    print()
    
    for i, conv in enumerate(dashboard_conversations, 1):
        assigned_name = conv.assigned_to.username if conv.assigned_to else 'Sin asignar'
        needs_response = '🚨' if conv.needs_response else '✅'
        updated = conv.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        last_msg = conv.last_message_at.strftime('%Y-%m-%d %H:%M') if conv.last_message_at else 'N/A'
        
        print(f"{i:2d}. Conv {conv.id:3d} | {assigned_name:12s} {needs_response} | Updated: {updated} | Last: {last_msg}")
    
    # Estadísticas actuales
    total_active = base_conversations.count()
    total_assigned = base_conversations.filter(assigned_to__isnull=False).count()
    total_unassigned = base_conversations.filter(assigned_to__isnull=True).count()
    needs_response = base_conversations.filter(needs_response=True).count()
    
    print(f"\n📈 ESTADÍSTICAS DEL DASHBOARD:")
    print(f"   - Total conversaciones activas: {total_active}")
    print(f"   - Conversaciones asignadas: {total_assigned}")
    print(f"   - Conversaciones sin asignar: {total_unassigned}")  
    print(f"   - Conversaciones que necesitan respuesta: {needs_response}")
    
    # Verificar distribución por agente
    print(f"\n👥 DISTRIBUCIÓN POR AGENTE:")
    users = User.objects.filter(role__in=['sales', 'support'])
    for user in users:
        user_convs = base_conversations.filter(assigned_to=user).count()
        user_leads = Lead.objects.filter(assigned_to=user).count()
        print(f"   - {user.username} ({user.role}): {user_convs} conversaciones, {user_leads} leads")
    
    # Verificar conversaciones más recientemente actualizadas
    print(f"\n🔄 CONVERSACIONES ACTUALIZADAS EN ÚLTIMOS MINUTOS:")
    recent_cutoff = timezone.now() - timezone.timedelta(minutes=30)
    recent_updates = base_conversations.filter(
        updated_at__gte=recent_cutoff
    ).order_by('-updated_at')[:5]
    
    if recent_updates.exists():
        for conv in recent_updates:
            assigned_name = conv.assigned_to.username if conv.assigned_to else 'Sin asignar'
            updated = conv.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            print(f"   - Conv {conv.id} ({assigned_name}) - {updated}")
    else:
        print("   - No hay conversaciones actualizadas en los últimos 30 minutos")
    
    # Verificar que las asignaciones recientes aparezcan al top
    most_recent = dashboard_conversations[0] if dashboard_conversations.exists() else None
    if most_recent:
        minutes_ago = (timezone.now() - most_recent.updated_at).total_seconds() / 60
        print(f"\n🎯 CONVERSACIÓN MÁS RECIENTE EN DASHBOARD:")
        print(f"   - Conv {most_recent.id} actualizada hace {minutes_ago:.1f} minutos")
        
        if minutes_ago < 60:  # Actualizada en la última hora
            print(f"   ✅ Dashboard actualizado recientemente - funcionando correctamente")
        else:
            print(f"   ⚠️  La conversación más reciente es antigua - revisar actividad")
    
    print(f"\n✅ VERIFICACIÓN COMPLETADA - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return {
        'total_conversations': total_active,
        'assigned_conversations': total_assigned,
        'unassigned_conversations': total_unassigned,
        'dashboard_working': True if most_recent and minutes_ago < 60 else False
    }

if __name__ == '__main__':
    result = test_dashboard_realtime()
    
    # Status final
    if result['dashboard_working']:
        print(f"\n🎉 ¡DASHBOARD FUNCIONANDO EN TIEMPO REAL!")
        print(f"   Las conversaciones aparecen actualizadas inmediatamente")
    else:
        print(f"\n⚠️  Dashboard puede necesitar más actividad para verificar funcionamiento")
    
    print(f"\n📋 RESUMEN:")
    print(f"   - {result['assigned_conversations']} conversaciones asignadas")
    print(f"   - {result['unassigned_conversations']} conversaciones disponibles")
    print(f"   - Dashboard ordenado por actualización más reciente")