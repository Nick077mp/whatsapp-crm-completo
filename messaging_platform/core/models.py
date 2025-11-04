from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Usuario extendido con campos adicionales"""
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=[
        ('admin', 'Administrador'),
        ('support', 'Soporte'),
        ('sales', 'Ventas/Recuperación')
    ], default='support')
    is_active_chat = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'users'


class Platform(models.Model):
    """Plataformas de mensajería disponibles"""
    name = models.CharField(max_length=50, unique=True)  # whatsapp, facebook, telegram
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'platforms'
    
    def __str__(self):
        return self.name


class Contact(models.Model):
    """Contactos/Clientes de la organización"""
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name='contacts')
    platform_user_id = models.CharField(max_length=255)  # ID del usuario en la plataforma
    name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    profile_pic = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contacts'
        unique_together = ['platform', 'platform_user_id']
    
    def __str__(self):
        return f"{self.name or self.phone or 'Sin nombre'} ({self.platform.name})"
    
    @property
    def display_name(self):
        """Nombre para mostrar - exactamente como aparece en WhatsApp"""
        if self.name and self.name.strip():
            return self.name
        # Mostrar el número exactamente como lo recibimos de WhatsApp
        return self.phone or "Usuario sin identificar"
    
    @property 
    def display_initials(self):
        """Iniciales para avatar"""
        if self.name and self.name.strip():
            return self.name[0].upper()
        elif self.phone:
            return self.phone[0].upper()
        return "U"
    
    @property
    def whatsapp_number(self):
        """Obtener número limpio para enlaces de WhatsApp"""
        if self.platform.name != 'whatsapp':
            return None
            
        # Usar el phone si está disponible y es válido
        if self.phone:
            # Limpiar el número de formatos como +57 300 734 1192
            clean_phone = ''.join(filter(str.isdigit, self.phone))
            
            # Si es un número colombiano válido, devolverlo
            if clean_phone.startswith('57') and len(clean_phone) == 12:
                return clean_phone
            elif len(clean_phone) == 10:
                # Agregar código de país colombiano si falta
                return f"57{clean_phone}"
                
        # Si no hay phone válido, intentar extraer del platform_user_id
        if self.platform_user_id:
            # Limpiar prefijos como WA-
            clean_id = self.platform_user_id.replace('WA-', '').replace('-', '')
            
            # Si parece un número colombiano válido
            if clean_id.startswith('57') and len(clean_id) == 12:
                return clean_id
                
            # Si el ID contiene un número colombiano válido
            import re
            colombian_match = re.search(r'57\d{10}', clean_id)
            if colombian_match:
                return colombian_match.group(0)
                
        # Fallback: usar platform_user_id limpio
        return ''.join(filter(str.isdigit, self.platform_user_id or ''))
    
    @property
    def display_initials(self):
        """Iniciales para avatar"""
        if self.name and self.name.strip():
            return self.name[0].upper()
        elif self.phone:
            return self.phone[0].upper()
        return "U"


class RecoveryCase(models.Model):
    """Casos de recuperación de clientes"""
    REASON_CHOICES = [
        ('price_objection', 'Objeción de Precio'),
        ('competitor', 'Se fue a la Competencia'),
        ('timing', 'Mal Momento'),
        ('feature_missing', 'Falta de Funcionalidad'),
        ('service_issue', 'Problema de Servicio'),
        ('communication', 'Falla de Comunicación'),
        ('other', 'Otro')
    ]
    
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('recovered', 'Recuperado'),
        ('lost', 'Perdido Definitivamente'),
        ('paused', 'Pausado')
    ]
    
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='recovery_cases')
    conversation = models.ForeignKey('Conversation', on_delete=models.CASCADE, related_name='recovery_case')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recovery_cases_created')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recovery_cases_assigned')
    
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    reason_notes = models.TextField(blank=True, null=True, help_text="Detalles específicos sobre la razón")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    recovery_strategy = models.TextField(blank=True, null=True, help_text="Estrategia planificada para la recuperación")
    
    # Métricas
    attempts_count = models.IntegerField(default=0, help_text="Número de intentos de contacto")
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    target_recovery_date = models.DateField(null=True, blank=True, help_text="Fecha objetivo para recuperación")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'recovery_cases'
        unique_together = ['contact', 'conversation']  # Un caso por conversación
    
    def __str__(self):
        return f"Recuperación {self.id} - {self.contact.display_name}"


class Lead(models.Model):
    """Leads generados desde las conversaciones"""
    CASE_TYPE_CHOICES = [
        ('sales', 'Ventas'),
        ('support', 'Soporte'),
        ('recovery', 'Recuperación')
    ]
    
    STATUS_CHOICES = [
        ('new', 'Nuevo'),
        ('in_progress', 'En Progreso'),
        ('negotiation', 'Negociación'),
        ('closed_won', 'Cerrado Ganado'),
        ('closed_lost', 'Cerrado Perdido')
    ]
    
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='leads')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    case_type = models.CharField(max_length=20, choices=CASE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'leads'
    
    def __str__(self):
        return f"Lead {self.id} - {self.contact.name}"
    
    @property
    def dynamic_status_display(self):
        """Devuelve el estado basado en la conversación activa del contacto"""
        # Buscar la conversación más reciente del contacto
        latest_conversation = self.contact.conversations.filter(status='active').order_by('-last_message_at').first()
        
        if not latest_conversation or latest_conversation.funnel_type == 'none':
            return self.get_status_display()
        
        # Mapeo de etapas de embudo a estados de lead
        stage_to_status = {
            # Ventas
            'sales_initial': 'Chat Inicial',
            'sales_negotiation': 'Negociación',
            'sales_debate': 'Debate',
            'sales_closing': 'Finalización',
            # Soporte
            'support_initial': 'Contacto Inicial',
            'support_process': 'En Proceso',
            'support_closing': 'Finalizando',
            # Recuperación
            'recovery_initial': 'Contacto Inicial',
            'recovery_evaluation': 'Evaluación',
            'recovery_proposal': 'Propuesta',
            'recovery_followup': 'Seguimiento',
            'recovery_closing': 'Cierre',
        }
        
        return stage_to_status.get(latest_conversation.funnel_stage, self.get_status_display())
    
    @property
    def funnel_based_status_class(self):
        """Devuelve la clase CSS basada en el estado del embudo"""
        latest_conversation = self.contact.conversations.filter(status='active').order_by('-last_message_at').first()
        
        if not latest_conversation or latest_conversation.funnel_type == 'none':
            return f'status-{self.status}'
        
        # Mapeo de etapas a clases CSS
        stage_to_class = {
            'sales_initial': 'status-new',
            'sales_negotiation': 'status-negotiation',
            'sales_debate': 'status-negotiation',
            'sales_closing': 'status-closing',
            'support_initial': 'status-new',
            'support_process': 'status-in-progress',
            'support_closing': 'status-closing',
            'recovery_initial': 'status-new',
            'recovery_evaluation': 'status-in-progress',
            'recovery_proposal': 'status-negotiation',
            'recovery_followup': 'status-in-progress',
            'recovery_closing': 'status-closing',
        }
        
        return stage_to_class.get(latest_conversation.funnel_stage, f'status-{self.status}')


class Conversation(models.Model):
    """Conversaciones/Diálogos con contactos"""
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('pending', 'Pendiente'),
        ('closed', 'Cerrado')
    ]
    
    FUNNEL_CHOICES = [
        ('sales', 'Ventas'),
        ('support', 'Soporte'),
        ('recovery', 'Recuperación'),
        ('none', 'Ninguno')
    ]
    
    FUNNEL_STAGE_CHOICES = [
        # Ventas
        ('sales_initial', 'Chat Inicial'),
        ('sales_negotiation', 'Negociación'),
        ('sales_debate', 'Debate'),
        ('sales_closing', 'Finalización'),
        # Soporte
        ('support_initial', 'Contacto Inicial'),
        ('support_process', 'Proceso de Soporte'),
        ('support_closing', 'Finalización'),
        # Recuperación
        ('recovery_initial', 'Contacto Inicial'),
        ('recovery_evaluation', 'Evaluación'),
        ('recovery_proposal', 'Propuesta'),
        ('recovery_followup', 'Seguimiento'),
        ('recovery_closing', 'Cierre'),
        # Ninguno
        ('none', 'Sin Embudo')
    ]
    
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='conversations')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    funnel_type = models.CharField(max_length=20, choices=FUNNEL_CHOICES, default='none')
    funnel_stage = models.CharField(max_length=30, choices=FUNNEL_STAGE_CHOICES, default='none')
    last_message_at = models.DateTimeField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    last_response_at = models.DateTimeField(null=True, blank=True)
    is_answered = models.BooleanField(default=False)
    needs_response = models.BooleanField(default=False, help_text="Indica si la conversación necesita respuesta del agente")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversations'
    
    def __str__(self):
        return f"Conversación {self.id} - {self.contact.name}"
    
    def calculate_response_time(self):
        """Calcula el tiempo de respuesta en segundos"""
        if self.first_response_at and self.created_at:
            return (self.first_response_at - self.created_at).total_seconds()
        return None
    
    def is_overdue(self, minutes=5):
        """
        Verifica si la conversación está vencida (sin respuesta por X minutos)
        """
        from django.utils import timezone
        from datetime import timedelta
        
        if not self.needs_response or not self.last_message_at:
            return False
        
        # Obtener el último mensaje del contacto (no del agente)
        last_contact_message = self.messages.filter(sender_type='contact').order_by('-created_at').first()
        
        if not last_contact_message:
            return False
        
        # Verificar si han pasado más de X minutos desde el último mensaje del contacto
        time_threshold = timezone.now() - timedelta(minutes=minutes)
        return last_contact_message.created_at < time_threshold


class Message(models.Model):
    """Mensajes individuales dentro de conversaciones"""
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Texto'),
        ('image', 'Imagen'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Documento'),
        ('location', 'Ubicación')
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    platform_message_id = models.CharField(max_length=255, unique=True)
    sender_type = models.CharField(max_length=10, choices=[
        ('contact', 'Contacto'),
        ('agent', 'Agente')
    ])
    sender_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    content = models.TextField()
    media_url = models.URLField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'messages'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender_type}: {self.content[:50]}..."


class Template(models.Model):
    """Plantillas de respuestas predefinidas"""
    name = models.CharField(max_length=255)
    content = models.TextField()
    category = models.CharField(max_length=50, blank=True, null=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name='templates', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'templates'
    
    def __str__(self):
        return self.name


class Reminder(models.Model):
    """Recordatorios para seguimiento de leads"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='reminders')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    reminder_date = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reminders'
        ordering = ['reminder_date']
    
    def __str__(self):
        return f"Recordatorio {self.id} - {self.title}"


