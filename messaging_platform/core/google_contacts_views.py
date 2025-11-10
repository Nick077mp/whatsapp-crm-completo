from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import os
import requests
from datetime import datetime, timedelta

# Para desarrollo local - permitir HTTP
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from .models import GoogleContactsAuth, Contact
from .services.google_contacts_service import GoogleContactsService


@login_required
def google_auth_start(request):
    """Iniciar el proceso de autenticación con Google"""
    
    print(f"🔍 DEBUG AUTH START - User: {request.user.username}")
    print(f"🔍 DEBUG AUTH START - CLIENT_ID exists: {hasattr(settings, 'GOOGLE_OAUTH2_CLIENT_ID')}")
    print(f"🔍 DEBUG AUTH START - CLIENT_SECRET exists: {hasattr(settings, 'GOOGLE_OAUTH2_CLIENT_SECRET')}")
    print(f"🔍 DEBUG AUTH START - SCOPES exist: {hasattr(settings, 'GOOGLE_OAUTH2_SCOPES')}")
    
    # Crear credenciales temporales para el flujo OAuth
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }
    
    # Verificar que tenemos las credenciales
    if not settings.GOOGLE_OAUTH2_CLIENT_ID or not settings.GOOGLE_OAUTH2_CLIENT_SECRET:
        print("❌ ERROR: Credenciales de Google OAuth no configuradas")
        messages.error(request, 'Credenciales de Google OAuth no configuradas')
        return redirect('dashboard')
    
    try:
        # Configurar el flujo OAuth
        flow = Flow.from_client_config(
            client_config,
            scopes=settings.GOOGLE_OAUTH2_SCOPES
        )
        
        # Determinar URI de redirección basado en el host de la request
        host = request.get_host()
        redirect_uri = f"http://{host}/auth/google/callback/"
        
        flow.redirect_uri = redirect_uri
        
        # Generar URL de autorización
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        # Guardar el estado en la sesión
        request.session['google_auth_state'] = state
        request.session['google_auth_redirect_uri'] = redirect_uri
        
        return redirect(authorization_url)
        
    except Exception as e:
        messages.error(request, f'Error configurando OAuth: {str(e)}')
        return redirect('dashboard')


