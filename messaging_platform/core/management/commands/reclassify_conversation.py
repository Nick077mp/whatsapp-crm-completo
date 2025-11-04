from django.core.management.base import BaseCommand
from core.models import Conversation, Lead
from core.services.classification_service import ContactClassificationService

class Command(BaseCommand):
    help = 'Reclasifica conversaciones según el departamento y crea leads automáticamente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--conversation-id',
            type=int,
            help='ID de conversación específica a reclasificar'
        )
        parser.add_argument(
            '--to-department',
            choices=['support', 'sales'],
            help='Departamento al que reclasificar'
        )

    def handle(self, *args, **options):
        conversation_id = options.get('conversation_id')
        to_department = options.get('to_department')
        
        if conversation_id and to_department:
            # Reclasificar conversación específica
            try:
                conv = Conversation.objects.get(id=conversation_id)
                old_funnel = conv.funnel_type
                conv.funnel_type = to_department
                conv.save()
                
                # Crear lead si es ventas y no existe
                if to_department == 'sales' and not conv.lead:
                    lead = Lead.objects.create(
                        contact=conv.contact,
                        case_type='sales',
                        status='new',
                        notes=f'Lead creado por reclasificación manual de {old_funnel} a {to_department}'
                    )
                    conv.lead = lead
                    conv.save()
                    
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Conversación {conversation_id} reclasificada de {old_funnel} a {to_department}'
                    )
                )
                
            except Conversation.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Conversación {conversation_id} no encontrada')
                )
        else:
            # Mostrar conversaciones disponibles
            self.stdout.write('=== CONVERSACIONES DISPONIBLES ===')
            for conv in Conversation.objects.all():
                self.stdout.write(
                    f'ID: {conv.id} | Contacto: {conv.contact.name} | Departamento: {conv.funnel_type} | Mensajes: {conv.messages.count()}'
                )
            
            self.stdout.write('\nPara reclasificar, usa:')
            self.stdout.write('python manage.py reclassify_conversation --conversation-id=XX --to-department=sales|support')