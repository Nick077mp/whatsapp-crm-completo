# 🔧 Configuración del Bridge de Baileys para Detección de Respuestas Externas

## 📋 **Problema Identificado**

El sistema **ya está funcionando correctamente** para procesar webhooks salientes. La prueba mostró:

✅ **Webhook procesado exitosamente**: `WA-2699-1357-9118-670`
✅ **Estado actualizado**: `needs_response: False`, `is_answered: True`
✅ **Mensaje guardado**: "Respuesta de prueba desde celular - formato WA"

**El problema real es**: El bridge de Baileys no está configurado para enviar webhooks automáticamente cuando respondes desde el celular.

---

## 🛠️ **Solución: Configurar Bridge de Baileys**

### **1. Webhooks que debe enviar el bridge:**

#### **Mensajes Entrantes (ya funciona):**
```javascript
// Cuando llega un mensaje del cliente
const incomingWebhook = {
    from: "WA-2699-1357-9118-670",     // ID del contacto
    message_id: "msg_123",
    timestamp: Date.now(),
    type: "text",                      // text, image, video, audio, document
    content: "Hola, necesito ayuda",
    media_url: "https://..." // Si tiene media
};

// Enviar a Django
axios.post('http://localhost:8000/webhooks/whatsapp/', incomingWebhook);
```

#### **Mensajes Salientes (NECESARIO CONFIGURAR):**
```javascript
// Cuando TÚ respondes desde WhatsApp/celular
const outgoingWebhook = {
    to: "WA-2699-1357-9118-670",       // ID del contacto
    message_id: "msg_456", 
    timestamp: Date.now(),
    type: "text",                      // text, image, video, audio, document
    content: "Sí, te ayudo ahora",     // Tu respuesta
    from_me: true,                     // IMPORTANTE: indica que lo enviaste tú
    media_url: "https://..." // Si enviaste media
};

// Enviar a Django (ESTE ES EL QUE FALTA)
axios.post('http://localhost:8000/webhooks/whatsapp-outgoing/', outgoingWebhook);
```

---

## 📝 **Configuración Requerida en el Bridge**

### **Ejemplo de configuración en Node.js (Baileys):**

```javascript
const { makeWASocket, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const axios = require('axios');

// URLs de webhooks
const DJANGO_WEBHOOK_INCOMING = 'http://localhost:8000/webhooks/whatsapp/';
const DJANGO_WEBHOOK_OUTGOING = 'http://localhost:8000/webhooks/whatsapp-outgoing/';

async function startWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('./auth_info');
    
    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: true,
    });

    // Guardar credenciales
    sock.ev.on('creds.update', saveCreds);

    // MENSAJES ENTRANTES (ya existe)
    sock.ev.on('messages.upsert', async (m) => {
        const message = m.messages[0];
        if (message.key.fromMe) return; // Ignorar nuestros mensajes aquí
        
        const webhookData = {
            from: message.key.remoteJid,
            message_id: message.key.id,
            timestamp: message.messageTimestamp,
            type: getMessageType(message),
            content: getMessageContent(message),
            media_url: await getMediaUrl(message)
        };
        
        // Enviar a Django
        try {
            await axios.post(DJANGO_WEBHOOK_INCOMING, webhookData);
            console.log('✅ Mensaje entrante enviado a Django');
        } catch (error) {
            console.error('❌ Error enviando webhook entrante:', error.message);
        }
    });

    // MENSAJES SALIENTES (ESTE ES EL NUEVO)
    sock.ev.on('messages.upsert', async (m) => {
        const message = m.messages[0];
        if (!message.key.fromMe) return; // Solo procesar nuestros mensajes
        
        const webhookData = {
            to: message.key.remoteJid,
            message_id: message.key.id,
            timestamp: message.messageTimestamp,
            type: getMessageType(message),
            content: getMessageContent(message),
            from_me: true,
            media_url: await getMediaUrl(message)
        };
        
        // Enviar a Django (IMPORTANTE)
        try {
            await axios.post(DJANGO_WEBHOOK_OUTGOING, webhookData);
            console.log('✅ Mensaje saliente enviado a Django');
        } catch (error) {
            console.error('❌ Error enviando webhook saliente:', error.message);
        }
    });
}

function getMessageType(message) {
    if (message.message?.imageMessage) return 'image';
    if (message.message?.videoMessage) return 'video';
    if (message.message?.audioMessage) return 'audio';
    if (message.message?.documentMessage) return 'document';
    return 'text';
}

function getMessageContent(message) {
    return message.message?.conversation || 
           message.message?.extendedTextMessage?.text ||
           message.message?.imageMessage?.caption ||
           message.message?.videoMessage?.caption ||
           '';
}

async function getMediaUrl(message) {
    // Implementar descarga y almacenamiento de media
    // Retornar URL pública del archivo
    return null;
}

startWhatsApp();
```

---

## 🧪 **Verificar que Funciona**

### **1. Probar webhook manualmente:**
```bash
curl -X POST http://localhost:8000/webhooks/whatsapp-outgoing/ \
  -H "Content-Type: application/json" \
  -d '{
    "to": "WA-2699-1357-9118-670",
    "message_id": "test_123",
    "timestamp": 1698624136,
    "type": "text",
    "content": "Respuesta de prueba",
    "from_me": true
  }'
```

### **2. Verificar en Django:**
```python
# En Django shell
from core.models import Contact, Conversation
contact = Contact.objects.get(platform_user_id='WA-2699-1357-9118-670')
conv = contact.conversations.filter(status='active').first()
print(f'needs_response: {conv.needs_response}')  # Debe ser False
print(f'Último mensaje: {conv.messages.last().content}')
```

---

## ✅ **Estado Actual**

### **Lo que YA funciona:**
- ✅ Endpoint `/webhooks/whatsapp-outgoing/` funcional
- ✅ Lógica de procesamiento correcta
- ✅ Actualización de `needs_response` 
- ✅ Guardado de mensajes salientes
- ✅ Búsqueda de contactos con formato WA-
- ✅ Auto-refresh en la interfaz web

### **Lo que FALTA configurar:**
- ❌ Bridge de Baileys no envía webhooks salientes automáticamente
- ❌ Configuración de eventos `messages.upsert` con `fromMe: true`

---

## 🎯 **Siguiente Paso**

**Modificar el bridge de Baileys** para que envíe webhooks salientes cuando detecte mensajes con `fromMe: true`.

Una vez configurado esto, el sistema detectará automáticamente:
1. Cuando respondes desde tu celular
2. Actualizará el estado "Sin responder" 
3. Mostrará el mensaje en la interfaz web
4. Ordenará correctamente las conversaciones

**El backend de Django está 100% listo.** Solo falta la configuración del bridge.