@login_required
def google_auth_callback(request):
    """Callback después de la autorización de Google"""
    
    print(f"🔍 DEBUG CALLBACK - User authenticated: {request.user.is_authenticated}")
    print(f"🔍 DEBUG CALLBACK - User: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    print(f"🔍 DEBUG CALLBACK - GET params: {request.GET}")
    
    # Verificar si hay error de autorización
    if request.GET.get('error'):
        error = request.GET.get('error')
        print(f"❌ Error de OAuth: {error}")
        messages.error(request, f'Error de autorización de Google: {error}')
        return redirect('dashboard')
    
    # Verificar el estado
    state = request.session.get('google_auth_state')
    redirect_uri = request.session.get('google_auth_redirect_uri')
    
    print(f"🔍 DEBUG CALLBACK - Session state: {state}")
    print(f"🔍 DEBUG CALLBACK - Request state: {request.GET.get('state')}")
    print(f"🔍 DEBUG CALLBACK - Redirect URI: {redirect_uri}")
    
    if not state or request.GET.get('state') != state:
        print("❌ Error de estado en callback")
        messages.error(request, 'Error de seguridad en la autenticación con Google')
        return redirect('dashboard')
    
    # Configurar el flujo OAuth con los mismos parámetros
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=settings.GOOGLE_OAUTH2_SCOPES,
        state=state
    )
    
    flow.redirect_uri = redirect_uri
    
    try:
        print("🔍 DEBUG CALLBACK - Intercambiando código por tokens...")
        
        # Usar approach alternativo para evitar el problema de scope
        import requests
        from google.oauth2.credentials import Credentials
        
        # Obtener el código de la URL
        code = request.GET.get('code')
        if not code:
            raise Exception("No se recibió código de autorización")
        
        # Intercambiar código por token manualmente
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': settings.GOOGLE_OAUTH2_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH2_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }
        
        print("🔍 DEBUG CALLBACK - Haciendo request manual para tokens...")
        response = requests.post(token_url, data=data)
        
        if response.status_code != 200:
            raise Exception(f"Error obteniendo tokens: {response.text}")
        
        token_data = response.json()
        print(f"🔍 DEBUG CALLBACK - Token data recibida: {list(token_data.keys())}")
        
        # Crear objeto credentials manualmente
        from datetime import datetime, timedelta
        import json
        
        expires_at = None
        if 'expires_in' in token_data:
            expires_at = datetime.utcnow() + timedelta(seconds=int(token_data['expires_in']))
        
        print(f"🔍 DEBUG CALLBACK - Tokens obtenidos exitosamente")
        print(f"🔍 DEBUG CALLBACK - Access token: {token_data.get('access_token', 'N/A')[:20]}...")
        print(f"🔍 DEBUG CALLBACK - Refresh token: {'Sí' if token_data.get('refresh_token') else 'No'}")
        print(f"🔍 DEBUG CALLBACK - Expires at: {expires_at}")
        print(f"🔍 DEBUG CALLBACK - Scope: {token_data.get('scope', 'N/A')}")
        
        # Guardar o actualizar los tokens en la base de datos
        auth_obj, created = GoogleContactsAuth.objects.update_or_create(
            user=request.user,
            defaults={
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'token_expires_at': expires_at,
                'scopes': token_data.get('scope', '').split() if token_data.get('scope') else settings.GOOGLE_OAUTH2_SCOPES
            }
        )
        
        print(f"🔍 DEBUG CALLBACK - Auth object {'created' if created else 'updated'}: {auth_obj.id}")
        
        # Limpiar la sesión
        if 'google_auth_state' in request.session:
            del request.session['google_auth_state']
        if 'google_auth_redirect_uri' in request.session:
            del request.session['google_auth_redirect_uri']
        
        if created:
            messages.success(request, 'Google Contacts se ha conectado exitosamente')
            print("✅ Google Contacts conectado exitosamente")
        else:
            messages.success(request, 'Google Contacts se ha actualizado exitosamente')
            print("✅ Google Contacts actualizado exitosamente")
            
    except Exception as e:
        print(f"❌ ERROR en callback: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error al conectar con Google Contacts: {str(e)}')
    
    return redirect('dashboard')


@login_required
def google_contacts_status(request):
    """Verificar el estado de la conexión con Google Contacts"""
    
    try:
        auth = GoogleContactsAuth.objects.get(user=request.user)
        
        # Verificar si el token es válido
        is_connected = not auth.is_token_expired()
        
        return JsonResponse({
            'connected': is_connected,
            'expires_at': auth.token_expires_at.isoformat() if auth.token_expires_at else None,
            'scopes': auth.scopes
        })
        
    except GoogleContactsAuth.DoesNotExist:
        return JsonResponse({
            'connected': False,
            'error': 'No hay conexión con Google Contacts'
        })


def google_auth_callback_alt(request):
    """Callback alternativo sin requerir login (para debug)"""
    
    print(f"🔍 DEBUG CALLBACK ALT - User authenticated: {request.user.is_authenticated}")
    print(f"🔍 DEBUG CALLBACK ALT - Session keys: {list(request.session.keys())}")
    print(f"🔍 DEBUG CALLBACK ALT - GET params: {dict(request.GET)}")
    
    # Si no está autenticado, intentar redireccionar al login
    if not request.user.is_authenticated:
        print("❌ Usuario no autenticado en callback")
        messages.error(request, 'Sesión perdida durante OAuth. Por favor, inicia sesión nuevamente.')
        return redirect('login')
    
    # Resto del proceso de callback...
    return google_auth_callback(request)


# Mantener la función original con login_required
    """Vista de prueba para verificar el estado de autenticación"""
    return JsonResponse({
        'authenticated': request.user.is_authenticated,
        'user_id': request.user.id if request.user.is_authenticated else None,
        'username': request.user.username if request.user.is_authenticated else None,
        'session_key': request.session.session_key,
        'is_staff': request.user.is_staff if request.user.is_authenticated else False
    })
@login_required
def search_google_contact(request):
    """Buscar un contacto en Google Contacts por número de teléfono"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Solo se permite método POST'}, status=405)
    
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        
        if not phone_number:
            return JsonResponse({'error': 'Número de teléfono requerido'}, status=400)
        
        # Obtener el servicio de Google Contacts
        service = GoogleContactsService(request.user)
        
        # Buscar el contacto
        contact_info = service.search_contact_by_phone(phone_number)
        
        if contact_info:
            return JsonResponse({
                'found': True,
                'name': contact_info.get('name'),
                'google_id': contact_info.get('id'),
                'phone': contact_info.get('phone')
            })
        else:
            return JsonResponse({
                'found': False,
                'message': 'Contacto no encontrado en Google Contacts'
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def sync_contact_with_google(request, contact_id):
    """Sincronizar un contacto específico con Google Contacts"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Solo se permite método POST'}, status=405)
    
    try:
        contact = Contact.objects.get(id=contact_id)
        
        # Obtener el servicio de Google Contacts
        service = GoogleContactsService(request.user)
        
        # Intentar encontrar el contacto en Google
        phone_to_search = contact.phone or contact.platform_user_id
        if phone_to_search:
            contact_info = service.search_contact_by_phone(phone_to_search)
            
            if contact_info:
                # Actualizar el contacto con información de Google
                contact.google_contact_name = contact_info.get('name')
                contact.google_contact_id = contact_info.get('id')
                contact.google_last_sync = timezone.now()
                contact.save()
                
                return JsonResponse({
                    'success': True,
                    'google_name': contact.google_contact_name,
                    'message': 'Contacto sincronizado exitosamente'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Contacto no encontrado en Google Contacts'
                })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No hay número de teléfono para buscar'
            })
            
    except Contact.DoesNotExist:
        return JsonResponse({'error': 'Contacto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required  
def disconnect_google_contacts(request):
    """Desconectar Google Contacts"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Solo se permite método POST'}, status=405)
    
    try:
        auth = GoogleContactsAuth.objects.get(user=request.user)
        auth.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Google Contacts desconectado exitosamente'
        })
        
    except GoogleContactsAuth.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'No hay conexión activa con Google Contacts'
        })


def test_auth_status(request):
    """Vista de prueba para verificar el estado de autenticación"""
    return JsonResponse({
        'user': str(request.user),
        'authenticated': request.user.is_authenticated,
        'google_auths': list(GoogleContactsAuth.objects.all().values()),
        'settings': {
            'client_id': settings.GOOGLE_OAUTH2_CLIENT_ID[:20] + '...' if settings.GOOGLE_OAUTH2_CLIENT_ID else 'NOT SET',
            'client_secret': 'SET' if settings.GOOGLE_OAUTH2_CLIENT_SECRET else 'NOT SET',
            'insecure_transport': os.environ.get('OAUTHLIB_INSECURE_TRANSPORT', 'NOT SET')
        }
    })


def debug_oauth_callback(request):
    """Función de debug simplificada para OAuth"""
    print(f"🔍 DEBUG SIMPLE CALLBACK")
    print(f"🔍 GET params: {dict(request.GET)}")
    print(f"🔍 User: {request.user}")
    
    # Si hay código, intentar crear un registro manual
    if 'code' in request.GET:
        try:
            # Crear registro manual de prueba
            auth, created = GoogleContactsAuth.objects.get_or_create(
                user=request.user,
                defaults={
                    'access_token': f'test_token_{request.GET.get("code")[:10]}',
                    'refresh_token': 'test_refresh',
                    'token_expires_at': timezone.now() + timezone.timedelta(hours=1),
                }
            )
            print(f"✅ Registro de prueba creado: {auth.id}")
            messages.success(request, 'Conexión de prueba establecida')
        except Exception as e:
            print(f"❌ Error creando registro: {e}")
            messages.error(request, f'Error: {e}')
    
    return redirect('dashboard')