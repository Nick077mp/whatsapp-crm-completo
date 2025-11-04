const { default: makeWASocket, DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const qrcode = require('qrcode');
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const FormData = require('form-data');

// ✅ Configuración definitiva - Solo WA-IDs únicos
const DJANGO_BASE_URL = process.env.DJANGO_BASE_URL || 'http://127.0.0.1:8000';

console.log(`🔥 BRIDGE WA DEFINITIVO - Solo WA-IDs únicos`);
console.log(`📡 Django URL: ${DJANGO_BASE_URL}`);

let sock;
let qrCodeData = null;
let connectionState = 'disconnected';
let lastOpenAt = 0; // timestamp ms de la última conexión abierta

// 🔥 FUNCIÓN PRINCIPAL: Siempre devolver WA-ID único
const getWAIdentifier = (jid, pushName = null) => {
    try {
        console.log("🆔 Obteniendo WA-ID para:", jid);
        
        // Limpiar JID para obtener identificador base
        const cleanJid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '');
        
        // ✅ SIEMPRE retornar formato WA-ID único
        const waId = `WA-${cleanJid}`;
        
        console.log(`🔥 WA-ID definitivo: ${waId}`);
        return waId;
        
    } catch (error) {
        console.error("❌ Error generando WA-ID:", error);
        // Fallback seguro
        const safeName = jid.replace(/@.*/, '');
        return `WA-${safeName}`;
    }
};

// Función para formatear números de teléfono (solo para logs informativos)
const formatPhoneForDisplay = (phoneNumber) => {
    if (!phoneNumber) return phoneNumber;
    
    const cleaned = phoneNumber.replace(/\D/g, '');
    
    if (cleaned.startsWith('57') && cleaned.length === 12) {
        return `+${cleaned.slice(0, 2)} ${cleaned.slice(2, 5)} ${cleaned.slice(5, 8)} ${cleaned.slice(8)}`;
    }
    
    if (cleaned.startsWith('1') && cleaned.length === 11) {
        return `+${cleaned.slice(0, 1)} ${cleaned.slice(1, 4)} ${cleaned.slice(4, 7)} ${cleaned.slice(7)}`;
    }
    
    return `+${cleaned}`;
};

// Función para subir archivos multimedia
const uploadMedia = async (mediaBuffer, fileName, mimeType) => {
    try {
        const form = new FormData();
        form.append('file', mediaBuffer, {
            filename: fileName,
            contentType: mimeType
        });

        console.log(`📎 Subiendo archivo: ${fileName} (${mimeType})`);
        
        const uploadResponse = await axios.post(`${DJANGO_BASE_URL}/api/upload-media/`, form, {
            headers: {
                ...form.getHeaders()
            },
            timeout: 30000
        });
        
        if (uploadResponse.data.success) {
            console.log(`✅ Archivo subido: ${uploadResponse.data.media_url}`);
            return uploadResponse.data.media_url;
        } else {
            console.error('❌ Error subiendo archivo:', uploadResponse.data.error);
            return null;
        }
        
    } catch (error) {
        console.error('❌ Error en upload:', error.message);
        return null;
    }
};

