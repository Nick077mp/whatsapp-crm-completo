import requests
import json
from django.conf import settings
from ..models import APIConfiguration, Platform, Contact, Conversation, Message, ActivityLog
from django.utils import timezone


class WhatsAppService:
    """Servicio para integración con WhatsApp usando Baileys"""
    
    def __init__(self):
        try:
            platform = Platform.objects.get(name='whatsapp')
            self.platform = platform
            # Para Baileys usaremos el bridge local
            self.bridge_url = "http://localhost:3000"
        except Platform.DoesNotExist:
            self.platform = None
            self.bridge_url = "http://localhost:3000"
    
    def is_configured(self):
        """Verifica si el servicio está configurado"""
        try:
            # Verificar si el bridge está activo
            response = requests.get(f"{self.bridge_url}/status", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def is_connected(self):
        """Verifica si WhatsApp está conectado"""
        try:
            response = requests.get(f"{self.bridge_url}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('connected', False)
            return False
        except:
            return False
    
    def get_qr_code(self):
        """Obtiene el código QR para autenticación"""
        try:
            response = requests.get(f"{self.bridge_url}/qr", timeout=5)
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': 'No hay código QR disponible'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_message(self, to_number, message_text, conversation=None):
        """Envía un mensaje de texto"""
        if not self.is_configured():
            return {'success': False, 'error': 'Bridge de WhatsApp no disponible'}
        
        if not self.is_connected():
            return {'success': False, 'error': 'WhatsApp no está conectado'}
        
        # Normalizar número destino para el bridge (evitar timeouts por JIDs inválidos)
        normalized_to = self._normalize_phone_for_bridge(to_number)
        print(f"🔍 DEBUG SEND: to_number={to_number}, normalized_to={normalized_to}, message_text={message_text}")
        payload = {
            'to': normalized_to,
            'message': message_text
        }
        print(f"🔍 DEBUG PAYLOAD: {payload}")
        
        try:
            # Aumentar timeout porque el envío vía WhatsApp puede demorar
            response = requests.post(f"{self.bridge_url}/send-message", json=payload, timeout=25)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('success'):
                # Guardar mensaje en la base de datos
                if conversation:
                    message_id = response_data.get('message_id', '')
                    
                    # Si message_id está vacío, generar uno único
                    if not message_id:
                        import uuid
                        from datetime import datetime
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        message_id = f"agent_{timestamp}_{str(uuid.uuid4())[:8]}"
                    
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
                    conversation.needs_response = False  # El agente respondió, ya no necesita respuesta
                    conversation.save()
                
                return {'success': True, 'data': response_data}
            else:
                return {'success': False, 'error': response_data.get('error', 'Error desconocido')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_media(self, to_number, media_type, media_url, caption='', conversation=None):
        """Envía un mensaje con media (imagen, video, documento)"""
        if not self.is_configured():
            return {'success': False, 'error': 'Bridge de WhatsApp no disponible'}
        
        if not self.is_connected():
            return {'success': False, 'error': 'WhatsApp no está conectado'}
        
        # Por ahora solo soportamos imágenes
        if media_type == 'image':
            payload = {
                'to': self._normalize_phone_for_bridge(to_number),
                'image_url': media_url,
                'caption': caption
            }
            
            try:
                response = requests.post(f"{self.bridge_url}/send-image", json=payload, timeout=30)
                response_data = response.json()
                
                if response.status_code == 200 and response_data.get('success'):
                    if conversation:
                        message_id = response_data.get('message_id', '')
                        
                        # Si message_id está vacío, generar uno único
                        if not message_id:
                            import uuid
                            from datetime import datetime
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            message_id = f"agent_{timestamp}_{str(uuid.uuid4())[:8]}"
                        
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
                        conversation.needs_response = False  # El agente respondió, ya no necesita respuesta
                        conversation.save()
                    
                    return {'success': True, 'data': response_data}
                else:
                    return {'success': False, 'error': response_data.get('error', 'Error desconocido')}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        else:
            return {'success': False, 'error': f'Tipo de media no soportado: {media_type}'}
    
    def restart_connection(self):
        """Reinicia la conexión de WhatsApp"""
        try:
            response = requests.post(f"{self.bridge_url}/restart", timeout=10)
            return response.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def process_webhook(self, webhook_data):
        """Procesa los webhooks recibidos del bridge de Baileys"""
        try:
            # El webhook viene del bridge de Baileys con esta estructura:
            # {
            #     "from": "1234567890",
            #     "message_id": "abc123",
            #     "timestamp": 1234567890,
            #     "type": "text",
            #     "content": "Hola",
            #     "media_url": null
            # }
            
            from_number = webhook_data.get('from')
            received_at = webhook_data.get('received_at')  # Número de negocio que recibió
            message_id = webhook_data.get('message_id')
            timestamp = webhook_data.get('timestamp')
            message_type = webhook_data.get('type', 'text')
            content = webhook_data.get('content', '')
            media_url = webhook_data.get('media_url')
            
            if not from_number or not message_id:
                return {'success': False, 'error': 'Datos incompletos en webhook'}
            
            # Limpiar número telefónico de sufijos de WhatsApp (por si acaso)
            clean_from_number = from_number.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '').replace('@g.us', '')
            
            # Intentar extraer número real si viene formateado desde el bridge
            real_phone_number = self._extract_real_phone_number(from_number)
            
            # Obtener o crear contacto usando unificación por número real
            contact = self._get_or_create_unified_contact(clean_from_number, real_phone_number)
            
            # Clasificar el departamento basado en el número de destino
            from .classification_service import ContactClassificationService
            
            # Clasificar el departamento basado en el número que recibió el mensaje
            if received_at:
                # Usar el número que recibió el mensaje para clasificar
                department = ContactClassificationService.classify_contact_by_recipient(received_at)
                print(f"🔍 DEBUG: Mensaje recibido en {received_at} -> clasificado como {department}")
            else:
                # Fallback: clasificar por número del contacto
                department = ContactClassificationService.classify_contact_by_recipient(contact.phone or clean_from_number)
                print(f"🔍 DEBUG: Sin received_at, clasificado por contacto {contact.phone or clean_from_number} -> {department}")
            
            # Si no se puede clasificar, usar soporte por defecto
            if not department:
                department = 'support'
            
            # Obtener o crear conversación activa
            conversation, created = Conversation.objects.get_or_create(
                contact=contact,
                status='active',
                defaults={
                    'last_message_at': timezone.now(),
                    'funnel_type': department  # Asignar departamento usando funnel_type
                }
            )
            
            # Si la conversación ya existía, actualizar funnel_type si no estaba asignado o era 'none'
            if not created and (conversation.funnel_type == 'none' or not conversation.funnel_type):
                conversation.funnel_type = department
                conversation.save()
            
            # Crear mensaje con soporte mejorado para media
            message = Message.objects.create(
                conversation=conversation,
                platform_message_id=message_id,
                sender_type='contact',
                message_type=message_type,
                content=content or self._get_media_fallback_content(message_type),
                media_url=media_url
            )
            
            # Actualizar conversación - Marcar que necesita respuesta cuando llega mensaje de contacto
            conversation.last_message_at = timezone.now()
            conversation.needs_response = True  # El contacto envió mensaje, necesita respuesta
            if not conversation.first_response_at:
                conversation.is_answered = False
            conversation.save()
            
            # Crear lead automáticamente solo para conversaciones de ventas
            if not conversation.lead and department == 'sales':
                from ..models import Lead
                lead = Lead.objects.create(
                    contact=contact,
                    case_type='sales',
                    status='new',
                    notes=f'Lead generado automáticamente desde WhatsApp (Baileys)'
                )
                conversation.lead = lead
                conversation.save()
            
            return {'success': True}
            
        except Exception as e:
            # Log error silently or use proper logging
            return {'success': False, 'error': str(e)}
    
    def _extract_real_phone_number(self, from_number):
        """Extrae el número real de teléfono desde el ID de WhatsApp (INTERNACIONAL)"""
        from ..utils.international_phone import formatear_numero_internacional, limpiar_numero
        import re
        
        # Limpiar el número de sufijos de WhatsApp
        clean_number = from_number.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '').replace('@g.us', '')
        
        # Si ya viene formateado desde el bridge (ej: +52 55 1234 5678)
        if clean_number.startswith('+'):
            # Validar que sea un formato internacional válido
            formatted = formatear_numero_internacional(clean_number)
            if formatted:
                return formatted
        
        # Intentar formatear como número internacional directo
        formatted = formatear_numero_internacional(clean_number)
        if formatted:
            return formatted
        
        # RETROCOMPATIBILIDAD: Si es un número de 10 dígitos, asumir Colombia
        clean_digits = limpiar_numero(clean_number)
        if len(clean_digits) == 10 and clean_digits.isdigit() and clean_digits.startswith('3'):
            colombia_number = '57' + clean_digits
            formatted = formatear_numero_internacional(colombia_number)
            if formatted:
                return formatted
        
        # Buscar patrones de números dentro de IDs complejos
        # Buscar cualquier secuencia de 10-15 dígitos que pueda ser un número válido
        number_matches = re.findall(r'(\d{10,15})', clean_number)
        for match in number_matches:
            formatted = formatear_numero_internacional(match)
            if formatted:
                return formatted
        
        # Buscar números colombianos específicamente (retrocompatibilidad)
        colombian_match = re.search(r'57(\d{10})', clean_number)
        if colombian_match:
            full_number = '57' + colombian_match.group(1)
            formatted = formatear_numero_internacional(full_number)
            if formatted:
                return formatted
        
        # Buscar móviles colombianos (retrocompatibilidad)
        mobile_match = re.search(r'(3\d{9})', clean_number)
        if mobile_match:
            colombia_mobile = '57' + mobile_match.group(1)
            formatted = formatear_numero_internacional(colombia_mobile)
            if formatted:
                return formatted
        
        # Si no se puede extraer un número válido, devolver None
        return None
    
    def process_outgoing_webhook(self, webhook_data):
        """Procesa los webhooks de mensajes salientes (enviados desde WhatsApp directamente)"""
        try:
            # Debug logging
            print(f"🔍 DEBUG Webhook saliente recibido: {webhook_data}")
            
            # Crear log de actividad
            ActivityLog.objects.create(
                user=None,
                action='outgoing_webhook_received',
                description=f'Webhook saliente recibido: {webhook_data}'
            )
            # El webhook viene del bridge de Baileys con esta estructura:
            # {
            #     "to": "+57 300 734 1192",
            #     "message_id": "abc123",
            #     "timestamp": 1234567890,
            #     "type": "text",
            #     "content": "Hola, sí estoy disponible",
            #     "from_me": true
            # }
            
            to_number = webhook_data.get('to')  # Cliente que recibe
            from_number = webhook_data.get('from')  # Nuestro número que envía
            message_id = webhook_data.get('message_id')
            timestamp = webhook_data.get('timestamp')
            message_type = webhook_data.get('type', 'text')
            content = webhook_data.get('content', '')
            from_me = webhook_data.get('from_me', False)
            
            if not to_number or not message_id or not from_me:
                return {'success': False, 'error': 'Datos incompletos en webhook saliente'}
            
            print(f"📤 DEBUG: Mensaje saliente DE {from_number} PARA {to_number}")
            
            # Determinar departamento basado en NUESTRO número que envía el mensaje
            from .classification_service import ContactClassificationService
            if from_number and from_number != 'unknown':
                department = ContactClassificationService.classify_contact_by_recipient(from_number)
                print(f"🎯 DEBUG: Departamento determinado por número de origen {from_number}: {department}")
            else:
                # Si no tenemos número de origen, usar soporte como default
                department = 'support'
                print(f"⚠️ DEBUG: Sin número de origen, usando departamento default: {department}")
            
            # Limpiar número telefónico de formatos (por si acaso)
            clean_to_number = to_number.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '').replace('@g.us', '')
            
            # Intentar extraer número real si viene formateado desde el bridge
            real_phone_number = self._extract_real_phone_number(clean_to_number)
            
            # Buscar contacto existente usando múltiples estrategias
            contact = None
            
            # Estrategia 1: Buscar por platform_user_id exacto
            try:
                contact = Contact.objects.get(
                    platform=self.platform,
                    platform_user_id=clean_to_number
                )
            except Contact.DoesNotExist:
                pass
            
            # Estrategia 2: Buscar por formato WA- (ej: WA-2699-1357-9118-670)
            if not contact:
                try:
                    contact = Contact.objects.filter(
                        platform=self.platform,
                        platform_user_id__startswith='WA-'
                    ).filter(
                        platform_user_id__contains=clean_to_number.replace('WA-', '').replace('-', '')
                    ).first()
                except:
                    pass
            
            # Estrategia 3: Buscar por coincidencia de dígitos en platform_user_id
            if not contact:
                # Extraer solo los dígitos del to_number
                digits_only = ''.join(filter(str.isdigit, clean_to_number))
                if digits_only:
                    try:
                        # Buscar contactos que contengan estos dígitos
                        contacts = Contact.objects.filter(
                            platform=self.platform
                        ).exclude(platform_user_id='')
                        
                        for c in contacts:
                            contact_digits = ''.join(filter(str.isdigit, c.platform_user_id))
                            if contact_digits and contact_digits == digits_only:
                                contact = c
                                break
                    except:
                        pass
            
            # Estrategia 4: Buscar por phone si existe
            if not contact and real_phone_number:
                try:
                    contact = Contact.objects.get(
                        platform=self.platform,
                        phone=real_phone_number
                    )
                except Contact.DoesNotExist:
                    pass
            
            # Logging de búsqueda de contacto
            print(f"🔍 DEBUG Buscando contacto para: {clean_to_number}")
            print(f"🔍 DEBUG Contacto encontrado: {contact.id if contact else 'No encontrado'}")
            
            if contact:
                print(f"🔍 DEBUG Contacto: {contact.display_name} (ID: {contact.platform_user_id})")
            
            # Si no se encuentra el contacto, crear uno nuevo (esto no debería pasar normalmente)
            if not contact:
                print(f"⚠️ ADVERTENCIA: Creando contacto nuevo para webhook saliente: {clean_to_number}")
                contact = Contact.objects.create(
                    platform=self.platform,
                    platform_user_id=clean_to_number,
                    name=real_phone_number if real_phone_number else clean_to_number,
                    phone=real_phone_number if real_phone_number else clean_to_number
                )
            
            # Buscar conversación activa para este contacto
            conversation = Conversation.objects.filter(
                contact=contact,
                status='active'
            ).first()
            
            if not conversation:
                # Crear una nueva conversación si no existe CON EL DEPARTAMENTO CORRECTO
                conversation = Conversation.objects.create(
                    contact=contact,
                    status='active',
                    funnel_type=department,  # ← ASIGNAR DEPARTAMENTO CORRECTO
                    needs_response=True,
                    is_answered=False
                )
                print(f"✅ Conversación creada automáticamente: {conversation.id} para contacto {contact.id} en departamento {department}")
                
                ActivityLog.objects.create(
                    user=None,
                    conversation=conversation,
                    action='auto_conversation_created',
                    description=f'Conversación creada automáticamente por respuesta externa de {contact.display_name} en {department}'
                )
            else:
                # Si la conversación existe, actualizar el departamento si es necesario
                if conversation.funnel_type != department:
                    print(f"🔄 Actualizando departamento de conversación {conversation.id}: {conversation.funnel_type} → {department}")
                    conversation.funnel_type = department
                    conversation.save()
            
            # **AQUÍ ES DONDE OCURRE LA MAGIA** 🎯
            # Crear el mensaje saliente en la base de datos con soporte de media
            media_url = webhook_data.get('media_url')
            
            # Usar contenido real si está disponible, solo usar fallback para mensajes de media sin contenido
            final_content = content
            if not content:
                if message_type == 'text':
                    final_content = '⚠️ Mensaje enviado desde WhatsApp (contenido no disponible)'
                else:
                    final_content = self._get_media_fallback_content(message_type)
            
            # Si message_id está vacío, generar uno único (por seguridad)
            if not message_id:
                import uuid
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                message_id = f"agent_{timestamp}_{str(uuid.uuid4())[:8]}"
            
            Message.objects.create(
                conversation=conversation,
                platform_message_id=message_id,
                sender_type='agent',  # Mensaje enviado por el agente (desde WhatsApp externo)
                message_type=message_type,
                content=final_content,
                media_url=media_url
            )
            
            # **ACTUALIZAR EL ESTADO DE LA CONVERSACIÓN** ✅
            conversation.last_message_at = timezone.now()
            conversation.last_response_at = timezone.now()
            conversation.is_answered = True  # ← ESTE ES EL CAMBIO CRUCIAL
            conversation.needs_response = False  # ← QUITAR "SIN RESPONDER" CUANDO SE RESPONDE DESDE WHATSAPP
            
            # Si es la primera respuesta, registrarla
            if not conversation.first_response_at:
                conversation.first_response_at = timezone.now()
            
            conversation.save()
            
            # Respuesta externa detectada y conversación marcada como respondida
            
            # Registrar actividad
            ActivityLog.objects.create(
                user=None,  # No hay usuario específico ya que se envió desde WhatsApp externo
                conversation=conversation,
                action='external_whatsapp_response',
                description=f'Respuesta enviada desde WhatsApp externo a {contact.name}: {content[:100]}'
            )
            
            return {'success': True, 'conversation_id': conversation.id}
            
        except Exception as e:
            # Log error silently or use proper logging
            return {'success': False, 'error': str(e)}
    
    def verify_webhook(self, mode, token, challenge):
        """Para compatibilidad con el código existente - no necesario en Baileys"""
        # Baileys no usa verificación de webhook como Facebook
        return challenge if challenge else None

    def _get_media_fallback_content(self, message_type):
        """Devuelve contenido por defecto para mensajes de media"""
        fallback_map = {
            'image': '📷 Imagen enviada',
            'video': '🎥 Video enviado',
            'audio': '🎵 Audio enviado',
            'document': '📄 Documento enviado',
            'location': '📍 Ubicación compartida',
            'sticker': '😀 Sticker enviado'
        }
        return fallback_map.get(message_type, 'Mensaje enviado')
    
    def _normalize_phone_for_bridge(self, value: str) -> str:
        """
        Normalizar números de teléfono INTERNACIONALES para el bridge
        ACEPTA cualquier número internacional válido
        """
        from ..utils.international_phone import limpiar_numero, formatear_numero_internacional, obtener_numero_para_whatsapp
        
        try:
            print(f"🌍 Normalizando número internacional: {value}")
            v = str(value).strip()
            
            # Intentar formatear como número internacional
            formatted = formatear_numero_internacional(v)
            if formatted:
                clean_digits = obtener_numero_para_whatsapp(formatted)
                print(f"✅ Número internacional válido: {formatted} -> {clean_digits}")
                return clean_digits
            
            # RETROCOMPATIBILIDAD: Si es un celular colombiano de 10 dígitos
            digits = limpiar_numero(v)
            if len(digits) == 10 and digits.startswith('3'):
                colombia_number = f"57{digits}"
                formatted = formatear_numero_internacional(colombia_number)
                if formatted:
                    print(f"✅ Número colombiano (retrocompatibilidad): {formatted}")
                    return colombia_number
            
            # Si no se puede formatear, intentar usar directamente si parece válido
            if len(digits) >= 10 and len(digits) <= 15:
                print(f"⚠️  Número no reconocido, usando formato directo: {digits}")
                return digits
                
            raise ValueError(f"Número no válido o muy corto: {v}")
            
        except Exception as e:
            print(f"❌ Error normalizando número {value}: {e}")
            raise e

    def _get_or_create_unified_contact(self, clean_from_number, real_phone_number):
        """
        SISTEMA UNIFICADO INTERNACIONAL: Manejo de contactos de cualquier país
        NO más WA-IDs, NO más duplicaciones
        """
        from ..utils.international_phone import obtener_info_pais
        
        # REGLA 1: Solo aceptar números reales formateados internacionales
        if not real_phone_number or not real_phone_number.startswith('+'):
            print(f"❌ RECHAZADO: No hay número real válido para {clean_from_number}")
            raise ValueError(f"Número no válido: {clean_from_number}")
        
        # Obtener información del país
        country_info = obtener_info_pais(real_phone_number)
        country_name = country_info['name'] if country_info else 'Desconocido'
        
        # REGLA 2: Buscar ÚNICAMENTE por número real
        existing_contact = Contact.objects.filter(
            platform=self.platform,
            phone=real_phone_number
        ).first()
        
        if existing_contact:
            print(f"✅ Contacto {country_name} existente encontrado: ID={existing_contact.id}, phone={existing_contact.phone}")
            # Asegurar que platform_user_id sea consistente
            if existing_contact.platform_user_id != clean_from_number:
                existing_contact.platform_user_id = clean_from_number
                existing_contact.save()
            return existing_contact
        
        # REGLA 3: Crear nuevo contacto internacional
        contact = Contact.objects.create(
            platform=self.platform,
            platform_user_id=clean_from_number,  # JID limpio sin @
            name=real_phone_number,  # Usar número formateado como nombre inicial
            phone=real_phone_number,
            country=country_name  # Agregar país detectado
        )
        
        print(f"✅ Nuevo contacto {country_name} creado: ID={contact.id}, phone={contact.phone}")
        return contact
    
    def _merge_duplicate_conversations(self, main_contact):
        """Fusiona conversaciones duplicadas del mismo contacto real"""
        
        # Buscar otras conversaciones del mismo número real
        if main_contact.phone:
            duplicate_contacts = Contact.objects.filter(
                platform=self.platform,
                phone=main_contact.phone
            ).exclude(id=main_contact.id)
            
            for duplicate_contact in duplicate_contacts:
                # Migrar conversaciones del contacto duplicado al principal
                duplicate_conversations = Conversation.objects.filter(contact=duplicate_contact)
                
                for duplicate_conv in duplicate_conversations:
                    # Buscar conversación existente del contacto principal
                    main_conversation = Conversation.objects.filter(
                        contact=main_contact,
                        status='active'
                    ).first()
                    
                    if main_conversation:
                        # Migrar mensajes de la conversación duplicada a la principal
                        duplicate_conv.message_set.update(conversation=main_conversation)
                        
                        # Actualizar timestamps si es necesario
                        if duplicate_conv.last_message_at > main_conversation.last_message_at:
                            main_conversation.last_message_at = duplicate_conv.last_message_at
                            main_conversation.save()
                        
                        # Eliminar conversación duplicada
                        duplicate_conv.delete()
                    else:
                        # Si no hay conversación principal, transferir la propiedad
                        duplicate_conv.contact = main_contact
                        duplicate_conv.save()
                
                # Eliminar contacto duplicado
                duplicate_contact.delete()

