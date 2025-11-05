#!/usr/bin/env python3
"""
Script para identificar y analizar contactos que NO son de Colombia
"""

import os
import sys
import sqlite3
import re
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
    from core.models import Contact, Conversation, Message, Lead, RecoveryCase
except ImportError as e:
    print(f"Error importing Django: {e}")
    print("Usando conexión directa a SQLite...")
    
    # Conexión directa a SQLite como fallback
    db_path = messaging_platform_dir / "db.sqlite3"
    if not db_path.exists():
        print(f"Base de datos no encontrada en: {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Obtener contactos directamente de SQLite
    cursor.execute("""
        SELECT id, name, phone, platform_user_id, platform_id, created_at
        FROM contacts 
        ORDER BY id
    """)
    
    contacts_data = cursor.fetchall()
    
    print(f"=== ANÁLISIS DE CONTACTOS (SQLite directo) ===")
    print(f"Total contactos encontrados: {len(contacts_data)}")
    print()
    
    colombian_contacts = []
    non_colombian_contacts = []
    unknown_contacts = []
    
    for contact_data in contacts_data:
        contact_id, name, phone, platform_user_id, platform_id, created_at = contact_data
        
        # Usar phone o platform_user_id para analizar
        phone_to_analyze = phone or platform_user_id or ''
        clean_phone = re.sub(r'[^0-9]', '', phone_to_analyze)
        
        contact_info = {
            'id': contact_id,
            'name': name,
            'phone': phone,
            'platform_user_id': platform_user_id,
            'clean_phone': clean_phone,
            'created_at': created_at
        }
        
        if clean_phone.startswith('57') and len(clean_phone) == 12:
            # Número colombiano válido (57 + 10 dígitos)
            colombian_contacts.append(contact_info)
        elif len(clean_phone) >= 10 and not clean_phone.startswith('57'):
            # Número extranjero (no empieza con 57)
            non_colombian_contacts.append(contact_info)
        else:
            # No se puede determinar o número incompleto
            unknown_contacts.append(contact_info)
    
    print(f"Contactos colombianos: {len(colombian_contacts)}")
    print(f"Contactos NO colombianos: {len(non_colombian_contacts)}")
    print(f"Contactos indeterminados: {len(unknown_contacts)}")
    print()
    
    if non_colombian_contacts:
        print("=== CONTACTOS NO COLOMBIANOS IDENTIFICADOS ===")
        for i, contact in enumerate(non_colombian_contacts, 1):
            country_code = ""
            if contact['clean_phone'].startswith('52'):
                country_code = " [MÉXICO]"
            elif contact['clean_phone'].startswith('1'):
                country_code = " [USA/CANADÁ]"
            elif contact['clean_phone'].startswith('34'):
                country_code = " [ESPAÑA]"
            elif contact['clean_phone'].startswith('54'):
                country_code = " [ARGENTINA]"
            
            print(f"{i:2d}. ID: {contact['id']:3d} | Nombre: {contact['name'] or 'Sin nombre':<20} | "
                  f"Teléfono: {contact['phone'] or 'N/A':<15} | "
                  f"Platform ID: {contact['platform_user_id'] or 'N/A':<15} | "
                  f"Limpio: {contact['clean_phone']:<15}{country_code}")
        
        print()
        print("=== RESUMEN DE DATOS A ELIMINAR ===")
        
        # Contar conversaciones relacionadas
        non_colombian_ids = [c['id'] for c in non_colombian_contacts]
        placeholders = ','.join(['?' for _ in non_colombian_ids])
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM conversations 
            WHERE contact_id IN ({placeholders})
        """, non_colombian_ids)
        
        conversations_count = cursor.fetchone()[0]
        
        # Contar mensajes relacionados
        cursor.execute(f"""
            SELECT COUNT(*) FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.contact_id IN ({placeholders})
        """, non_colombian_ids)
        
        messages_count = cursor.fetchone()[0]
        
        # Contar leads relacionados
        cursor.execute(f"""
            SELECT COUNT(*) FROM leads 
            WHERE contact_id IN ({placeholders})
        """, non_colombian_ids)
        
        leads_count = cursor.fetchone()[0]
        
        # Contar casos de recuperación
        cursor.execute(f"""
            SELECT COUNT(*) FROM recovery_cases 
            WHERE contact_id IN ({placeholders})
        """, non_colombian_ids)
        
        recovery_cases_count = cursor.fetchone()[0]
        
        print(f"Contactos a eliminar: {len(non_colombian_contacts)}")
        print(f"Conversaciones a eliminar: {conversations_count}")
        print(f"Mensajes a eliminar: {messages_count}")
        print(f"Leads a eliminar: {leads_count}")
        print(f"Casos de recuperación a eliminar: {recovery_cases_count}")
        print()
        
        print("⚠️  ADVERTENCIA: Esta operación eliminará permanentemente todos estos datos")
        print("   Se recomienda hacer un backup completo antes de proceder")
    
    else:
        print("✅ No se encontraron contactos NO colombianos para eliminar")
    
    conn.close()
    sys.exit(0)

# Si Django está disponible, usar los modelos ORM
def analyze_with_django():
    print("=== ANÁLISIS DE CONTACTOS (Django ORM) ===")
    print()
    
    contacts = Contact.objects.all()
    print(f'Total de contactos: {contacts.count()}')
    print()
    
    colombian_contacts = []
    non_colombian_contacts = []
    unknown_contacts = []
    
    for contact in contacts:
        phone = contact.phone or contact.platform_user_id or ''
        clean_phone = re.sub(r'[^0-9]', '', phone)
        
        if clean_phone.startswith('57') and len(clean_phone) == 12:
            # Número colombiano válido
            colombian_contacts.append(contact)
        elif len(clean_phone) >= 10 and not clean_phone.startswith('57'):
            # Número extranjero
            non_colombian_contacts.append(contact)
        else:
            # No se puede determinar
            unknown_contacts.append(contact)
    
    print(f'Contactos colombianos: {len(colombian_contacts)}')
    print(f'Contactos NO colombianos: {len(non_colombian_contacts)}')
    print(f'Contactos indeterminados: {len(unknown_contacts)}')
    print()
    
    if non_colombian_contacts:
        print('=== CONTACTOS NO COLOMBIANOS IDENTIFICADOS ===')
        for i, contact in enumerate(non_colombian_contacts, 1):
            clean_phone = re.sub(r'[^0-9]', '', contact.phone or contact.platform_user_id or '')
            country_code = ""
            if clean_phone.startswith('52'):
                country_code = " [MÉXICO]"
            elif clean_phone.startswith('1'):
                country_code = " [USA/CANADÁ]"
            elif clean_phone.startswith('34'):
                country_code = " [ESPAÑA]"
            elif clean_phone.startswith('54'):
                country_code = " [ARGENTINA]"
            
            print(f'{i:2d}. ID: {contact.id:3d} | Nombre: {contact.name or "Sin nombre":<20} | '
                  f'Tel: {contact.phone or "N/A":<15} | '
                  f'Platform ID: {contact.platform_user_id or "N/A":<15} | '
                  f'Limpio: {clean_phone:<15}{country_code}')
        
        print()
        print("=== RESUMEN DE DATOS A ELIMINAR ===")
        
        non_colombian_ids = [c.id for c in non_colombian_contacts]
        
        conversations_count = Conversation.objects.filter(contact_id__in=non_colombian_ids).count()
        messages_count = Message.objects.filter(conversation__contact_id__in=non_colombian_ids).count()
        leads_count = Lead.objects.filter(contact_id__in=non_colombian_ids).count()
        recovery_cases_count = RecoveryCase.objects.filter(contact_id__in=non_colombian_ids).count()
        
        print(f"Contactos a eliminar: {len(non_colombian_contacts)}")
        print(f"Conversaciones a eliminar: {conversations_count}")
        print(f"Mensajes a eliminar: {messages_count}")
        print(f"Leads a eliminar: {leads_count}")
        print(f"Casos de recuperación a eliminar: {recovery_cases_count}")
        print()
        
        print("⚠️  ADVERTENCIA: Esta operación eliminará permanentemente todos estos datos")
        print("   Se recomienda hacer un backup completo antes de proceder")
        
    else:
        print("✅ No se encontraron contactos NO colombianos para eliminar")

# Ejecutar análisis
if __name__ == "__main__":
    try:
        analyze_with_django()
    except Exception as e:
        print(f"Error con Django: {e}")
        print("Continuando con análisis directo...")