from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
from django.utils import timezone
import re

from ..models import GoogleContactsAuth


class GoogleContactsService:
    """Servicio para interactuar con Google Contacts API"""
    
    def __init__(self, user):
        self.user = user
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Inicializar el servicio de Google Contacts"""
        try:
            auth = GoogleContactsAuth.objects.get(user=self.user)
            
            # Verificar si el token ha expirado
            if auth.is_token_expired():
                # Aquí se podría implementar la renovación automática del token
                raise Exception("Token de Google Contacts expirado. Por favor, vuelve a autorizar.")
            
            # Crear las credenciales
            credentials = Credentials(
                token=auth.access_token,
                refresh_token=auth.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_OAUTH2_CLIENT_ID,
                client_secret=settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                scopes=auth.scopes
            )
            
            # Crear el servicio
            self.service = build('people', 'v1', credentials=credentials)
            
        except GoogleContactsAuth.DoesNotExist:
            raise Exception("No hay autorización de Google Contacts para este usuario")
        except Exception as e:
            raise Exception(f"Error al inicializar Google Contacts: {str(e)}")
    
    def normalize_phone_number(self, phone):
        """Normalizar número de teléfono para búsqueda"""
        if not phone:
            return None
            
        # Remover todos los caracteres que no sean dígitos
        clean_phone = re.sub(r'[^\d]', '', phone)
        
        # Si el número no tiene código de país y es colombiano (10 dígitos empezando con 3)
        if len(clean_phone) == 10 and clean_phone.startswith('3'):
            clean_phone = '57' + clean_phone  # Agregar código de Colombia
        
        # Si el número empieza con 57 pero no tiene el prefijo +
        if clean_phone.startswith('57') and len(clean_phone) == 12:
            clean_phone = '+' + clean_phone
        
        return clean_phone
    
    def search_contact_by_phone(self, phone_number):
        """Buscar un contacto por número de teléfono"""
        if not self.service:
            return None
        
        normalized_phone = self.normalize_phone_number(phone_number)
        if not normalized_phone:
            return None
        
        try:
            # Buscar en todos los contactos
            results = self.service.people().connections().list(
                resourceName='people/me',
                pageSize=1000,  # Máximo permitido por la API
                personFields='names,phoneNumbers'
            ).execute()
            
            connections = results.get('connections', [])
            
            # Buscar coincidencia por número
            for person in connections:
                phone_numbers = person.get('phoneNumbers', [])
                
                for phone_data in phone_numbers:
                    contact_phone = phone_data.get('value', '')
                    normalized_contact_phone = self.normalize_phone_number(contact_phone)
                    
                    # Comparar números normalizados
                    if normalized_contact_phone and (
                        normalized_phone == normalized_contact_phone or
                        normalized_phone.replace('+', '') == normalized_contact_phone.replace('+', '') or
                        normalized_phone.endswith(contact_phone.replace('+', '').replace(' ', '').replace('-', ''))
                    ):
                        # Encontramos una coincidencia
                        names = person.get('names', [])
                        if names:
                            display_name = names[0].get('displayName', '')
                            return {
                                'id': person.get('resourceName', ''),
                                'name': display_name,
                                'phone': contact_phone
                            }
            
            return None
            
        except HttpError as e:
            print(f"Error de Google API: {e}")
            return None
        except Exception as e:
            print(f"Error buscando contacto: {e}")
            return None
    
    def get_contact_by_id(self, contact_id):
        """Obtener un contacto específico por ID"""
        if not self.service:
            return None
        
        try:
            person = self.service.people().get(
                resourceName=contact_id,
                personFields='names,phoneNumbers,emailAddresses'
            ).execute()
            
            # Extraer información relevante
            names = person.get('names', [])
            phone_numbers = person.get('phoneNumbers', [])
            emails = person.get('emailAddresses', [])
            
            result = {
                'id': person.get('resourceName', ''),
                'name': names[0].get('displayName', '') if names else '',
                'phones': [p.get('value', '') for p in phone_numbers],
                'emails': [e.get('value', '') for e in emails]
            }
            
            return result
            
        except HttpError as e:
            print(f"Error obteniendo contacto: {e}")
            return None
    
    def search_contacts_by_query(self, query, limit=10):
        """Buscar contactos por texto libre"""
        if not self.service or not query:
            return []
        
        try:
            results = self.service.people().connections().list(
                resourceName='people/me',
                pageSize=limit,
                personFields='names,phoneNumbers'
            ).execute()
            
            connections = results.get('connections', [])
            matching_contacts = []
            
            query_lower = query.lower()
            
            for person in connections:
                names = person.get('names', [])
                
                # Buscar en nombres
                for name_data in names:
                    display_name = name_data.get('displayName', '')
                    if query_lower in display_name.lower():
                        phone_numbers = person.get('phoneNumbers', [])
                        phone = phone_numbers[0].get('value', '') if phone_numbers else ''
                        
                        matching_contacts.append({
                            'id': person.get('resourceName', ''),
                            'name': display_name,
                            'phone': phone
                        })
                        break
            
            return matching_contacts
            
        except HttpError as e:
            print(f"Error buscando contactos: {e}")
            return []
    
    def refresh_credentials(self):
        """Renovar las credenciales OAuth2"""
        try:
            auth = GoogleContactsAuth.objects.get(user=self.user)
            
            if not auth.refresh_token:
                raise Exception("No hay refresh token disponible")
            
            # Crear credenciales con refresh token
            credentials = Credentials(
                token=auth.access_token,
                refresh_token=auth.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_OAUTH2_CLIENT_ID,
                client_secret=settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                scopes=auth.scopes
            )
            
            # Forzar renovación del token
            credentials.refresh(Request())
            
            # Actualizar en base de datos
            auth.access_token = credentials.token
            auth.token_expires_at = credentials.expiry
            auth.save()
            
            # Reinicializar el servicio
            self._initialize_service()
            
            return True
            
        except Exception as e:
            print(f"Error renovando credenciales: {e}")
            return False
