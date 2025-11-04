const express = require('express');
const cors = require('cors');
const axios = require('axios');
const fs = require('fs-extra');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { makeWASocket, DisconnectReason, useMultiFileAuthState, downloadMediaMessage } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');

const app = express();
const PORT = 3000;

// Configuración
app.use(cors());
app.use(express.json());

// Variables globales
let sock = null;
let isConnected = false;
let qrCodeData = null;

// Cache para mensajes recientes (para capturar contenido de mensajes salientes)
const recentMessagesCache = new Map();

// URL del Django backend
const DJANGO_BASE_URL = 'http://localhost:8000';

// Directorio para archivos multimedia temporales
const MEDIA_DIR = path.join(__dirname, 'media');

// Asegurar que exista el directorio de media
fs.ensureDirSync(MEDIA_DIR);

/**
 * REINGENIERÍA COMPLETA - Solo números reales colombianos @s.whatsapp.net
 * NO más LIDs, NO más WA-IDs, NO más duplicaciones
 */

/**
 * Validar y formatear números colombianos únicamente
 */
function formatColombianNumber(rawNumber) {
    console.log("🇨🇴 Formateando número colombiano:", rawNumber);
    
    // Limpiar número
    const digits = rawNumber.replace(/\D/g, '');
    
    // Debe ser 57 + 10 dígitos (colombiano completo)
    if (digits.startsWith('57') && digits.length === 12) {
        const formatted = `+57 ${digits.substring(2, 5)} ${digits.substring(5, 8)} ${digits.substring(8)}`;
        console.log("✅ Número colombiano formateado:", formatted);
        return formatted;
    }
    
    throw new Error(`Número no válido: ${rawNumber}`);
}

/**
 * Validar JID y extraer número colombiano
 */
function validateAndExtractNumber(jid) {
    console.log("🔍 VALIDANDO JID:", jid);
    console.log("🔍 JID incluye @s.whatsapp.net:", jid.includes('@s.whatsapp.net'));
    console.log("🔍 JID incluye @lid:", jid.includes('@lid'));
    console.log("🔍 JID incluye @c.us:", jid.includes('@c.us'));
    console.log("🔍 JID incluye @g.us:", jid.includes('@g.us'));
    
    // RECHAZAR todo lo que no sea @s.whatsapp.net
    if (!jid.includes('@s.whatsapp.net')) {
        console.log(`❌ JID RECHAZADO: ${jid} - Motivo: No es @s.whatsapp.net`);
        throw new Error(`JID rechazado - Solo se aceptan JIDs estándar: ${jid}`);
    }
    
    // Extraer número
    const number = jid.replace('@s.whatsapp.net', '');
    
    // Validar que sea número colombiano
    if (!number.match(/^57\d{10}$/)) {
        throw new Error(`Número rechazado - Solo números colombianos: ${number}`);
    }
    
    return formatColombianNumber(number);
}

/**
 * Procesar mensaje multimedia y subirlo al servidor Django
 */
async function processMediaMessage(message) {
    try {
        let messageType = 'text';
        let caption = '';
        let mediaBuffer = null;
        let mediaUrl = null;
        let fileName = '';
        let mimeType = '';

        // Identificar tipo de mensaje multimedia
        if (message.message.imageMessage) {
            messageType = 'image';
            caption = message.message.imageMessage.caption || '';
            mimeType = message.message.imageMessage.mimetype || 'image/jpeg';
            fileName = `image_${uuidv4()}.jpg`;
        } else if (message.message.videoMessage) {
            messageType = 'video';
            caption = message.message.videoMessage.caption || '';
            mimeType = message.message.videoMessage.mimetype || 'video/mp4';
            fileName = `video_${uuidv4()}.mp4`;
        } else if (message.message.audioMessage) {
            messageType = 'audio';
            caption = 'Mensaje de audio';
            mimeType = message.message.audioMessage.mimetype || 'audio/ogg';
            fileName = `audio_${uuidv4()}.ogg`;
        } else if (message.message.documentMessage) {
            messageType = 'document';
            caption = message.message.documentMessage.caption || '';
            mimeType = message.message.documentMessage.mimetype || 'application/octet-stream';
            fileName = message.message.documentMessage.fileName || `document_${uuidv4()}`;
        }

        if (messageType !== 'text') {
            // Descargar el archivo multimedia
            console.log(`📥 Descargando ${messageType}: ${fileName}`);
            mediaBuffer = await downloadMediaMessage(message, 'buffer', {});
            
            if (mediaBuffer) {
                // Guardar archivo temporalmente
                const tempPath = path.join(MEDIA_DIR, fileName);
                await fs.writeFile(tempPath, mediaBuffer);
                
                // Subir a Django usando FormData
                const FormData = require('form-data');
                const formData = new FormData();
                formData.append('media_file', fs.createReadStream(tempPath), {
                    filename: fileName,
                    contentType: mimeType
                });
                
                // Subir archivo al servidor Django
                const uploadResponse = await axios.post(`${DJANGO_BASE_URL}/api/upload-media/`, formData, {
                    headers: {
                        ...formData.getHeaders()
                    },
                    timeout: 30000
                });
                
                if (uploadResponse.data.success) {
                    mediaUrl = uploadResponse.data.media_url;
                    console.log(`✅ Archivo ${messageType} subido: ${mediaUrl}`);
                }
                
                // Limpiar archivo temporal
                await fs.remove(tempPath);
            }
        }

        return {
            messageType,
            content: caption || `${messageType} recibido`,
            mediaUrl,
            fileName,
            mimeType
        };
        
    } catch (error) {
        console.error('❌ Error procesando multimedia:', error);
        return {
            messageType: 'text',
            content: 'Error procesando archivo multimedia',
            mediaUrl: null,
            fileName: '',
            mimeType: ''
        };
    }
}

