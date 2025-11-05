#!/usr/bin/env python3
"""
Script para eliminar de forma SEGURA todos los contactos que NO son de Colombia
junto con sus conversaciones, mensajes y datos relacionados.

ADVERTENCIA: Esta operación es IRREVERSIBLE
"""

import os
import sys
import re
import sqlite3
from datetime import datetime
from pathlib import Path

# Configurar path para Django
current_dir = Path(__file__).parent
messaging_platform_dir = current_dir / "messaging_platform"
sys.path.insert(0, str(messaging_platform_dir))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    import django
    django.setup()
    from django.db import transaction
    from core.models import Contact, Conversation, Message, Lead, RecoveryCase, Reminder, ActivityLog
    DJANGO_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Django: {e}")
    DJANGO_AVAILABLE = False


def create_backup():
    """Crear backup de la base de datos antes de eliminar"""
    print("🔄 Creando backup de la base de datos...")
    
    db_path = messaging_platform_dir / "db.sqlite3"
    if not db_path.exists():
        print(f"❌ Base de datos no encontrada: {db_path}")
        return False
    
    # Crear nombre de backup con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"db_backup_before_non_colombian_deletion_{timestamp}.sqlite3"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        backup_size = backup_path.stat().st_size / (1024 * 1024)  # MB
        print(f"✅ Backup creado exitosamente: {backup_path}")
        print(f"   Tamaño: {backup_size:.2f} MB")
        return str(backup_path)
    except Exception as e:
        print(f"❌ Error creando backup: {e}")
        return False


def identify_non_colombian_contacts():
    """Identificar contactos que NO son colombianos"""
    if not DJANGO_AVAILABLE:
        print("❌ Django no disponible, no se puede continuar")
        return []
    
    print("🔍 Identificando contactos no colombianos...")
    
    contacts = Contact.objects.all()
    non_colombian_contacts = []
    
    for contact in contacts:
        phone = contact.phone or contact.platform_user_id or ''
        clean_phone = re.sub(r'[^0-9]', '', phone)
        
        # Identificar números NO colombianos
        if len(clean_phone) >= 10 and not clean_phone.startswith('57'):
            # Es un número extranjero
            country_info = ""
            if clean_phone.startswith('52'):
                country_info = "MÉXICO"
            elif clean_phone.startswith('1'):
                country_info = "USA/CANADÁ"
            elif clean_phone.startswith('34'):
                country_info = "ESPAÑA"
            elif clean_phone.startswith('51'):
                country_info = "PERÚ"
            elif clean_phone.startswith('507'):
                country_info = "HONDURAS"
            elif clean_phone.startswith('44'):
                country_info = "REINO UNIDO"
            else:
                country_info = "OTRO PAÍS"
            
            non_colombian_contacts.append({
                'contact': contact,
                'clean_phone': clean_phone,
                'country': country_info
            })
    
    return non_colombian_contacts


def get_related_data_counts(contact_ids):
    """Obtener conteos de datos relacionados que serán eliminados"""
    if not DJANGO_AVAILABLE:
        return {}
    
    return {
        'conversations': Conversation.objects.filter(contact_id__in=contact_ids).count(),
        'messages': Message.objects.filter(conversation__contact_id__in=contact_ids).count(),
        'leads': Lead.objects.filter(contact_id__in=contact_ids).count(),
        'recovery_cases': RecoveryCase.objects.filter(contact_id__in=contact_ids).count(),
        'reminders': Reminder.objects.filter(lead__contact_id__in=contact_ids).count(),
        'activity_logs': ActivityLog.objects.filter(conversation__contact_id__in=contact_ids).count()
    }


def confirm_deletion(non_colombian_contacts, related_counts):
    """Confirmar la eliminación con el usuario"""
    print("\n" + "="*60)
    print("⚠️  CONFIRMACIÓN DE ELIMINACIÓN - OPERACIÓN IRREVERSIBLE")
    print("="*60)
    print()
    
    print(f"Se eliminarán {len(non_colombian_contacts)} contactos NO colombianos:")
    print()
    
    for i, contact_data in enumerate(non_colombian_contacts, 1):
        contact = contact_data['contact']
        country = contact_data['country']
        print(f"{i:2d}. {contact.name or 'Sin nombre'} | {contact.phone or contact.platform_user_id} | {country}")
    
    print()
    print("DATOS RELACIONADOS QUE TAMBIÉN SE ELIMINARÁN:")
    print(f"- Conversaciones: {related_counts.get('conversations', 0)}")
    print(f"- Mensajes: {related_counts.get('messages', 0)}")
    print(f"- Leads: {related_counts.get('leads', 0)}")
    print(f"- Casos de recuperación: {related_counts.get('recovery_cases', 0)}")
    print(f"- Recordatorios: {related_counts.get('reminders', 0)}")
    print(f"- Logs de actividad: {related_counts.get('activity_logs', 0)}")
    print()
    
    print("⚠️  ADVERTENCIA: Esta operación es IRREVERSIBLE")
    print("   Solo se conservarán los contactos colombianos (código +57)")
    print()
    
    while True:
        confirmation = input("¿Está COMPLETAMENTE SEGURO de eliminar estos datos? (escriba 'ELIMINAR DEFINITIVAMENTE' para confirmar): ")
        
        if confirmation == 'ELIMINAR DEFINITIVAMENTE':
            print("✅ Confirmación recibida. Procediendo con la eliminación...")
            return True
        elif confirmation.lower() in ['no', 'n', 'cancelar', 'cancel', 'exit', 'salir']:
            print("❌ Operación cancelada por el usuario.")
            return False
        else:
            print("⚠️  Debe escribir exactamente 'ELIMINAR DEFINITIVAMENTE' para confirmar")


