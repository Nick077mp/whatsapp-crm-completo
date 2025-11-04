#!/usr/bin/env python
"""
Script para limpiar la base de datos manteniendo solo el superusuario
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import (
    User, Platform, Contact, Lead, Conversation, 
    Message, Template, Reminder, ActivityLog, RecoveryCase
)

def clean_database():
    """Limpia todos los datos excepto el superusuario"""
    
    print("🧹 Iniciando limpieza de la base de datos...")
    
    # Obtener información del superusuario antes de limpiar
    superusers = User.objects.filter(is_superuser=True)
    admin_users = User.objects.filter(role='admin')
    
    print(f"📋 Superusuarios encontrados: {superusers.count()}")
    print(f"📋 Usuarios admin encontrados: {admin_users.count()}")
    
    # Contar registros antes de limpiar
    print("\n📊 Registros ANTES de la limpieza:")
    print(f"   - Usuarios: {User.objects.count()}")
    print(f"   - Conversaciones: {Conversation.objects.count()}")
    print(f"   - Mensajes: {Message.objects.count()}")
    print(f"   - Contactos: {Contact.objects.count()}")
    print(f"   - Leads: {Lead.objects.count()}")
    print(f"   - Plantillas: {Template.objects.count()}")
    print(f"   - Recordatorios: {Reminder.objects.count()}")
    print(f"   - Logs de actividad: {ActivityLog.objects.count()}")
    print(f"   - Casos de recuperación: {RecoveryCase.objects.count()}")
    
    # Limpiar datos en orden (respetando foreign keys)
    print("\n🗑️  Eliminando registros...")
    
    # 1. Eliminar mensajes
    messages_deleted = Message.objects.all().delete()[0]
    print(f"   ✅ Mensajes eliminados: {messages_deleted}")
    
    # 2. Eliminar recordatorios
    reminders_deleted = Reminder.objects.all().delete()[0]
    print(f"   ✅ Recordatorios eliminados: {reminders_deleted}")
    
    # 3. Eliminar casos de recuperación
    recovery_deleted = RecoveryCase.objects.all().delete()[0]
    print(f"   ✅ Casos de recuperación eliminados: {recovery_deleted}")
    
    # 4. Eliminar leads
    leads_deleted = Lead.objects.all().delete()[0]
    print(f"   ✅ Leads eliminados: {leads_deleted}")
    
    # 5. Eliminar conversaciones
    conversations_deleted = Conversation.objects.all().delete()[0]
    print(f"   ✅ Conversaciones eliminadas: {conversations_deleted}")
    
    # 6. Eliminar contactos
    contacts_deleted = Contact.objects.all().delete()[0]
    print(f"   ✅ Contactos eliminados: {contacts_deleted}")
    
    # 7. Eliminar plantillas
    templates_deleted = Template.objects.all().delete()[0]
    print(f"   ✅ Plantillas eliminadas: {templates_deleted}")
    
    # 8. Eliminar logs de actividad
    logs_deleted = ActivityLog.objects.all().delete()[0]
    print(f"   ✅ Logs de actividad eliminados: {logs_deleted}")
    
    # 9. Eliminar usuarios (excepto superusuarios y admins)
    users_to_keep = User.objects.filter(Q(is_superuser=True) | Q(role='admin'))
    users_to_delete = User.objects.exclude(Q(is_superuser=True) | Q(role='admin'))
    users_deleted = users_to_delete.delete()[0]
    print(f"   ✅ Usuarios eliminados: {users_deleted}")
    print(f"   ✅ Usuarios mantenidos: {users_to_keep.count()}")
    
    # Verificar usuarios restantes
    print("\n👤 Usuarios restantes:")
    for user in users_to_keep:
        print(f"   - {user.username} ({user.email}) - Rol: {user.role} - Superuser: {user.is_superuser}")
    
    # Contar registros después de limpiar
    print("\n📊 Registros DESPUÉS de la limpieza:")
    print(f"   - Usuarios: {User.objects.count()}")
    print(f"   - Conversaciones: {Conversation.objects.count()}")
    print(f"   - Mensajes: {Message.objects.count()}")
    print(f"   - Contactos: {Contact.objects.count()}")
    print(f"   - Leads: {Lead.objects.count()}")
    print(f"   - Plantillas: {Template.objects.count()}")
    print(f"   - Recordatorios: {Reminder.objects.count()}")
    print(f"   - Logs de actividad: {ActivityLog.objects.count()}")
    print(f"   - Casos de recuperación: {RecoveryCase.objects.count()}")
    
    print("\n✅ ¡Limpieza completada exitosamente!")

if __name__ == '__main__':
    from django.db.models import Q
    clean_database()