#!/usr/bin/env python3
"""
Script para probar la API de recuperación directamente
"""
import os
import sys
import json
import requests

def test_recovery_api():
    """Probar la API de casos de recuperación"""
    
    # URL base del servidor Django
    base_url = "http://localhost:8000"
    
    # Datos de prueba
    test_data = {
        "conversation_id": 1,  # Asumiendo que existe una conversación con ID 1
        "reason": "price_objection",
        "reason_notes": "Cliente considera que el precio es muy alto",
        "recovery_strategy": "Ofrecer descuento del 15% y plan de pagos",
        "target_recovery_date": "2025-11-15"
    }
    
    print("🧪 Probando API de casos de recuperación...")
    print(f"📡 URL: {base_url}/api/recovery-cases/create/")
    print(f"📋 Datos: {json.dumps(test_data, indent=2)}")
    
    try:
        # Primero, intentar obtener la página de login para conseguir el token CSRF
        session = requests.Session()
        
        # Obtener token CSRF desde la página de login
        login_page = session.get(f"{base_url}/login/")
        print(f"📊 Status login page: {login_page.status_code}")
        
        if login_page.status_code == 200:
            # Extraer token CSRF (esto es una implementación simplificada)
            csrf_token = None
            for cookie in session.cookies:
                if cookie.name == 'csrftoken':
                    csrf_token = cookie.value
                    break
            
            print(f"🔐 CSRF Token: {'Encontrado' if csrf_token else 'No encontrado'}")
            
            if csrf_token:
                # Intentar hacer login (necesitarás las credenciales correctas)
                print("⚠️  Para continuar la prueba, necesitas hacer login manualmente")
                print("   o modificar este script con credenciales válidas")
        
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")

if __name__ == "__main__":
    test_recovery_api()