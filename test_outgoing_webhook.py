#!/usr/bin/env python3
"""
Script de prueba para simular un webhook de mensaje saliente
Esto simula lo que ocurre cuando se responde desde WhatsApp directamente
"""

import requests
import json
import time

# Configuración
DJANGO_URL = "http://localhost:8000"
WEBHOOK_URL = f"{DJANGO_URL}/webhooks/whatsapp-outgoing/"

# Datos de prueba - simula un mensaje saliente enviado desde WhatsApp
test_webhook_data = {
    "to": "+57 300 734 1192",  # Número del cliente al que respondimos
    "message_id": f"test_outgoing_{int(time.time())}",
    "timestamp": int(time.time()),
    "type": "text",
    "content": "Hola, sí estoy disponible. ¿En qué puedo ayudarte?",
    "from_me": True  # Indicador importante
}

def test_outgoing_webhook():
    """Prueba el webhook de mensajes salientes"""
    print("🧪 Probando webhook de mensajes salientes...")
    print(f"📡 Enviando a: {WEBHOOK_URL}")
    print(f"📝 Datos: {json.dumps(test_webhook_data, indent=2)}")
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=test_webhook_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ ¡Webhook procesado exitosamente!")
        else:
            print("❌ Error en el webhook")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    test_outgoing_webhook()