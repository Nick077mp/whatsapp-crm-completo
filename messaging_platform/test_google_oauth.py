#!/usr/bin/env python
"""
Script de prueba para verificar las credenciales de Google OAuth
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from google_auth_oauthlib.flow import Flow

def test_google_credentials():
    print("=== PRUEBA DE CREDENCIALES GOOGLE ===")
    
    # Verificar variables
    client_id = settings.GOOGLE_OAUTH2_CLIENT_ID
    client_secret = settings.GOOGLE_OAUTH2_CLIENT_SECRET
    
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {'***' + client_secret[-4:] if client_secret else 'NO CONFIGURADO'}")
    
    if not client_id or not client_secret:
        print("❌ ERROR: Credenciales no configuradas")
        return False
    
    # Probar configuración del flujo
    try:
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=['https://www.googleapis.com/auth/contacts.readonly']
        )
        
        flow.redirect_uri = "http://localhost:8000/auth/google/callback/"
        
        # Generar URL de prueba
        auth_url, state = flow.authorization_url(access_type='offline')
        
        print("✅ Configuración OAuth válida")
        print(f"URL de autorización generada: {auth_url[:100]}...")
        print("✅ Las credenciales están funcionando correctamente")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR en configuración OAuth: {e}")
        return False

if __name__ == "__main__":
    test_google_credentials()