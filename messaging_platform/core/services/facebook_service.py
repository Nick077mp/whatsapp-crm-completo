import requests
import json
import hmac
import hashlib
from django.conf import settings
from ..models import APIConfiguration, Platform, Contact, Conversation, Message
from django.utils import timezone


class FacebookService:
    """Servicio para integración con Facebook Messenger API"""
    
    def __init__(self):
        try:
            platform = Platform.objects.get(name='facebook')
            self.config = APIConfiguration.objects.get(platform=platform)
            self.platform = platform
            self.base_url = "https://graph.facebook.com/v18.0"
        except (Platform.DoesNotExist, APIConfiguration.DoesNotExist):
            self.config = None
            self.platform = None
    
    def is_configured(self):
        """Verifica si el servicio está configurado"""
        return (self.config is not None and 
                self.config.facebook_page_access_token and 
                self.config.facebook_page_id)
    
    def send_message(self, recipient_id, message_text, conversation=None):
        """Envía un mensaje de texto"""
        if not self.is_configured():
            return {'success': False, 'error': 'Facebook Messenger no configurado'}
        
        url = f"{self.base_url}/me/messages"
        params = {'access_token': self.config.facebook_page_access_token}
        
        payload = {
            'recipient': {'id': recipient_id},
            'message': {'text': message_text}
        }
        
        try:
            response = requests.post(url, params=params, json=payload)
            response_data = response.json()
            
            if response.status_code == 200:
                if conversation:
                    message_id = response_data.get('message_id', '')
                    Message.objects.create(
                        conversation=conversation,
                        platform_message_id=message_id,
                        sender_type='agent',
                        message_type='text',
                        content=message_text
                    )
                    
                    conversation.last_message_at = timezone.now()
                    conversation.last_response_at = timezone.now()
                    conversation.is_answered = True
                    conversation.needs_response = False  # El agente respondió
                    conversation.save()
                
                return {'success': True, 'data': response_data}
            else:
                return {'success': False, 'error': response_data}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_attachment(self, recipient_id, attachment_type, attachment_url, conversation=None):
        """Envía un mensaje con adjunto (imagen, video, archivo)"""
        if not self.is_configured():
            return {'success': False, 'error': 'Facebook Messenger no configurado'}
        
        url = f"{self.base_url}/me/messages"
        params = {'access_token': self.config.facebook_page_access_token}
        
        payload = {
            'recipient': {'id': recipient_id},
            'message': {
                'attachment': {
                    'type': attachment_type,
                    'payload': {
                        'url': attachment_url,
                        'is_reusable': True
                    }
                }
            }
        }
        
        try:
            response = requests.post(url, params=params, json=payload)
            response_data = response.json()
            
            if response.status_code == 200:
                if conversation:
                    message_id = response_data.get('message_id', '')
                    Message.objects.create(
                        conversation=conversation,
                        platform_message_id=message_id,
                        sender_type='agent',
                        message_type=attachment_type,
                        content='',
                        media_url=attachment_url
                    )
                    
                    conversation.last_message_at = timezone.now()
                    conversation.last_response_at = timezone.now()
                    conversation.is_answered = True
                    conversation.needs_response = False  # El agente respondió
                    conversation.save()
                
                return {'success': True, 'data': response_data}
            else:
                return {'success': False, 'error': response_data}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def process_webhook(self, webhook_data):
        """Procesa los webhooks recibidos de Facebook Messenger"""
        try:
            entries = webhook_data.get('entry', [])
            
            for entry in entries:
                messaging_events = entry.get('messaging', [])
                
                for event in messaging_events:
                    sender_id = event.get('sender', {}).get('id')
                    recipient_id = event.get('recipient', {}).get('id')
                    
                    # Procesar mensaje
                    if 'message' in event:
                        self._process_incoming_message(event, sender_id)
                    
                    # Procesar postback
                    elif 'postback' in event:
                        self._process_postback(event, sender_id)
                    
                    # Procesar lectura
                    elif 'read' in event:
                        self._process_read(event, sender_id)
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_incoming_message(self, event, sender_id):
        """Procesa un mensaje entrante"""
        try:
            message_data = event.get('message', {})
            message_id = message_data.get('mid')
            timestamp = event.get('timestamp')
            
            # Obtener información del usuario
            user_info = self._get_user_info(sender_id)
            
            # Obtener o crear contacto
            contact, created = Contact.objects.get_or_create(
                platform=self.platform,
                platform_user_id=sender_id,
                defaults={
                    'name': user_info.get('name', ''),
                    'profile_pic': user_info.get('profile_pic', '')
                }
            )
            
            # Obtener o crear conversación
            conversation, created = Conversation.objects.get_or_create(
                contact=contact,
                status='active',
                defaults={
                    'last_message_at': timezone.now()
                }
            )
            
            # Procesar contenido del mensaje
            message_type = 'text'
            content = message_data.get('text', '')
            media_url = None
            
            # Verificar si tiene adjuntos
            if 'attachments' in message_data:
                attachments = message_data.get('attachments', [])
                if attachments:
                    attachment = attachments[0]
                    message_type = attachment.get('type', 'file')
                    media_url = attachment.get('payload', {}).get('url', '')
                    content = f"Adjunto: {message_type}"
            
            # Guardar mensaje
            Message.objects.create(
                conversation=conversation,
                platform_message_id=message_id,
                sender_type='contact',
                message_type=message_type,
                content=content,
                media_url=media_url
            )
            
            # Actualizar conversación - Marcar que necesita respuesta cuando llega mensaje de contacto
            conversation.last_message_at = timezone.now()
            conversation.needs_response = True  # El contacto envió mensaje, necesita respuesta
            if not conversation.first_response_at:
                conversation.is_answered = False
            conversation.save()
            
            # Crear lead automáticamente si no existe
            if not conversation.lead:
                from ..models import Lead
                lead = Lead.objects.create(
                    contact=contact,
                    case_type='sales',
                    status='new',
                    notes=f'Lead generado automáticamente desde Facebook Messenger'
                )
                conversation.lead = lead
                conversation.save()
            
        except Exception as e:
            print(f"Error procesando mensaje de Facebook: {str(e)}")
    
    def _process_postback(self, event, sender_id):
        """Procesa un postback (botón presionado)"""
        try:
            postback = event.get('postback', {})
            payload = postback.get('payload', '')
            title = postback.get('title', '')
            
            # Aquí puedes manejar diferentes payloads según tu lógica
            print(f"Postback recibido: {payload} - {title}")
        except Exception as e:
            print(f"Error procesando postback: {str(e)}")
    
    def _process_read(self, event, sender_id):
        """Procesa confirmación de lectura"""
        try:
            read_data = event.get('read', {})
            watermark = read_data.get('watermark')
            
            # Marcar mensajes como leídos
            Message.objects.filter(
                conversation__contact__platform_user_id=sender_id,
                sender_type='agent',
                is_read=False
            ).update(is_read=True)
        except Exception as e:
            print(f"Error procesando lectura: {str(e)}")
    
    def _get_user_info(self, user_id):
        """Obtiene información del usuario desde Facebook"""
        if not self.is_configured():
            return {}
        
        url = f"{self.base_url}/{user_id}"
        params = {
            'fields': 'first_name,last_name,profile_pic',
            'access_token': self.config.facebook_page_access_token
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return {
                    'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                    'profile_pic': data.get('profile_pic', '')
                }
        except Exception as e:
            print(f"Error obteniendo info de usuario: {str(e)}")
        
        return {}
    
    def verify_webhook(self, mode, token, challenge):
        """Verifica el webhook de Facebook"""
        if not self.is_configured():
            return None
        
        verify_token = self.config.facebook_verify_token
        
        if mode == 'subscribe' and token == verify_token:
            return challenge
        return None
    
    def verify_signature(self, payload, signature):
        """Verifica la firma del webhook"""
        if not self.is_configured():
            return False
        
        app_secret = self.config.facebook_app_secret
        
        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)

