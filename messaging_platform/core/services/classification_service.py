from django.utils import timezone
from django.db.models import Q
from ..models import Contact, Lead, Conversation


class ContactClassificationService:
    """
    Servicio para clasificar automáticamente contactos y conversaciones
    según el número de teléfono del destinatario
    """
    
    # Números de teléfono para clasificación
    SUPPORT_NUMBER = "573022620031"  # Número de soporte: +57 302 2620031
    SALES_NUMBER = "573243230276"    # Número de ventas: +57 324 323 0276
    
    @classmethod
    def classify_contact_by_recipient(cls, recipient_number):
        """
        Clasifica un contacto según el número al que envió el mensaje
        
        Args:
            recipient_number (str): Número de teléfono del destinatario
            
        Returns:
            str: 'support' o 'sales'
        """
        # Limpiar número (quitar espacios, guiones, etc.)
        clean_number = ''.join(filter(str.isdigit, recipient_number))
        
        # Clasificar según el número destinatario
        if clean_number.endswith(cls.SALES_NUMBER) or cls.SALES_NUMBER in clean_number:
            return 'sales'
        elif clean_number.endswith(cls.SUPPORT_NUMBER) or cls.SUPPORT_NUMBER in clean_number:
            return 'support'
        else:
            # Por defecto, todo va a soporte
            return 'support'
    
    @classmethod
    def auto_create_lead_for_sales_conversation(cls, conversation):
        """
        Crea automáticamente un lead si la conversación es de ventas/recuperación
        
        Args:
            conversation (Conversation): La conversación a procesar
        """
        if not conversation.lead:  # Solo si no existe ya un lead
            classification = cls.classify_contact_by_recipient(
                conversation.contact.platform_user_id
            )
            
            if classification == 'sales':
                # Crear lead automáticamente
                lead = Lead.objects.create(
                    conversation=conversation,
                    contact=conversation.contact,
                    case_type='sales',
                    priority='medium',
                    status='new',
                    created_by=None,  # Creado automáticamente
                    notes=f"Lead creado automáticamente - Mensaje recibido en número de ventas"
                )
                
                # Actualizar el funnel de la conversación
                conversation.funnel_type = 'sales'
                conversation.save()
                
                return lead
        
        return None
    
    @classmethod
    def get_conversations_by_department(cls, department):
        """
        Obtiene conversaciones filtradas por departamento
        
        Args:
            department (str): 'support' o 'sales'
            
        Returns:
            QuerySet: Conversaciones filtradas
        """
        if department == 'sales':
            # Conversaciones que llegaron al número de ventas
            return Conversation.objects.filter(
                Q(contact__platform_user_id__contains=cls.SALES_NUMBER) |
                Q(funnel_type='sales') |
                Q(lead__case_type='sales')
            ).distinct()
        else:
            # Conversaciones de soporte (resto)
            return Conversation.objects.exclude(
                Q(contact__platform_user_id__contains=cls.SALES_NUMBER) |
                Q(funnel_type='sales') |
                Q(lead__case_type='sales')
            ).distinct()