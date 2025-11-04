"""
Comando para limpiar contactos duplicados y unificar conversaciones
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import Contact, Conversation, Platform
import re


class Command(BaseCommand):
    help = 'Limpia contactos duplicados y unifica conversaciones por número real'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar en modo de prueba sin hacer cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write('🔍 Ejecutando en modo DRY RUN (sin cambios)')
        
        try:
            whatsapp_platform = Platform.objects.get(name='whatsapp')
        except Platform.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ Plataforma WhatsApp no encontrada'))
            return

        # Obtener todos los contactos de WhatsApp
        contacts = Contact.objects.filter(platform=whatsapp_platform)
        
        # Agrupar contactos por número real
        phone_groups = {}
        wa_id_contacts = []
        
        for contact in contacts:
            # Extraer número real del phone o platform_user_id
            real_phone = self.extract_real_phone(contact.phone or contact.platform_user_id)
            
            if real_phone:
                if real_phone not in phone_groups:
                    phone_groups[real_phone] = []
                phone_groups[real_phone].append(contact)
            elif contact.platform_user_id.startswith('WA-'):
                wa_id_contacts.append(contact)
        
        merged_count = 0
        
        # Procesar grupos con múltiples contactos (duplicados)
        for phone, group_contacts in phone_groups.items():
            if len(group_contacts) > 1:
                merged_count += self.merge_contact_group(group_contacts, phone, dry_run)
        
        # Intentar asociar WA-IDs con números reales existentes
        for wa_contact in wa_id_contacts:
            # Buscar si hay algún contacto con número real similar
            potential_matches = []
            
            for phone, group_contacts in phone_groups.items():
                # Heurística simple: si el WA-ID contiene dígitos del número real
                phone_digits = re.sub(r'[^\d]', '', phone)
                wa_id = wa_contact.platform_user_id
                
                # Si hay coincidencia de dígitos, es potencialmente el mismo contacto
                if len(phone_digits) >= 8 and phone_digits[-8:] in wa_id:
                    potential_matches.extend(group_contacts)
            
            if potential_matches:
                # Fusionar con el primer match encontrado
                main_contact = potential_matches[0]
                if not dry_run:
                    self.merge_wa_contact_to_main(wa_contact, main_contact)
                    merged_count += 1
                
                self.stdout.write(
                    f'🔗 Fusionando WA-ID {wa_contact.platform_user_id} → {main_contact.phone}'
                )

        self.stdout.write(
            self.style.SUCCESS(f'✅ Procesamiento completado. Contactos fusionados: {merged_count}')
        )

    def extract_real_phone(self, phone_string):
        """Extrae el número real de teléfono de una cadena"""
        if not phone_string:
            return None
        
        # Limpiar cadena
        clean = re.sub(r'[^\d\+]', '', phone_string)
        
        # Patrones de números colombianos
        if clean.startswith('+57') and len(clean) >= 12:
            return phone_string  # Ya está formateado
        elif clean.startswith('57') and len(clean) == 12:
            # Formato: 573001234567 → +57 300 123 4567
            return f"+57 {clean[2:5]} {clean[5:8]} {clean[8:]}"
        elif len(clean) == 10 and clean.startswith('3'):
            # Formato: 3001234567 → +57 300 123 4567
            return f"+57 {clean[0:3]} {clean[3:6]} {clean[6:]}"
        
        return None

    def merge_contact_group(self, contacts, real_phone, dry_run):
        """Fusiona un grupo de contactos duplicados"""
        # El contacto principal será el que tenga el platform_user_id más limpio (número real)
        main_contact = None
        
        for contact in contacts:
            if not contact.platform_user_id.startswith('WA-') and not main_contact:
                main_contact = contact
                break
        
        if not main_contact:
            main_contact = contacts[0]
        
        self.stdout.write(f'📞 Fusionando {len(contacts)} contactos para {real_phone}')
        
        merged_count = 0
        
        for contact in contacts:
            if contact.id != main_contact.id:
                if not dry_run:
                    self.merge_wa_contact_to_main(contact, main_contact)
                
                self.stdout.write(f'  ↳ Fusionando {contact.platform_user_id} → {main_contact.platform_user_id}')
                merged_count += 1
        
        return merged_count

    def merge_wa_contact_to_main(self, duplicate_contact, main_contact):
        """Fusiona un contacto duplicado al principal"""
        # Migrar conversaciones
        duplicate_conversations = Conversation.objects.filter(contact=duplicate_contact)
        
        for duplicate_conv in duplicate_conversations:
            # Buscar conversación activa del contacto principal
            main_conversation = Conversation.objects.filter(
                contact=main_contact,
                status='active'
            ).first()
            
            if main_conversation:
                # Migrar mensajes
                duplicate_conv.messages.update(conversation=main_conversation)
                
                # Actualizar timestamps si es necesario
                if duplicate_conv.last_message_at and main_conversation.last_message_at:
                    if duplicate_conv.last_message_at > main_conversation.last_message_at:
                        main_conversation.last_message_at = duplicate_conv.last_message_at
                        main_conversation.save()
                
                # Eliminar conversación duplicada
                duplicate_conv.delete()
            else:
                # Transferir propiedad de la conversación
                duplicate_conv.contact = main_contact
                duplicate_conv.save()
        
        # Actualizar información del contacto principal si es necesario
        if not main_contact.phone and duplicate_contact.phone:
            main_contact.phone = duplicate_contact.phone
        
        if duplicate_contact.name and (not main_contact.name or main_contact.name == main_contact.platform_user_id):
            main_contact.name = duplicate_contact.name
        
        main_contact.save()
        
        # Eliminar contacto duplicado
        duplicate_contact.delete()