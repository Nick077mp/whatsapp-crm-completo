#!/usr/bin/env python
"""
Script para probar autenticación como un navegador
"""
import requests

# Crear una sesión (simula un navegador)
session = requests.Session()

# Primero, obtener el token CSRF
login_page = session.get('http://localhost:8000/login/')
print(f"Login page status: {login_page.status_code}")

# Extraer CSRF token (simplificado)
csrf_start = login_page.text.find('name="csrfmiddlewaretoken" value="') + 34
csrf_end = login_page.text.find('"', csrf_start)
csrf_token = login_page.text[csrf_start:csrf_end]
print(f"CSRF token: {csrf_token}")

# Intentar login (necesitarás cambiar estas credenciales)
login_data = {
    'csrfmiddlewaretoken': csrf_token,
    'email': 'admin@example.com',  # Cambia por tu email
    'password': 'admin'  # Cambia por tu contraseña
}

login_response = session.post('http://localhost:8000/login/', data=login_data)
print(f"Login response status: {login_response.status_code}")
print(f"Login response URL: {login_response.url}")

# Probar acceso a Google Auth
google_auth = session.get('http://localhost:8000/auth/google/', allow_redirects=False)
print(f"Google auth status: {google_auth.status_code}")
if google_auth.status_code == 302:
    print(f"Redirect to: {google_auth.headers.get('Location')}")
    
# Probar API de test
test_auth = session.get('http://localhost:8000/api/test-auth/')
print(f"Test auth status: {test_auth.status_code}")
print(f"Test auth response: {test_auth.text}")