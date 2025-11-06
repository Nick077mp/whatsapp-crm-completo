#!/usr/bin/env python3
"""
Script para arreglar y sincronizar leads con conversaciones asignadas
"""
import os
import sys
import django
from datetime import datetime

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Lead, User, Conversation, Contact
from django.utils import timezone

def fix_leads_system():
    print("🔧 ARREGLANDO SISTEMA DE LEADS")
    print("=" * 50)
    
    # 1. Encontrar conversaciones asignadas sin lead
    conversations_without_leads = Conversation.objects.filter(
        status='active',
        assigned_to__isnull=False,
        lead__isnull=True
    ).select_related('contact', 'assigned_to')
    
    print(f"\n🔍 Encontradas {conversations_without_leads.count()} conversaciones sin lead")
    
    created_count = 0
    updated_count = 0
    
    # 2. Crear leads para conversaciones que no tienen
    for conv in conversations_without_leads:
        # Mapear funnel_type a case_type correctamente
        case_type_mapping = {
            'sales': 'sales',
            'support': 'support', 
            'recovery': 'recovery',
            'none': 'support'  # Default para conversaciones sin clasificar
        }
        
        funnel_type = conv.funnel_type or 'none'
        case_type = case_type_mapping.get(funnel_type, 'support')
        
        print(f"   📋 Procesando: {conv.contact.display_name} - {conv.assigned_to.username} - Funnel: {funnel_type} → Case: {case_type}")
        
        # Verificar si ya existe un lead para este contacto y case_type
        existing_lead = Lead.objects.filter(
            contact=conv.contact,
            case_type=case_type
        ).first()
        
        if existing_lead:
            # Asociar conversación al lead existente
            conv.lead = existing_lead
            conv.save()
            print(f"      ✅ Asociado al lead existente {existing_lead.id}")
            updated_count += 1
        else:
            # Crear nuevo lead
            lead = Lead.objects.create(
                contact=conv.contact,
                assigned_to=conv.assigned_to,
                case_type=case_type,
                status='active',
                notes=f'Lead creado automáticamente el {timezone.now().strftime("%Y-%m-%d %H:%M")} para conversación {conv.id}'
            )
            
            # Asociar conversación al lead
            conv.lead = lead
            conv.save()
            
            print(f"      ✅ Creado nuevo lead {lead.id}")
            created_count += 1
    
    # 3. Corregir leads con case_type incorrecto
    print(f"\n🔄 CORRIGIENDO CASE_TYPES INCORRECTOS")
    
    # Encontrar leads asignados a usuarios de ventas pero con case_type='support'
    incorrect_leads = Lead.objects.filter(
        assigned_to__role='sales',
        case_type='support'
    )
    
    print(f"   Encontrados {incorrect_leads.count()} leads de sales con case_type incorrecto")
    
    for lead in incorrect_leads:
        print(f"   📝 Corrigiendo lead {lead.id} - {lead.contact.display_name}: support → sales")
        lead.case_type = 'sales'
        lead.save()
    
    # 4. Mostrar resumen final
    print(f"\n📊 RESUMEN DE CAMBIOS:")
    print(f"   ✅ Leads creados: {created_count}")
    print(f"   🔗 Conversaciones asociadas: {updated_count}")
    print(f"   🔄 Case types corregidos: {incorrect_leads.count()}")
    
    # 5. Mostrar estadísticas finales
    print(f"\n📈 ESTADÍSTICAS FINALES:")
    all_leads = Lead.objects.all()
    print(f"   Total leads: {all_leads.count()}")
    print(f"   - Sales: {all_leads.filter(case_type='sales').count()}")
    print(f"   - Support: {all_leads.filter(case_type='support').count()}")
    print(f"   - Recovery: {all_leads.filter(case_type='recovery').count()}")
    
    # Verificar conversaciones sin lead
    remaining_without_leads = Conversation.objects.filter(
        status='active',
        assigned_to__isnull=False,
        lead__isnull=True
    ).count()
    
    print(f"\n🔍 Conversaciones asignadas sin lead restantes: {remaining_without_leads}")
    
    print("\n✅ SISTEMA ARREGLADO!")

if __name__ == "__main__":
    fix_leads_system()