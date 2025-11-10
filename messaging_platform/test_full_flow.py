#!/usr/bin/env python
"""
Script para simular el flujo completo del navegador
"""
import requests
from bs4 import BeautifulSoup
import re

def test_full_flow():
    # Crear sesión (simula un navegador)
    session = requests.Session()
    
    print("=== 1. Obteniendo página de login ===")
    login_page = session.get('http://localhost:8000/login/')
    print(f"Status: {login_page.status_code}")
    
    # Extraer CSRF token
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
    print(f"CSRF token: {csrf_token[:20]}...")
    
    print("\\n=== 2. Intentando login ===")
    login_data = {
        'csrfmiddlewaretoken': csrf_token,
        'email': 'admin@admin.com',  # Usuario existente
        'password': 'newadmin123'  # Nueva contraseña
    }
    
    login_response = session.post('http://localhost:8000/login/', data=login_data, allow_redirects=False)
    print(f"Login status: {login_response.status_code}")
    print(f"Redirect to: {login_response.headers.get('Location', 'No redirect')}")
    
    print("\\n=== 3. Verificando dashboard ===")
    dashboard = session.get('http://localhost:8000/dashboard/')
    print(f"Dashboard status: {dashboard.status_code}")
    
    if dashboard.status_code == 200:
        if 'Dashboard' in dashboard.text:
            print("✅ Login exitoso - Dashboard cargado")
        else:
            print("❌ Redirigido al login - credenciales incorrectas")
            return
    
    print("\\n=== 4. Probando API de autenticación ===")
    auth_test = session.get('http://localhost:8000/api/test-auth/')
    print(f"Auth test status: {auth_test.status_code}")
    print(f"Auth response: {auth_test.text}")
    
    print("\\n=== 5. Probando Google Contacts status ===")
    google_status = session.get('http://localhost:8000/api/google-contacts/status/')
    print(f"Google status: {google_status.status_code}")
    print(f"Google response: {google_status.text}")
    
    print("\\n=== 6. Probando URL de Google Auth ===")
    google_auth = session.get('http://localhost:8000/auth/google/', allow_redirects=False)
    print(f"Google auth status: {google_auth.status_code}")
    
    if google_auth.status_code == 302:
        location = google_auth.headers.get('Location', '')
        if 'accounts.google.com' in location:
            print("✅ Redirige correctamente a Google OAuth")
            print(f"URL: {location[:100]}...")
        else:
            print(f"❌ Redirige incorrectamente a: {location}")
    else:
        print(f"❌ No redirige (status: {google_auth.status_code})")

if __name__ == "__main__":
    test_full_flow()