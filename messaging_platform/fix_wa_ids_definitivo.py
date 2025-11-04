#!/usr/bin/env python3
"""
Solución definitiva para eliminar identificadores WA-XXXX y 
unificar contactos automáticamente basado en números reales.
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Contact, Conversation, Message, Platform
from django.db.models import Count, Q
from django.db import transaction
import re

class ContactUnificationEngine:
    """Motor de unificación de contactos que previene duplicados de forma definitiva"""
    
    def __init__(self):
        self.platform = Platform.objects.get(name='whatsapp')
        
    def create_jid_mapping_table(self):
        """Crear tabla para mapear JIDs de WhatsApp a números reales"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Crear tabla de mapeo si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whatsapp_jid_mapping (
                    id SERIAL PRIMARY KEY,
                    jid VARCHAR(255) UNIQUE NOT NULL,
                    real_phone_number VARCHAR(50) NOT NULL,
                    contact_id INTEGER REFERENCES core_contact(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Crear índices para búsqueda rápida
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jid_mapping_jid 
                ON whatsapp_jid_mapping(jid);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jid_mapping_phone 
                ON whatsapp_jid_mapping(real_phone_number);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jid_mapping_contact 
                ON whatsapp_jid_mapping(contact_id);
            """)
            
            print("✅ Tabla de mapeo JID creada/actualizada")
    
    def add_jid_mapping(self, jid, real_phone, contact_id):
        """Agregar o actualizar mapeo JID → número real"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO whatsapp_jid_mapping (jid, real_phone_number, contact_id, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (jid) DO UPDATE SET
                    real_phone_number = EXCLUDED.real_phone_number,
                    contact_id = EXCLUDED.contact_id,
                    updated_at = NOW()
            """, [jid, real_phone, contact_id])
            
        print(f"📝 Mapeo guardado: {jid} → {real_phone} (Contacto {contact_id})")
    
    def get_contact_by_jid(self, jid):
        """Obtener contacto por JID usando la tabla de mapeo"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT contact_id, real_phone_number 
                FROM whatsapp_jid_mapping 
                WHERE jid = %s
            """, [jid])
            
            result = cursor.fetchone()
            if result:
                contact_id, real_phone = result
                try:
                    contact = Contact.objects.get(id=contact_id)
                    print(f"✅ Contacto encontrado por JID: {jid} → {real_phone} (ID {contact_id})")
                    return contact
                except Contact.DoesNotExist:
                    print(f"⚠️ Contacto {contact_id} no existe, limpiando mapeo obsoleto")
                    cursor.execute("DELETE FROM whatsapp_jid_mapping WHERE contact_id = %s", [contact_id])
        
        return None
    
    def extract_phone_from_jid_or_name(self, jid, push_name=None):
        """Extraer número de teléfono real de JID o pushName"""
        
        # Limpiar JID
        clean_jid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '')
        
        # Método 1: JID es directamente un número válido
        if re.match(r'^57\d{10}$', clean_jid):  # Número colombiano
            formatted = f"+57 {clean_jid[2:5]} {clean_jid[5:8]} {clean_jid[8:]}"
            print(f"📞 Número colombiano detectado en JID: {formatted}")
            return formatted
        
        if re.match(r'^1\d{10}$', clean_jid):  # Número USA/Canadá
            formatted = f"+1 {clean_jid[1:4]} {clean_jid[4:7]} {clean_jid[7:]}"
            print(f"📞 Número USA detectado en JID: {formatted}")
            return formatted
        
        # Método 2: Extraer de pushName si es un número
        if push_name:
            # Limpiar pushName de caracteres especiales y extraer dígitos
            digits = re.sub(r'[^\d+]', '', push_name)
            
            # Si parece un número de teléfono
            if re.match(r'^\+?57\d{10}$', digits):
                clean_digits = digits.replace('+', '')
                formatted = f"+57 {clean_digits[2:5]} {clean_digits[5:8]} {clean_digits[8:]}"
                print(f"📞 Número colombiano extraído del pushName '{push_name}': {formatted}")
                return formatted
            
            if re.match(r'^\+?1\d{10}$', digits):
                clean_digits = digits.replace('+', '')
                formatted = f"+1 {clean_digits[1:4]} {clean_digits[4:7]} {clean_digits[7:]}"
                print(f"📞 Número USA extraído del pushName '{push_name}': {formatted}")
                return formatted
        
        # Método 3: Buscar patrones conocidos en base de datos
        jid_digits = re.sub(r'[^\d]', '', clean_jid)
        if len(jid_digits) >= 10:
            # Buscar contactos existentes con números similares
            last_10_digits = jid_digits[-10:]
            
            similar_contacts = Contact.objects.filter(
                platform=self.platform,
                phone__iregex=f'.*{last_10_digits}.*'
            ).exclude(phone__startswith='WA-')
            
            if similar_contacts.exists():
                contact = similar_contacts.first()
                print(f"📞 Número similar encontrado en BD: {contact.phone} para JID {jid}")
                return contact.phone
        
        print(f"❌ No se pudo extraer número real de JID: {jid}")
        return None
    
    def find_or_create_unified_contact(self, jid, push_name=None):
        """Encuentra o crea un contacto unificado evitando duplicados WA-"""
        
        print(f"\n🔍 === BUSCANDO CONTACTO UNIFICADO ===")
        print(f"JID: {jid}")
        print(f"PushName: {push_name}")
        
        # Paso 1: Buscar en tabla de mapeo
        contact = self.get_contact_by_jid(jid)
        if contact:
            return contact
        
        # Paso 2: Extraer número real
        real_phone = self.extract_phone_from_jid_or_name(jid, push_name)
        
        # Paso 3: Si tenemos número real, buscar contacto existente
        if real_phone:
            existing_contact = Contact.objects.filter(
                platform=self.platform,
                phone=real_phone
            ).first()
            
            if existing_contact:
                print(f"✅ Contacto existente encontrado: ID {existing_contact.id}")
                # Guardar mapeo para futuras búsquedas
                self.add_jid_mapping(jid, real_phone, existing_contact.id)
                return existing_contact
        
        # Paso 4: Buscar contactos WA- que puedan coincidir
        jid_digits = re.sub(r'[^\d]', '', jid)
        if len(jid_digits) >= 10:
            wa_contacts = Contact.objects.filter(
                platform=self.platform,
                platform_user_id__startswith='WA-'
            )
            
            for wa_contact in wa_contacts:
                wa_digits = re.sub(r'[^\d]', '', wa_contact.platform_user_id)
                
                # Si los últimos 10 dígitos coinciden, probablemente es el mismo
                if len(wa_digits) >= 10 and len(jid_digits) >= 10:
                    if wa_digits[-10:] == jid_digits[-10:]:
                        print(f"🔄 Contacto WA- coincidente encontrado: ID {wa_contact.id}")
                        
                        # Actualizar con número real si lo tenemos
                        if real_phone:
                            wa_contact.phone = real_phone
                            wa_contact.platform_user_id = real_phone
                            wa_contact.name = real_phone
                            wa_contact.save()
                            print(f"🔄 Contacto actualizado con número real: {real_phone}")
                        
                        # Guardar mapeo
                        self.add_jid_mapping(jid, real_phone or wa_contact.phone, wa_contact.id)
                        return wa_contact
        
        # Paso 5: Crear nuevo contacto solo si es absolutamente necesario
        if real_phone:
            # Crear con número real
            new_contact = Contact.objects.create(
                platform=self.platform,
                platform_user_id=real_phone,
                phone=real_phone,
                name=real_phone
            )
            print(f"✅ Contacto nuevo creado con número real: {real_phone} (ID {new_contact.id})")
        else:
            # Último recurso: crear con WA-ID pero marcado para revisión
            clean_jid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '')
            wa_id = f"WA-{'-'.join([clean_jid[i:i+4] for i in range(0, len(clean_jid), 4)])}"
            
            new_contact = Contact.objects.create(
                platform=self.platform,
                platform_user_id=wa_id,
                phone=wa_id,
                name=f"REVISAR: {push_name or wa_id}"  # Marcar para revisión manual
            )
            print(f"⚠️ Contacto WA- creado (REQUIERE REVISIÓN): {wa_id} (ID {new_contact.id})")
        
        # Guardar mapeo
        self.add_jid_mapping(jid, new_contact.phone, new_contact.id)
        return new_contact
    
    def fix_all_wa_contacts(self):
        """Arreglar automáticamente todos los contactos WA- existentes"""
        
        wa_contacts = Contact.objects.filter(
            platform=self.platform,
            platform_user_id__startswith='WA-'
        )
        
        print(f"\n🔧 ARREGLANDO {wa_contacts.count()} CONTACTOS WA-")
        
        fixed_count = 0
        
        for contact in wa_contacts:
            print(f"\n📱 Procesando contacto ID {contact.id}: {contact.platform_user_id}")
            
            # Extraer dígitos del WA-ID
            wa_digits = re.sub(r'[^\d]', '', contact.platform_user_id)
            
            if len(wa_digits) >= 10:
                last_10 = wa_digits[-10:]
                
                # Buscar contacto con número real que coincida
                real_contacts = Contact.objects.filter(
                    platform=self.platform,
                    phone__iregex=f'.*{last_10}.*'
                ).exclude(phone__startswith='WA-').exclude(id=contact.id)
                
                if real_contacts.exists():
                    real_contact = real_contacts.first()
                    print(f"🔄 Fusionando con contacto real ID {real_contact.id}: {real_contact.phone}")
                    
                    # Fusionar conversaciones y mensajes
                    with transaction.atomic():
                        conversations = Conversation.objects.filter(contact=contact)
                        for conv in conversations:
                            conv.contact = real_contact
                            conv.save()
                        
                        # Eliminar contacto WA-
                        contact.delete()
                        
                        print(f"✅ Contacto WA- fusionado con número real: {real_contact.phone}")
                        fixed_count += 1
                
                else:
                    # Intentar convertir WA-ID a número real si es posible
                    if wa_digits.startswith('57') and len(wa_digits) == 12:
                        # Número colombiano
                        real_phone = f"+57 {wa_digits[2:5]} {wa_digits[5:8]} {wa_digits[8:]}"
                        contact.phone = real_phone
                        contact.platform_user_id = real_phone
                        contact.name = real_phone
                        contact.save()
                        print(f"🔄 Contacto WA- convertido a número real: {real_phone}")
                        fixed_count += 1
                    
                    elif wa_digits.startswith('1') and len(wa_digits) == 11:
                        # Número USA
                        real_phone = f"+1 {wa_digits[1:4]} {wa_digits[4:7]} {wa_digits[7:]}"
                        contact.phone = real_phone
                        contact.platform_user_id = real_phone
                        contact.name = real_phone
                        contact.save()
                        print(f"🔄 Contacto WA- convertido a número real: {real_phone}")
                        fixed_count += 1
        
        print(f"\n🎉 ARREGLOS COMPLETADOS: {fixed_count} contactos corregidos")
        
        return fixed_count

def main():
    engine = ContactUnificationEngine()
    
    print("🚀 INICIANDO SOLUCIÓN DEFINITIVA DE UNIFICACIÓN")
    print("=" * 60)
    
    # Crear infraestructura
    engine.create_jid_mapping_table()
    
    # Arreglar contactos existentes
    engine.fix_all_wa_contacts()
    
    # Mostrar estadísticas finales
    total_contacts = Contact.objects.filter(platform=engine.platform).count()
    wa_contacts = Contact.objects.filter(platform=engine.platform, platform_user_id__startswith='WA-').count()
    
    print(f"\n📊 ESTADÍSTICAS FINALES:")
    print(f"  - Total contactos: {total_contacts}")
    print(f"  - Contactos WA- restantes: {wa_contacts}")
    print(f"  - Porcentaje de números reales: {((total_contacts - wa_contacts) / total_contacts * 100):.1f}%")

if __name__ == "__main__":
    main()