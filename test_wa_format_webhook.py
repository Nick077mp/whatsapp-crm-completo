#!/usr/bin/env python3

"""
Script para simular un webhook saliente con formato real WA-
"""

import requests
import json

def test_outgoing_webhook_with_wa_format():
    """Simula un webhook saliente con el formato WA- real"""
    
    # URL del webhook
    url = "http://localhost:8000/webhooks/whatsapp-outgoing/"
    
    # Datos del webhook con formato real WA-
    webhook_data = {
        "to": "WA-2699-1357-9118-670",  # Formato real que estás viendo
        "message_id": "msg_test_wa_format_123",
        "timestamp": 1698624136,
        "type": "text", 
        "content": "Respuesta de prueba desde celular - formato WA",
        "from_me": True,
        "media_url": None
    }
    
    print("🚀 Simulando webhook saliente con formato WA-...")
    print(f"📊 Datos: {json.dumps(webhook_data, indent=2)}")
    
    try:
        response = requests.post(url, json=webhook_data, timeout=10)
        print(f"📡 Respuesta del servidor: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Éxito: {result}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")

def test_outgoing_webhook_with_phone():
    """Simula un webhook saliente con número de teléfono normal"""
    
    url = "http://localhost:8000/webhooks/whatsapp-outgoing/"
    
    webhook_data = {
        "to": "+57 300 734 1192",  # Formato de número normal
        "message_id": "msg_test_phone_format_456", 
        "timestamp": 1698624136,
        "type": "text",
        "content": "Respuesta de prueba desde celular - formato teléfono",
        "from_me": True,
        "media_url": None
    }
    
    print("\n🚀 Simulando webhook saliente con formato teléfono...")
    print(f"📊 Datos: {json.dumps(webhook_data, indent=2)}")
    
    try:
        response = requests.post(url, json=webhook_data, timeout=10)
        print(f"📡 Respuesta del servidor: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Éxito: {result}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")

if __name__ == "__main__":
    print("🧪 Pruebas de webhook saliente con formatos reales")
    test_outgoing_webhook_with_wa_format()
    test_outgoing_webhook_with_phone()
    print("\n✅ Pruebas completadas")