/**
 * Inicializar conexión de WhatsApp
 */
async function initializeWhatsApp() {
    try {
        // Usar autenticación multi-archivo
        const { state, saveCreds } = await useMultiFileAuthState('./auth_info');
        
        sock = makeWASocket({
            auth: state,
            printQRInTerminal: false,
        });

        // Evento de conexión actualizada
        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            
            if (qr) {
                console.log('📱 Código QR generado');
                qrCodeData = qr;
                qrcode.generate(qr, { small: true });
            }
            
            if (connection === 'close') {
                isConnected = false;
                console.log('❌ Conexión perdida');
                
                const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
                
                if (shouldReconnect) {
                    console.log('🔄 Reconectando...');
                    setTimeout(initializeWhatsApp, 3000);
                }
            } else if (connection === 'open') {
                isConnected = true;
                qrCodeData = null;
                console.log('✅ WhatsApp conectado exitosamente!');
            }
        });

        // Evento de nuevas credenciales
        sock.ev.on('creds.update', saveCreds);

        // Evento de mensajes recibidos - REINGENIERÍA COMPLETA
        sock.ev.on('messages.upsert', async (m) => {
            const messages = m.messages;
            
            // **DEBUG: Mostrar estructura completa del evento messages.upsert**
            console.log("🔍 ESTRUCTURA COMPLETA DEL EVENTO messages.upsert:");
            console.log(JSON.stringify(m, null, 2));
            
            for (const message of messages) {
                // **DEBUG: Mostrar estructura completa de cada mensaje individual ANTES DE CUALQUIER VALIDACIÓN**
                console.log("========================================");
                console.log("🔍 MENSAJE RAW COMPLETO (ANTES DE VALIDACIÓN):");
                console.log("🔍 message.key.remoteJid RAW:", message.key?.remoteJid);
                console.log("🔍 message.key.fromMe:", message.key?.fromMe);
                console.log("🔍 message.key completo:", JSON.stringify(message.key, null, 2));
                console.log("🔍 message.message completo:", JSON.stringify(message.message, null, 2));
                console.log("🔍 OBJETO MESSAGE COMPLETO:");
                console.log(JSON.stringify(message, null, 2));
                console.log("========================================");
                
                // Ignorar mensajes de estado
                if (!message.message) continue;
                
                // **MANEJAR MENSAJES SALIENTES (PROPIOS) DIRECTAMENTE AQUÍ**
                if (message.key.fromMe) {
                    console.log("📤 MENSAJE SALIENTE DETECTADO - Estructura completa:");
                    console.log("📤 message.key:", JSON.stringify(message.key, null, 2));
                    console.log("📤 message.message:", JSON.stringify(message.message, null, 2));
                    
                    try {
                        const remoteJid = message.key.remoteJid;
                        const cleanJid = remoteJid.split(':')[0];
                        
                        // Validar JID
                        const phoneNumber = validateAndExtractNumber(cleanJid);
                        
                        // Extraer contenido real del mensaje saliente
                        const messageId = message.key.id;
                        const timestamp = Date.now();
                        
                        let messageContent = 'Mensaje enviado desde WhatsApp';
                        let messageType = 'text';
                        
                        if (message.message) {
                            const msgContent = message.message.conversation || 
                                            message.message.extendedTextMessage?.text ||
                                            message.message.imageMessage?.caption ||
                                            message.message.videoMessage?.caption ||
                                            null;
                            
                            if (msgContent) {
                                messageContent = msgContent;
                                console.log("✅ Contenido real extraído de mensaje saliente:", msgContent);
                            }
                            
                            // Determinar tipo
                            if (message.message.imageMessage) messageType = 'image';
                            else if (message.message.videoMessage) messageType = 'video';
                            else if (message.message.audioMessage) messageType = 'audio';
                            else if (message.message.documentMessage) messageType = 'document';
                            else if (message.message.stickerMessage) messageType = 'sticker';
                            else if (message.message.locationMessage) messageType = 'location';
                        }
                        
                        const outgoingData = {
                            to: phoneNumber,
                            from: '+57 302 2620031',
                            message_id: messageId,
                            timestamp: Math.floor(timestamp / 1000),
                            type: messageType,
                            content: messageContent,
                            from_me: true
                        };
                        
                        console.log("📤 Mensaje saliente REAL detectado:", outgoingData);
                        
                        // Notificar a Django
                        await axios.post(`${DJANGO_BASE_URL}/webhooks/whatsapp-outgoing/`, outgoingData, {
                            timeout: 5000
                        });
                        
                        console.log("✅ Mensaje saliente REAL notificado a Django");
                        
                    } catch (error) {
                        console.error("❌ Error procesando mensaje saliente real:", error.message);
                    }
                    
                    // Continuar con el siguiente mensaje (no procesar como entrante)
                    continue;
                }
                
                try {
                    const from = message.key.remoteJid;
                    
                    console.log("📨 MENSAJE ENTRANTE DETECTADO - Estructura completa:");
                    console.log("📨 message.key:", JSON.stringify(message.key, null, 2));
                    console.log("📨 message.message:", JSON.stringify(message.message, null, 2));
                    console.log("📨 message completo:", JSON.stringify(message, null, 2));
                    
                    console.log(`🔍 PROCESANDO MENSAJE ENTRANTE - JID RAW COMPLETO: ${from}`);
                    console.log(`🔍 Tipo de JID detectado:`, from.includes('@lid') ? 'LID' : from.includes('@s.whatsapp.net') ? 'STANDARD' : 'OTRO');
                    
                    // VALIDACIÓN ESTRICTA: Solo JIDs colombianos @s.whatsapp.net
                    const phoneNumber = validateAndExtractNumber(from);
                    
                    // Procesar contenido del mensaje
                    const messageId = message.key.id;
                    const timestamp = message.messageTimestamp;
                    
                    // Procesar multimedia si existe
                    const mediaInfo = await processMediaMessage(message);
                    
                    // Extraer contenido de texto
                    let textContent = '';
                    if (message.message.conversation) {
                        textContent = message.message.conversation;
                    } else if (message.message.extendedTextMessage) {
                        textContent = message.message.extendedTextMessage.text;
                    }
                    
                    const webhookData = {
                        from: phoneNumber,
                        received_at: '+57 302 2620031', // Número fijo del negocio
                        message_id: messageId,
                        timestamp: timestamp,
                        type: mediaInfo.messageType,
                        content: textContent || mediaInfo.content,
                        media_url: mediaInfo.mediaUrl
                    };
                    
                    console.log("📨 Mensaje procesado:", webhookData);
                    
                    // **CACHE: Guardar mensaje para referencia futura en mensajes salientes**
                    const cacheKey = `${messageId}`;
                    recentMessagesCache.set(cacheKey, {
                        content: textContent || mediaInfo.content,
                        type: mediaInfo.messageType,
                        timestamp: timestamp,
                        jid: phoneNumber
                    });
                    
                    // Limpiar cache después de 5 minutos (mantener solo 100 mensajes recientes)
                    if (recentMessagesCache.size > 100) {
                        const oldestKey = recentMessagesCache.keys().next().value;
                        recentMessagesCache.delete(oldestKey);
                    }
                    
                    // Enviar a Django
                    await axios.post(`${DJANGO_BASE_URL}/webhooks/whatsapp/`, webhookData, {
                        timeout: 10000
                    });
                    
                    console.log("✅ Mensaje enviado a Django");
                    
                } catch (error) {
                    console.error("❌ Mensaje rechazado:", error.message);
                    // Ignorar silenciosamente mensajes que no cumplan las reglas
                }
            }
        });

        // Evento de mensajes salientes (enviados desde WhatsApp Web/App) - DESHABILITADO
        // Ahora procesamos mensajes salientes directamente en messages.upsert
        /*
        sock.ev.on('messages.update', async (updates) => {
            for (const update of updates) {
                if (update.update.status === 3) { // Mensaje enviado
                    try {
                        const remoteJid = update.key.remoteJid;
                        
                        // Limpiar JID de sufijos adicionales (como :49, :50, etc.)
                        const cleanJid = remoteJid.split(':')[0];
                        
                        // VALIDACIÓN: Solo procesar JIDs válidos
                        const phoneNumber = validateAndExtractNumber(cleanJid);
                        
                        // Obtener detalles del mensaje
                        const messageId = update.key.id;
                        const timestamp = Date.now();
                        
                        // **ACTUALIZACIÓN: Intentar obtener el mensaje real para extraer contenido**
                        let messageContent = 'Mensaje enviado desde WhatsApp';
                        let messageType = 'text';
                        
                        try {
                            // Intentar obtener el mensaje del historial para extraer contenido real
                            const messages = await sock.fetchMessage(remoteJid, 1);
                            if (messages && messages.length > 0) {
                                const message = messages[0];
                                if (message.message) {
                                    const msgContent = message.message.conversation || 
                                                    message.message.extendedTextMessage?.text ||
                                                    message.message.imageMessage?.caption ||
                                                    message.message.videoMessage?.caption ||
                                                    null;
                                    
                                    if (msgContent) {
                                        messageContent = msgContent;
                                        console.log("✅ Contenido real extraído:", msgContent);
                                    }
                                    
                                    // Determinar tipo de mensaje
                                    if (message.message.imageMessage) messageType = 'image';
                                    else if (message.message.videoMessage) messageType = 'video';
                                    else if (message.message.audioMessage) messageType = 'audio';
                                    else if (message.message.documentMessage) messageType = 'document';
                                    else if (message.message.stickerMessage) messageType = 'sticker';
                                    else if (message.message.locationMessage) messageType = 'location';
                                }
                            }
                        } catch (fetchError) {
                            console.log("⚠️ No se pudo obtener contenido real del mensaje, usando fallback");
                        }
                        
                        const outgoingData = {
                            to: phoneNumber,
                            from: '+57 302 2620031',
                            message_id: messageId,
                            timestamp: Math.floor(timestamp / 1000),
                            type: messageType,
                            content: messageContent,
                            from_me: true
                        };
                        
                        console.log("📤 Mensaje saliente detectado:", outgoingData);
                        
                        // Notificar a Django
                        await axios.post(`${DJANGO_BASE_URL}/webhooks/whatsapp-outgoing/`, outgoingData, {
                            timeout: 5000
                        });
                        
                        console.log("✅ Mensaje saliente notificado a Django");
                        
                    } catch (error) {
                        console.error("❌ Error procesando mensaje saliente:", error.message);
                        // Silenciosamente ignorar mensajes que no cumplan reglas
                    }
                }
            }
        });
        */
        
    } catch (error) {
        console.error('❌ Error inicializando WhatsApp:', error);
        setTimeout(initializeWhatsApp, 5000);
    }
}

