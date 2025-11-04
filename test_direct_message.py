#!/usr/bin/env python3
"""
Script de prueba para enviar mensaje directamente al bridge
"""
import requests
import json

def test_direct_bridge_message():
    """Envía un mensaje directamente al bridge de WhatsApp"""
    bridge_url = "http://localhost:3000"
    
    print("🔍 Probando envío directo al bridge...")
    
    # Datos del mensaje
    payload = {
        'to': '573000000000',  # Número de prueba
        'message': 'Mensaje de prueba directo'
    }
    
    try:
        print(f"📡 Enviando a: {bridge_url}/send-message")
        print(f"📝 Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{bridge_url}/send-message", 
            json=payload, 
            timeout=10
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ ¡Mensaje enviado exitosamente!")
                return True
            else:
                print(f"❌ Error del bridge: {result.get('error')}")
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al bridge - ¿Está ejecutándose?")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    return False

if __name__ == "__main__":
    test_direct_bridge_message()