class ActivityLog(models.Model):
    """Log de actividades para reportes"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='activities')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    action = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'activity_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username if self.user else 'Sistema'} - {self.action}"


class APIConfiguration(models.Model):
    """Configuración de APIs de mensajería"""
    platform = models.OneToOneField(Platform, on_delete=models.CASCADE, related_name='api_config')
    
    # WhatsApp Business API
    whatsapp_phone_number_id = models.CharField(max_length=255, blank=True, null=True)
    whatsapp_business_account_id = models.CharField(max_length=255, blank=True, null=True)
    whatsapp_access_token = models.TextField(blank=True, null=True)
    whatsapp_webhook_verify_token = models.CharField(max_length=255, blank=True, null=True)
    
    # Facebook Messenger
    facebook_page_id = models.CharField(max_length=255, blank=True, null=True)
    facebook_page_access_token = models.TextField(blank=True, null=True)
    facebook_app_secret = models.CharField(max_length=255, blank=True, null=True)
    facebook_verify_token = models.CharField(max_length=255, blank=True, null=True)
    
    # Telegram
    telegram_bot_token = models.CharField(max_length=255, blank=True, null=True)
    telegram_webhook_url = models.URLField(blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'api_configurations'
    
    def __str__(self):
        return f"Config {self.platform.name}"
