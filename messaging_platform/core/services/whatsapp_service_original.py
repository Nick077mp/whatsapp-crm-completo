import requests
import json
from django.conf import settings
from ..models import APIConfiguration, Platform, Contact, Conversation, Message, ActivityLog
from django.utils import timezone


class WhatsAppService:
    """Servicio para integración con WhatsApp Business API"""
    
    def __init__(self):
        try:
            platform = Platform.objects.get(name='whatsapp')
            self.config = APIConfiguration.objects.get(platform=platform)
            self.platform = platform
            self.base_url = "https://graph.facebook.com/v18.0"
        except (Platform.DoesNotExist, APIConfiguration.DoesNotExist):
            self.config = None
            self.platform = None
    
    def is_configured(self):
        """Verifica si el servicio está configurado"""
        return (self.config is not None and 
                self.config.whatsapp_access_token and 
                self.config.whatsapp_phone_number_id)
    
    def send_message(self, to_number, message_text, conversation=None):
        """Envía un mensaje de texto"""
        if not self.is_configured():
            return {'success': False, 'error': 'WhatsApp no configurado'}
        
        url = f"{self.base_url}/{self.config.whatsapp_phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {self.config.whatsapp_access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messaging_product': 'whatsapp',
            'to': to_number,
            'type': 'text',
            'text': {
                'body': message_text
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            if response.status_code == 200:
                # Guardar mensaje en la base de datos
                if conversation:
                    message_id = response_data.get('messages', [{}])[0].get('id', '')
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
                    conversation.save()
                
                return {'success': True, 'data': response_data}
            else:
                return {'success': False, 'error': response_data}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_media(self, to_number, media_type, media_url, caption='', conversation=None):
        """Envía un mensaje con media (imagen, video, documento)"""
        if not self.is_configured():
            return {'success': False, 'error': 'WhatsApp no configurado'}
        
        url = f"{self.base_url}/{self.config.whatsapp_phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {self.config.whatsapp_access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messaging_product': 'whatsapp',
            'to': to_number,
            'type': media_type,
            media_type: {
                'link': media_url
            }
        }
        
        if caption and media_type in ['image', 'video', 'document']:
            payload[media_type]['caption'] = caption
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            if response.status_code == 200:
                if conversation:
                    message_id = response_data.get('messages', [{}])[0].get('id', '')
                    Message.objects.create(
                        conversation=conversation,
                        platform_message_id=message_id,
                        sender_type='agent',
                        message_type=media_type,
                        content=caption,
                        media_url=media_url
                    )
                    
                    conversation.last_message_at = timezone.now()
                    conversation.last_response_at = timezone.now()
                    conversation.is_answered = True
                    conversation.save()
                
                return {'success': True, 'data': response_data}
            else:
                return {'success': False, 'error': response_data}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def process_webhook(self, webhook_data):
        """Procesa los webhooks recibidos de WhatsApp"""
        try:
            entry = webhook_data.get('entry', [])[0]
            changes = entry.get('changes', [])[0]
            value = changes.get('value', {})
            
            # Procesar mensajes
            messages = value.get('messages', [])
            for message_data in messages:
                self._process_incoming_message(message_data, value)
            
            # Procesar estados de mensajes
            statuses = value.get('statuses', [])
            for status_data in statuses:
                self._process_message_status(status_data)
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_incoming_message(self, message_data, value):
        """Procesa un mensaje entrante"""
        try:
            # Obtener datos del contacto
            from_number = message_data.get('from')
            message_id = message_data.get('id')
            timestamp = message_data.get('timestamp')
            
            # Obtener o crear contacto
            contact_data = value.get('contacts', [{}])[0]
            contact_name = contact_data.get('profile', {}).get('name', '')
            
            contact, created = Contact.objects.get_or_create(
                platform=self.platform,
                platform_user_id=from_number,
                defaults={
                    'name': contact_name,
                    'phone': from_number
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
            message_type = message_data.get('type')
            content = ''
            media_url = None
            
            if message_type == 'text':
                content = message_data.get('text', {}).get('body', '')
            elif message_type == 'image':
                media_url = message_data.get('image', {}).get('link', '')
                content = message_data.get('image', {}).get('caption', '')
            elif message_type == 'video':
                media_url = message_data.get('video', {}).get('link', '')
                content = message_data.get('video', {}).get('caption', '')
            elif message_type == 'audio':
                media_url = message_data.get('audio', {}).get('link', '')
            elif message_type == 'document':
                media_url = message_data.get('document', {}).get('link', '')
                content = message_data.get('document', {}).get('filename', '')
            elif message_type == 'location':
                location = message_data.get('location', {})
                content = f"Ubicación: {location.get('latitude')}, {location.get('longitude')}"
            
            # Guardar mensaje
            Message.objects.create(
                conversation=conversation,
                platform_message_id=message_id,
                sender_type='contact',
                message_type=message_type,
                content=content,
                media_url=media_url
            )
            
            # Actualizar conversación
            conversation.last_message_at = timezone.now()
            if not conversation.first_response_at:
                conversation.is_answered = False
            conversation.save()
            
            # Crear lead automáticamente si no existe
            if not conversation.lead:
                from ..models import Lead
                lead = Lead.objects.create(
                    contact=contact,
                    case_type='sale',
                    status='new',
                    notes=f'Lead generado automáticamente desde WhatsApp'
                )
                conversation.lead = lead
                conversation.save()
            
        except Exception as e:
            print(f"Error procesando mensaje: {str(e)}")
    
    def _process_message_status(self, status_data):
        """Procesa el estado de un mensaje enviado"""
        try:
            message_id = status_data.get('id')
            status = status_data.get('status')  # sent, delivered, read, failed
            
            # Actualizar estado del mensaje si es necesario
            try:
                message = Message.objects.get(platform_message_id=message_id)
                if status == 'read':
                    message.is_read = True
                    message.save()
            except Message.DoesNotExist:
                pass
        except Exception as e:
            print(f"Error procesando estado: {str(e)}")
    
    def verify_webhook(self, mode, token, challenge):
        """Verifica el webhook de WhatsApp"""
        if not self.is_configured():
            return None
        
        verify_token = self.config.whatsapp_webhook_verify_token
        
        if mode == 'subscribe' and token == verify_token:
            return challenge
        return None