// Endpoints de la API

app.get('/status', (req, res) => {
    res.json({
        connected: isConnected,
        qr_available: !!qrCodeData
    });
});

app.get('/qr', (req, res) => {
    if (qrCodeData) {
        res.json({ qr: qrCodeData });
    } else {
        res.status(404).json({ error: 'No hay código QR disponible' });
    }
});

app.post('/send-message', async (req, res) => {
    try {
        const { to, message } = req.body;
        
        if (!to || !message) {
            return res.status(400).json({
                success: false,
                error: 'Faltan parámetros: to, message'
            });
        }
        
        if (!isConnected || !sock) {
            return res.status(500).json({
                success: false,
                error: 'WhatsApp no está conectado'
            });
        }
        
        // Normalizar número para envío (formato: 573001234567@s.whatsapp.net)
        let targetJid;
        if (to.includes('@')) {
            targetJid = to;
        } else {
            // Convertir número formateado a JID
            const cleanNumber = to.replace(/\D/g, '');
            if (cleanNumber.startsWith('57') && cleanNumber.length === 12) {
                targetJid = `${cleanNumber}@s.whatsapp.net`;
            } else {
                throw new Error('Número no válido para envío');
            }
        }
        
        console.log("📤 Enviando mensaje:", { to: targetJid, message });
        
        // Enviar mensaje
        const sentMessage = await sock.sendMessage(targetJid, { text: message });
        
        res.json({
            success: true,
            message_id: sentMessage.key.id,
            target: targetJid
        });
        
    } catch (error) {
        console.error('❌ Error enviando mensaje:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

app.post('/restart', async (req, res) => {
    try {
        if (sock) {
            sock.end();
        }
        setTimeout(initializeWhatsApp, 2000);
        res.json({ success: true, message: 'Reiniciando conexión...' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Iniciar servidor
app.listen(PORT, () => {
    console.log(`🚀 WhatsApp Bridge ejecutándose en puerto ${PORT}`);
    console.log('📱 Inicializando conexión de WhatsApp...');
    initializeWhatsApp();
});

// Manejo de cierre graceful
process.on('SIGINT', () => {
    console.log('🛑 Cerrando WhatsApp Bridge...');
    if (sock) {
        sock.end();
    }
    process.exit(0);
});