def delete_non_colombian_contacts(non_colombian_contacts):
    """Eliminar contactos no colombianos y todos sus datos relacionados"""
    if not DJANGO_AVAILABLE:
        print("❌ Django no disponible, no se puede continuar")
        return False
    
    contact_ids = [contact_data['contact'].id for contact_data in non_colombian_contacts]
    
    print(f"\n🗑️  Iniciando eliminación de {len(contact_ids)} contactos no colombianos...")
    
    try:
        with transaction.atomic():
            # 1. Eliminar recordatorios relacionados con leads de estos contactos
            reminders_deleted = Reminder.objects.filter(lead__contact_id__in=contact_ids).delete()
            print(f"   ✅ Recordatorios eliminados: {reminders_deleted[0] if reminders_deleted[0] else 0}")
            
            # 2. Eliminar logs de actividad relacionados
            activity_logs_deleted = ActivityLog.objects.filter(conversation__contact_id__in=contact_ids).delete()
            print(f"   ✅ Logs de actividad eliminados: {activity_logs_deleted[0] if activity_logs_deleted[0] else 0}")
            
            # 3. Eliminar casos de recuperación
            recovery_cases_deleted = RecoveryCase.objects.filter(contact_id__in=contact_ids).delete()
            print(f"   ✅ Casos de recuperación eliminados: {recovery_cases_deleted[0] if recovery_cases_deleted[0] else 0}")
            
            # 4. Eliminar leads
            leads_deleted = Lead.objects.filter(contact_id__in=contact_ids).delete()
            print(f"   ✅ Leads eliminados: {leads_deleted[0] if leads_deleted[0] else 0}")
            
            # 5. Eliminar mensajes (se eliminan automáticamente con las conversaciones por CASCADE)
            messages_deleted = Message.objects.filter(conversation__contact_id__in=contact_ids).delete()
            print(f"   ✅ Mensajes eliminados: {messages_deleted[0] if messages_deleted[0] else 0}")
            
            # 6. Eliminar conversaciones (CASCADE eliminará mensajes relacionados)
            conversations_deleted = Conversation.objects.filter(contact_id__in=contact_ids).delete()
            print(f"   ✅ Conversaciones eliminadas: {conversations_deleted[0] if conversations_deleted[0] else 0}")
            
            # 7. Finalmente eliminar los contactos
            contacts_deleted = Contact.objects.filter(id__in=contact_ids).delete()
            print(f"   ✅ Contactos eliminados: {contacts_deleted[0] if contacts_deleted[0] else 0}")
            
            print(f"\n✅ ELIMINACIÓN COMPLETADA EXITOSAMENTE")
            print(f"   Total de contactos no colombianos eliminados: {contacts_deleted[0] if contacts_deleted[0] else 0}")
            
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR durante la eliminación: {e}")
        print("   La transacción se ha revertido automáticamente")
        return False


def verify_deletion():
    """Verificar que la eliminación fue exitosa"""
    if not DJANGO_AVAILABLE:
        return
    
    print("\n🔍 Verificando eliminación...")
    
    # Re-analizar contactos restantes
    contacts = Contact.objects.all()
    non_colombian_remaining = []
    
    for contact in contacts:
        phone = contact.phone or contact.platform_user_id or ''
        clean_phone = re.sub(r'[^0-9]', '', phone)
        
        if len(clean_phone) >= 10 and not clean_phone.startswith('57'):
            non_colombian_remaining.append(contact)
    
    print(f"   Total de contactos restantes: {contacts.count()}")
    print(f"   Contactos no colombianos restantes: {len(non_colombian_remaining)}")
    
    if len(non_colombian_remaining) == 0:
        print("   ✅ Verificación exitosa: No quedan contactos no colombianos")
    else:
        print(f"   ⚠️  Advertencia: Aún quedan {len(non_colombian_remaining)} contactos no colombianos")
        for contact in non_colombian_remaining:
            print(f"      - {contact.id}: {contact.name} | {contact.phone}")


def main():
    """Función principal del script"""
    print("="*60)
    print("🇨🇴 ELIMINACIÓN DE CONTACTOS NO COLOMBIANOS")
    print("="*60)
    print()
    
    if not DJANGO_AVAILABLE:
        print("❌ Django no está disponible. Verifique el entorno virtual.")
        return
    
    # 1. Crear backup
    backup_path = create_backup()
    if not backup_path:
        print("❌ No se pudo crear el backup. Abortando operación por seguridad.")
        return
    
    # 2. Identificar contactos no colombianos
    non_colombian_contacts = identify_non_colombian_contacts()
    
    if not non_colombian_contacts:
        print("✅ No se encontraron contactos no colombianos para eliminar.")
        print("   Todos los contactos existentes son de Colombia.")
        return
    
    # 3. Obtener conteos de datos relacionados
    contact_ids = [contact_data['contact'].id for contact_data in non_colombian_contacts]
    related_counts = get_related_data_counts(contact_ids)
    
    # 4. Confirmar eliminación
    if not confirm_deletion(non_colombian_contacts, related_counts):
        print("Operación cancelada.")
        return
    
    # 5. Ejecutar eliminación
    success = delete_non_colombian_contacts(non_colombian_contacts)
    
    if success:
        # 6. Verificar eliminación
        verify_deletion()
        
        print(f"\n🎉 PROCESO COMPLETADO EXITOSAMENTE")
        print(f"   Backup guardado en: {backup_path}")
        print(f"   Solo contactos colombianos (+57) permanecen en la base de datos")
    else:
        print(f"\n❌ La eliminación falló. La base de datos no se ha modificado.")
        print(f"   Backup disponible en: {backup_path}")


if __name__ == "__main__":
    main()