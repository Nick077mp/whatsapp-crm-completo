import requests
import json
from django.conf import settings
from ..models import APIConfiguration, Platform, Contact, Conversation, Message
from django.utils import timezone


class TelegramService:
    """Servicio para integración con Telegram Bot API"""
    
    def __init__(self):
        try:
            platform = Platform.objects.get(name='telegram')
            self.config = APIConfiguration.objects.get(platform=platform)
            self.platform = platform
            if self.config and self.config.telegram_bot_token:
                self.base_url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}"
            else:
                self.base_url = None
        except (Platform.DoesNotExist, APIConfiguration.DoesNotExist):
            self.config = None
            self.platform = None
            self.base_url = None
    
    def is_configured(self):
        """Verifica si el servicio está configurado"""
        return self.config is not None and self.config.telegram_bot_token
    
    def send_message(self, chat_id, text, conversation=None):
        """Envía un mensaje de texto"""
        if not self.is_configured():
            return {'success': False, 'error': 'Telegram no configurado'}
        
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, json=payload)
            response_data = response.json()
            
            if response_data.get('ok'):
                if conversation:
                    message_id = str(response_data.get('result', {}).get('message_id', ''))
                    Message.objects.create(
                        conversation=conversation,
                        platform_message_id=message_id,
                        sender_type='agent',
                        message_type='text',
                        content=text
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
    
    def send_photo(self, chat_id, photo_url, caption='', conversation=None):
        """Envía una foto"""
        if not self.is_configured():
            return {'success': False, 'error': 'Telegram no configurado'}
        
        url = f"{self.base_url}/sendPhoto"
        
        payload = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption
        }
        
        try:
            response = requests.post(url, json=payload)
            response_data = response.json()
            
            if response_data.get('ok'):
                if conversation:
                    message_id = str(response_data.get('result', {}).get('message_id', ''))
                    Message.objects.create(
                        conversation=conversation,
                        platform_message_id=message_id,
                        sender_type='agent',
                        message_type='image',
                        content=caption,
                        media_url=photo_url
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
    
    def send_document(self, chat_id, document_url, caption='', conversation=None):
        """Envía un documento"""
        if not self.is_configured():
            return {'success': False, 'error': 'Telegram no configurado'}
        
        url = f"{self.base_url}/sendDocument"
        
        payload = {
            'chat_id': chat_id,
            'document': document_url,
            'caption': caption
        }
        
        try:
            response = requests.post(url, json=payload)
            response_data = response.json()
            
            if response_data.get('ok'):
                if conversation:
                    message_id = str(response_data.get('result', {}).get('message_id', ''))
                    Message.objects.create(
                        conversation=conversation,
                        platform_message_id=message_id,
                        sender_type='agent',
                        message_type='document',
                        content=caption,
                        media_url=document_url
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
        """Procesa los webhooks recibidos de Telegram"""
        try:
            # Telegram envía un objeto 'update'
            update_id = webhook_data.get('update_id')
            
            # Procesar mensaje
            if 'message' in webhook_data:
                self._process_incoming_message(webhook_data['message'])
            
            # Procesar mensaje editado
            elif 'edited_message' in webhook_data:
                self._process_edited_message(webhook_data['edited_message'])
            
            # Procesar callback query (botones inline)
            elif 'callback_query' in webhook_data:
                self._process_callback_query(webhook_data['callback_query'])
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_incoming_message(self, message_data):
        """Procesa un mensaje entrante"""
        try:
            message_id = str(message_data.get('message_id'))
            chat = message_data.get('chat', {})
            from_user = message_data.get('from', {})
            
            chat_id = str(chat.get('id'))
            user_id = str(from_user.get('id'))
            username = from_user.get('username', '')
            first_name = from_user.get('first_name', '')
            last_name = from_user.get('last_name', '')
            
            full_name = f"{first_name} {last_name}".strip()
            if not full_name:
                full_name = username or f"Usuario {user_id}"
            
            # Obtener o crear contacto
            contact, created = Contact.objects.get_or_create(
                platform=self.platform,
                platform_user_id=user_id,
                defaults={
                    'name': full_name
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
            
            # Verificar diferentes tipos de contenido
            if 'photo' in message_data:
                message_type = 'image'
                photos = message_data.get('photo', [])
                if photos:
                    # Obtener la foto de mayor resolución
                    photo = max(photos, key=lambda x: x.get('file_size', 0))
                    file_id = photo.get('file_id')
                    media_url = self._get_file_url(file_id)
                content = message_data.get('caption', '')
            
            elif 'video' in message_data:
                message_type = 'video'
                video = message_data.get('video', {})
                file_id = video.get('file_id')
                media_url = self._get_file_url(file_id)
                content = message_data.get('caption', '')
            
            elif 'document' in message_data:
                message_type = 'document'
                document = message_data.get('document', {})
                file_id = document.get('file_id')
                media_url = self._get_file_url(file_id)
                content = document.get('file_name', message_data.get('caption', ''))
            
            elif 'audio' in message_data:
                message_type = 'audio'
                audio = message_data.get('audio', {})
                file_id = audio.get('file_id')
                media_url = self._get_file_url(file_id)
                content = audio.get('title', '')
            
            elif 'voice' in message_data:
                message_type = 'audio'
                voice = message_data.get('voice', {})
                file_id = voice.get('file_id')
                media_url = self._get_file_url(file_id)
                content = 'Mensaje de voz'
            
            elif 'location' in message_data:
                message_type = 'location'
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
                    notes=f'Lead generado automáticamente desde Telegram'
                )
                conversation.lead = lead
                conversation.save()
            
        except Exception as e:
            print(f"Error procesando mensaje de Telegram: {str(e)}")
    
    def _process_edited_message(self, message_data):
        """Procesa un mensaje editado"""
        # Por ahora solo registramos que fue editado
        print(f"Mensaje editado: {message_data.get('message_id')}")
    
    def _process_callback_query(self, callback_data):
        """Procesa un callback query (botón presionado)"""
        callback_id = callback_data.get('id')
        data = callback_data.get('data')
        
        # Responder al callback
        if self.is_configured():
            url = f"{self.base_url}/answerCallbackQuery"
            requests.post(url, json={'callback_query_id': callback_id})
    
    def _get_file_url(self, file_id):
        """Obtiene la URL de un archivo"""
        if not self.is_configured():
            return None
        
        try:
            url = f"{self.base_url}/getFile"
            response = requests.post(url, json={'file_id': file_id})
            response_data = response.json()
            
            if response_data.get('ok'):
                file_path = response_data.get('result', {}).get('file_path')
                if file_path:
                    return f"https://api.telegram.org/file/bot{self.config.telegram_bot_token}/{file_path}"
        except Exception as e:
            print(f"Error obteniendo URL de archivo: {str(e)}")
        
        return None
    
    def set_webhook(self, webhook_url):
        """Configura el webhook de Telegram"""
        if not self.is_configured():
            return {'success': False, 'error': 'Telegram no configurado'}
        
        url = f"{self.base_url}/setWebhook"
        payload = {'url': webhook_url}
        
        try:
            response = requests.post(url, json=payload)
            response_data = response.json()
            
            if response_data.get('ok'):
                return {'success': True, 'data': response_data}
            else:
                return {'success': False, 'error': response_data}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_webhook_info(self):
        """Obtiene información del webhook configurado"""
        if not self.is_configured():
            return {'success': False, 'error': 'Telegram no configurado'}
        
        url = f"{self.base_url}/getWebhookInfo"
        
        try:
            response = requests.get(url)
            response_data = response.json()
            
            if response_data.get('ok'):
                return {'success': True, 'data': response_data.get('result')}
            else:
                return {'success': False, 'error': response_data}
        except Exception as e:
            return {'success': False, 'error': str(e)}