// Función principal del socket
async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('./auth_info');

    // Logger simple compatible con Baileys
    const logger = {
        child: () => logger,
        trace: () => {},
        debug: () => {},
        info: () => {},
        warn: () => {},
        error: () => {}
    };

    sock = makeWASocket({
        auth: state,
        printQRInTerminal: false,  // Manejamos QR manualmente
        logger: logger,
        browser: ['Chrome (Linux)', 'Chrome', '121.0.0.0'],
        markOnlineOnConnect: false,
        syncFullHistory: false
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        
        console.log('📱 Estado conexión:', connection);
        connectionState = connection || 'disconnected';

        if (qr) {
            console.log('📱 Generando código QR...');
            qrcode.toDataURL(qr, (err, url) => {
                if (!err) {
                    qrCodeData = url;
                    console.log('✅ Código QR generado');
                }
            });
        }

        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect?.error instanceof Boom) 
                ? lastDisconnect.error.output.statusCode !== DisconnectReason.loggedOut
                : true;

            console.log('🔄 Conexión cerrada, reconectando...', shouldReconnect);
            if (shouldReconnect) {
                setTimeout(connectToWhatsApp, 3000);
            }
        } else if (connection === 'open') {
            console.log('✅ Conectado a WhatsApp');
            qrCodeData = null;
            lastOpenAt = Date.now();
        }
    });

    // 🔥 EVENTO PRINCIPAL: Mensajes entrantes - Solo WA-IDs
    sock.ev.on('messages.upsert', async (m) => {
        try {
            const message = m.messages[0];
            
            if (!message || message.key.fromMe) return;

            const from = message.key.remoteJid;
            const messageId = message.key.id;
            const timestamp = message.messageTimestamp;

            console.log('\n📥 MENSAJE ENTRANTE:');
            console.log('From JID:', from);

            // 🔥 Obtener WA-ID único definitivo
            const waIdentifier = getWAIdentifier(from, message.pushName);
            console.log('🆔 WA-ID final:', waIdentifier);

            // Procesar contenido del mensaje
            let messageType = 'text';
            let messageContent = '';
            let mediaUrl = null;

            if (message.message?.conversation) {
                messageContent = message.message.conversation;
            } else if (message.message?.extendedTextMessage) {
                messageContent = message.message.extendedTextMessage.text;
            } else if (message.message?.imageMessage) {
                messageType = 'image';
                messageContent = message.message.imageMessage.caption || 'Imagen';
                
                try {
                    const buffer = await sock.downloadMediaMessage(message);
                    const fileName = `image_${messageId}.jpg`;
                    mediaUrl = await uploadMedia(buffer, fileName, 'image/jpeg');
                } catch (error) {
                    console.error('❌ Error descargando imagen:', error);
                }
            } else if (message.message?.documentMessage) {
                messageType = 'document';
                const doc = message.message.documentMessage;
                messageContent = doc.fileName || 'Documento';
                
                try {
                    const buffer = await sock.downloadMediaMessage(message);
                    const fileName = doc.fileName || `document_${messageId}`;
                    mediaUrl = await uploadMedia(buffer, fileName, doc.mimetype);
                } catch (error) {
                    console.error('❌ Error descargando documento:', error);
                }
            } else if (message.message?.audioMessage) {
                messageType = 'audio';
                messageContent = 'Mensaje de voz';
                
                try {
                    const buffer = await sock.downloadMediaMessage(message);
                    const fileName = `audio_${messageId}.ogg`;
                    mediaUrl = await uploadMedia(buffer, fileName, 'audio/ogg');
                } catch (error) {
                    console.error('❌ Error descargando audio:', error);
                }
            } else {
                messageContent = 'Mensaje no soportado';
                console.log('⚠️ Tipo de mensaje no reconocido:', Object.keys(message.message || {}));
            }

            // Preparar datos para Django
            const webhookData = {
                from: waIdentifier,  // 🔥 Siempre WA-ID único
                received_at: '+57 302 2620031',  // Número de negocio fijo
                message_id: messageId,
                timestamp: timestamp,
                type: messageType,
                content: messageContent,
                media_url: mediaUrl,
                push_name: message.pushName || null
            };

            console.log('📤 Enviando a Django:', JSON.stringify(webhookData, null, 2));

            // Enviar webhook a Django
            try {
                const response = await axios.post(`${DJANGO_BASE_URL}/webhooks/whatsapp/`, webhookData, {
                    timeout: 10000
                });

                if (response.data.success) {
                    console.log('✅ Webhook enviado exitosamente');
                } else {
                    console.log('⚠️ Respuesta webhook:', response.data);
                }
            } catch (webhookError) {
                console.error('❌ Error enviando webhook:', webhookError.message);
            }

        } catch (error) {
            console.error('❌ Error procesando mensaje:', error);
        }
    });
}

// API REST para envío de mensajes
const express = require('express');
const app = express();

app.use(express.json());
app.use(express.static('public'));

// Endpoint para obtener estado
app.get('/status', (req, res) => {
    // Considerar como "conectado" si está abierto o si estuvo abierto en el último minuto (suaviza reconexiones breves)
    const recentlyOpen = lastOpenAt && (Date.now() - lastOpenAt < 60 * 1000);
    res.json({
        connected: connectionState === 'open' || recentlyOpen,
        state: connectionState,
        qrCode: qrCodeData,
        lastOpenAt,
        timestamp: new Date().toISOString()
    });
});

// 🔥 Endpoint para envío - Solo acepta WA-IDs
app.post('/send-message', async (req, res) => {
    try {
        const { to, message, type = 'text' } = req.body;

        if (!to || !message) {
            return res.status(400).json({ 
                success: false, 
                error: 'Faltan parámetros: to, message' 
            });
        }

        if (connectionState !== 'open') {
            return res.status(503).json({ 
                success: false, 
                error: 'WhatsApp no conectado' 
            });
        }

        console.log('\n📤 ENVÍO DE MENSAJE:');
        console.log('To WA-ID:', to);
        console.log('Message:', message);

        // 🔥 Convertir WA-ID a JID para envío
        let targetJid = to;
        if (to.startsWith('WA-')) {
            // Remover prefijo WA- y agregar dominio WhatsApp
            const cleanId = to.substring(3);
            targetJid = `${cleanId}@s.whatsapp.net`;
            console.log('🔄 JID para envío:', targetJid);
        }

        // Obtener WA-ID consistente para el destinatario
        const recipientWAId = getWAIdentifier(targetJid);
        console.log('🆔 WA-ID destinatario:', recipientWAId);

        // Enviar mensaje
        await sock.sendMessage(targetJid, { text: message });

        // Notificar a Django sobre mensaje enviado
        const outgoingData = {
            to: recipientWAId,  // 🔥 Usar WA-ID único
            message: message,
            type: type,
            timestamp: Math.floor(Date.now() / 1000),
            status: 'sent'
        };

        console.log('📤 Notificando mensaje enviado a Django:', JSON.stringify(outgoingData, null, 2));

        try {
            await axios.post(`${DJANGO_BASE_URL}/webhooks/whatsapp-outgoing/`, outgoingData, {
                timeout: 10000
            });
            console.log('✅ Mensaje enviado y notificado a Django');
        } catch (notifyError) {
            console.error('⚠️ Error notificando a Django:', notifyError.message);
        }

        res.json({ success: true, message: 'Mensaje enviado' });

    } catch (error) {
        console.error('❌ Error enviando mensaje:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`🚀 Servidor iniciado en puerto ${PORT}`);
    console.log(`🔥 Modo: Solo WA-IDs únicos`);
    connectToWhatsApp();
});