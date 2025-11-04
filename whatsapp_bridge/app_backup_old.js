const express = require('express');
const cors = require('cors');
const axios = require('axios');
const fs = require('fs-extra');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { makeWASocket, DisconnectReason, useMultiFileAuthState, downloadMediaMessage } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');

const app = express();
const PORT = 3001;

// Configuración
app.use(cors());
app.use(express.json());

// Variables globales
let sock = null;
let isConnected = false;
let qrCodeData = null;

// URL del Django backend
const DJANGO_BASE_URL = 'http://localhost:8000';

// Directorio para archivos multimedia temporales
const MEDIA_DIR = path.join(__dirname, 'media');

// Asegurar que exista el directorio de media
fs.ensureDirSync(MEDIA_DIR);

// Utilidad: envolver promesas con timeout controlado
function withTimeout(promise, ms) {
    return Promise.race([
        promise,
        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), ms))
    ]);
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
                    timeout: 30000 // 30 segundos timeout
                });
                
                if (uploadResponse.data.success) {
                    mediaUrl = uploadResponse.data.media_url;
                    console.log(`✅ Archivo ${messageType} subido: ${mediaUrl}`);
                } else {
                    console.error('❌ Error subiendo archivo:', uploadResponse.data.error);
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
            printQRInTerminal: false, // Manejaremos el QR manualmente
        });

        // Evento de conexión actualizada
        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            
            if (qr) {
                console.log('📱 Código QR generado');
                qrCodeData = qr;
                
                // Mostrar QR en terminal también
                qrcode.generate(qr, { small: true });
                
                // Opcional: Notificar a Django que hay un nuevo QR
                try {
                    await axios.post(`${DJANGO_BASE_URL}/api/whatsapp/qr-updated/`, {
                        qr: qr,
                        timestamp: new Date().toISOString()
                    });
                } catch (error) {
                    console.log('⚠️ No se pudo notificar QR a Django:', error.message);
                }
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
                
                // Notificar a Django que estamos conectados
                try {
                    await axios.post(`${DJANGO_BASE_URL}/api/whatsapp/connected/`, {
                        status: 'connected',
                        timestamp: new Date().toISOString()
                    });
                } catch (error) {
                    console.log('⚠️ No se pudo notificar conexión a Django:', error.message);
                }
            }
        });

        // Evento de nuevas credenciales
        sock.ev.on('creds.update', saveCreds);

        // Evento de mensajes recibidos
        sock.ev.on('messages.upsert', async (m) => {
            const messages = m.messages;
            
            for (const message of messages) {
                if (!message.key.fromMe && message.message) {
                    // Mensaje entrante (del cliente hacia nosotros)
                    await handleIncomingMessage(message);
                } else if (message.key.fromMe && message.message) {
                    // Mensaje saliente (de nosotros hacia el cliente) - NUEVO
                    await handleOutgoingMessage(message);
                }
            }
        });

    } catch (error) {
        console.error('❌ Error inicializando WhatsApp:', error);
        setTimeout(initializeWhatsApp, 5000);
    }
}

/**
 * Manejar mensajes entrantes
 */
async function handleIncomingMessage(message) {
    try {
        const from = message.key.remoteJid;
        const messageId = message.key.id;
        const timestamp = message.messageTimestamp;
        
        // Excluir mensajes de grupos
        if (from.includes('@g.us')) {
            console.log('Mensaje de grupo ignorado');
            return;
        }
        
        // Procesar contenido del mensaje
        let messageContent = '';
        let messageType = 'text';
        let mediaUrl = null;
        
        if (message.message.conversation) {
            messageContent = message.message.conversation;
            messageType = 'text';
        } else if (message.message.extendedTextMessage) {
            messageContent = message.message.extendedTextMessage.text;
            messageType = 'text';
        } else if (message.message.imageMessage || message.message.videoMessage || 
                   message.message.audioMessage || message.message.documentMessage) {
            // Procesar mensaje multimedia
            console.log('📎 Procesando mensaje multimedia...');
            const mediaResult = await processMediaMessage(message);
            messageType = mediaResult.messageType;
            messageContent = mediaResult.content;
            mediaUrl = mediaResult.mediaUrl;
        } else if (message.message.locationMessage) {
            messageType = 'location';
            const lat = message.message.locationMessage.degreesLatitude;
            const lng = message.message.locationMessage.degreesLongitude;
            messageContent = `Ubicación: ${lat}, ${lng}`;
        }

        // Enviar mensaje a Django
        // Intentar obtener el número real del contacto
        const getRealPhoneNumber = async (jid, message) => {
            try {
                console.log("� Obteniendo número real para JID:", jid);
                
                // Limpiar JID
                const cleanJid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '');
                
                // Intentar obtener información del contacto desde WhatsApp
                if (sock && sock.onWhatsApp) {
                    try {
                        const contactInfo = await sock.onWhatsApp(jid);
                        console.log("📋 Info de contacto:", contactInfo);
                        
                        if (contactInfo && contactInfo.length > 0) {
                            const contact = contactInfo[0];
                            if (contact.jid && contact.jid !== jid) {
                                // Si el JID del contacto es diferente, podría ser el número real
                                const realNumber = contact.jid.replace('@s.whatsapp.net', '');
                                if (realNumber.match(/^\d+$/)) {
                                    console.log("✅ Número real encontrado:", realNumber);
                                    return formatRealPhoneNumber(realNumber);
                                }
                            }
                        }
                    } catch (contactError) {
                        console.log("⚠️ No se pudo obtener info de contacto:", contactError.message);
                    }
                }
                
                // Si el JID limpio parece un número de teléfono válido, úsalo
                if (cleanJid.match(/^57\d{10}$/)) {
                    console.log("📞 JID parece número colombiano válido");
                    return formatRealPhoneNumber(cleanJid);
                }
                
                // Para LIDs, intentar extraer número móvil colombiano antes de crear WA-ID
                if (jid.includes('@lid')) {
                    console.log("📞 Extrayendo solo números del JID:", cleanJid);
                    console.log("✅ Usando números extraídos:", cleanJid);
                    return formatRealPhoneNumber(cleanJid);
                }
                
                // Si no podemos determinar el número real, usar formato de ID único
                console.log("🆔 Usando formato de ID único para:", cleanJid);
                const formatted = cleanJid.match(/.{1,4}/g)?.join('-') || cleanJid;
                return `WA-${formatted}`;
                
            } catch (error) {
                console.error("❌ Error obteniendo número real:", error);
                const cleanJid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '');
                const formatted = cleanJid.match(/.{1,4}/g)?.join('-') || cleanJid;
                return `WA-${formatted}`;
            }
        };
        
        // Formatear número de teléfono real
        const formatRealPhoneNumber = (phoneNumber) => {
            console.log("📱 Formateando número real:", phoneNumber);
            
            // Remover cualquier carácter no numérico
            const cleanNumber = phoneNumber.replace(/\D/g, '');
            console.log("🔢 Número limpio (todos los dígitos):", cleanNumber);
            
            // Buscar específicamente números móviles colombianos (3 + 9 dígitos)
            const mobileMatch = cleanNumber.match(/(3\d{9})/);
            if (mobileMatch) {
                const mobile = mobileMatch[1];
                const formatted = `+57 ${mobile.substring(0, 3)} ${mobile.substring(3, 6)} ${mobile.substring(6)}`;
                console.log("🇨🇴 ✅ Móvil colombiano detectado en posición:", formatted);
                return formatted;
            }
            
            if (cleanNumber.startsWith('57') && cleanNumber.length === 12) {
                // Número colombiano: 573007341192 -> +57 300 734 1192
                const formatted = `+57 ${cleanNumber.substring(2, 5)} ${cleanNumber.substring(5, 8)} ${cleanNumber.substring(8)}`;
                console.log("🇨🇴 ✅ Número colombiano completo encontrado:", formatted);
                return formatted;
            } else if (cleanNumber.startsWith('1') && cleanNumber.length === 11) {
                // Número USA/Canadá: 15551234567 -> +1 555 123 4567
                const formatted = `+1 ${cleanNumber.substring(1, 4)} ${cleanNumber.substring(4, 7)} ${cleanNumber.substring(7)}`;
                console.log("🇺🇸 Número USA/Canadá formateado:", formatted);
                return formatted;
            } else if (cleanNumber.length >= 10) {
                // Formato internacional genérico
                const countryCode = cleanNumber.substring(0, cleanNumber.length - 10);
                const number = cleanNumber.substring(cleanNumber.length - 10);
                const formatted = `+${countryCode} ${number.substring(0, 3)} ${number.substring(3, 6)} ${number.substring(6)}`;
                console.log("🌍 Formato internacional genérico:", formatted);
                return formatted;
            }
            
            // Si no se puede formatear como número válido, crear WA-ID
            console.log("❓ No se pudo formatear como número válido, creando WA-ID");
            const waIdFormatted = cleanNumber.match(/.{1,4}/g)?.join('-') || cleanNumber;
            return `WA-${waIdFormatted}`;
        };

        // Obtener el número real del remitente
        const realPhoneNumber = await getRealPhoneNumber(from, message);
        
        // Obtener información sobre qué número de negocio recibió el mensaje
        // Por ahora usamos una configuración fija ya que Baileys no proporciona esta información directamente
        const businessNumbers = {
            'support': '+57 302 2620031',
            'sales': '+57 324 323 0276'
        };
        
        // Por defecto asumimos que es soporte, pero esto debe mejorarse
        // TODO: Implementar detección automática del número de destino
        let receivedAt = businessNumbers.support;
        
        const webhookData = {
            from: realPhoneNumber,
            received_at: receivedAt,  // Número de negocio que recibió el mensaje
            message_id: messageId,
            timestamp: timestamp,
            type: messageType,
            content: messageContent || 'Mensaje multimedia',
            media_url: mediaUrl
        };

        console.log('📨 Mensaje recibido:', webhookData);

        // Enviar a Django webhook
        try {
            await axios.post(`${DJANGO_BASE_URL}/webhooks/whatsapp/`, webhookData);
            console.log('✅ Mensaje enviado a Django');
        } catch (error) {
            console.error('❌ Error enviando mensaje a Django:', error.message);
        }

    } catch (error) {
        console.error('❌ Error procesando mensaje:', error);
    }
}

/**
 * Manejar mensajes salientes (enviados desde WhatsApp directamente)
 */
async function handleOutgoingMessage(message) {
    try {
        const to = message.key.remoteJid;
        const messageId = message.key.id;
        const timestamp = message.messageTimestamp;
        
        // Excluir mensajes de grupos
        if (to.includes('@g.us')) {
            console.log('Mensaje saliente de grupo ignorado');
            return;
        }
        
        // Extraer contenido del mensaje
        let messageContent = '';
        let messageType = 'text';
        
        if (message.message.conversation) {
            messageContent = message.message.conversation;
        } else if (message.message.extendedTextMessage) {
            messageContent = message.message.extendedTextMessage.text;
        } else if (message.message.imageMessage) {
            messageType = 'image';
            messageContent = message.message.imageMessage.caption || 'Imagen enviada';
        } else if (message.message.videoMessage) {
            messageType = 'video';
            messageContent = message.message.videoMessage.caption || 'Video enviado';
        } else if (message.message.audioMessage) {
            messageType = 'audio';
            messageContent = 'Audio enviado';
        } else if (message.message.documentMessage) {
            messageType = 'document';
            messageContent = message.message.documentMessage.fileName || 'Documento enviado';
        } else if (message.message.locationMessage) {
            messageType = 'location';
            const lat = message.message.locationMessage.degreesLatitude;
            const lng = message.message.locationMessage.degreesLongitude;
            messageContent = `Ubicación enviada: ${lat}, ${lng}`;
        }

        // Obtener el número real del destinatario (igual que en mensajes entrantes)
        const getRealPhoneNumber = async (jid, message) => {
            try {
                console.log("📱 [SALIENTE] Obteniendo número real para JID:", jid);
                
                // Limpiar JID
                const cleanJid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '');
                
                // Intentar obtener información del contacto desde WhatsApp
                if (sock && sock.onWhatsApp) {
                    try {
                        const contactInfo = await sock.onWhatsApp(jid);
                        console.log("📋 [SALIENTE] Info de contacto:", contactInfo);
                        
                        if (contactInfo && contactInfo.length > 0) {
                            const contact = contactInfo[0];
                            if (contact.jid && contact.jid !== jid) {
                                // Si el JID del contacto es diferente, podría ser el número real
                                const realNumber = contact.jid.replace('@s.whatsapp.net', '');
                                if (realNumber.match(/^\d+$/)) {
                                    console.log("✅ [SALIENTE] Número real encontrado:", realNumber);
                                    return formatRealPhoneNumber(realNumber);
                                }
                            }
                        }
                    } catch (contactError) {
                        console.log("⚠️ [SALIENTE] No se pudo obtener info de contacto:", contactError.message);
                    }
                }
                
                // Si el JID limpio parece un número de teléfono válido, úsalo
                if (cleanJid.match(/^57\d{10}$/)) {
                    console.log("📞 [SALIENTE] JID parece número colombiano válido");
                    return formatRealPhoneNumber(cleanJid);
                }
                
                // Para LIDs, intentar extraer número móvil colombiano antes de crear WA-ID
                if (jid.includes('@lid')) {
                    console.log("📞 [SALIENTE] Extrayendo solo números del JID:", cleanJid);
                    console.log("✅ [SALIENTE] Usando números extraídos:", cleanJid);
                    return formatRealPhoneNumber(cleanJid);
                }
                
                // Si no podemos determinar el número real, usar formato de ID único
                console.log("🆔 [SALIENTE] Usando formato de ID único para:", cleanJid);
                const formatted = cleanJid.match(/.{1,4}/g)?.join('-') || cleanJid;
                return `WA-${formatted}`;
                
            } catch (error) {
                console.error("❌ [SALIENTE] Error obteniendo número real:", error);
                const cleanJid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '');
                const formatted = cleanJid.match(/.{1,4}/g)?.join('-') || cleanJid;
                return `WA-${formatted}`;
            }
        };
        
        // Formatear número de teléfono real (usar la misma función)
        const formatRealPhoneNumber = (phoneNumber) => {
            console.log("📱 [SALIENTE] Formateando número real:", phoneNumber);
            
            // Remover cualquier carácter no numérico
            const cleanNumber = phoneNumber.replace(/\D/g, '');
            console.log("🔢 [SALIENTE] Número limpio (todos los dígitos):", cleanNumber);
            
            // Buscar específicamente números móviles colombianos (3 + 9 dígitos)
            const mobileMatch = cleanNumber.match(/(3\d{9})/);
            if (mobileMatch) {
                const mobile = mobileMatch[1];
                const formatted = `+57 ${mobile.substring(0, 3)} ${mobile.substring(3, 6)} ${mobile.substring(6)}`;
                console.log("🇨🇴 ✅ [SALIENTE] Móvil colombiano detectado en posición:", formatted);
                return formatted;
            }
            
            if (cleanNumber.startsWith('57') && cleanNumber.length === 12) {
                // Número colombiano: 573007341192 -> +57 300 734 1192
                const formatted = `+57 ${cleanNumber.substring(2, 5)} ${cleanNumber.substring(5, 8)} ${cleanNumber.substring(8)}`;
                console.log("🇨🇴 ✅ [SALIENTE] Número colombiano completo encontrado:", formatted);
                return formatted;
            } else if (cleanNumber.startsWith('1') && cleanNumber.length === 11) {
                // Número USA/Canadá: 15551234567 -> +1 555 123 4567
                const formatted = `+1 ${cleanNumber.substring(1, 4)} ${cleanNumber.substring(4, 7)} ${cleanNumber.substring(7)}`;
                console.log("🇺🇸 ✅ [SALIENTE] Número USA/Canadá formateado:", formatted);
                return formatted;
            } else if (cleanNumber.length >= 10) {
                console.log("🔍 [SALIENTE] Buscando patrón colombiano en:", cleanNumber);
                // Formato internacional genérico
                const countryCode = cleanNumber.substring(0, cleanNumber.length - 10);
                const number = cleanNumber.substring(cleanNumber.length - 10);
                const formatted = `+${countryCode}${number.substring(0, 3)} ${number.substring(3, 6)} ${number.substring(6)}`;
                console.log("🌍 [SALIENTE] Formato internacional genérico:", formatted);
                return formatted;
            }
            
            // Si no se puede formatear como número válido, crear WA-ID
            console.log("❓ [SALIENTE] No se pudo formatear como número válido, creando WA-ID");
            const waIdFormatted = cleanNumber.match(/.{1,4}/g)?.join('-') || cleanNumber;
            return `WA-${waIdFormatted}`;
        };

        // Obtener el número real del destinatario
        const realPhoneNumber = await getRealPhoneNumber(to, message);
        
        // Determinar número de origen basado en configuración
        // Para simplicidad, vamos a obtener del número del propio dispositivo conectado
        let fromNumber = 'unknown';
        try {
            if (sock && sock.user) {
                // Obtener el número del dispositivo actual (nuestro número)
                let ourNumber = sock.user.id.replace('@s.whatsapp.net', '').replace('@lid', '');
                
                // Limpiar sufijos como :0, :17, etc.
                ourNumber = ourNumber.split(':')[0];
                
                fromNumber = formatRealPhoneNumber(ourNumber);
                console.log('📱 [SALIENTE] Nuestro número detectado:', fromNumber);
            }
        } catch (error) {
            console.log('⚠️ [SALIENTE] No se pudo detectar número de origen:', error.message);
        }

        const webhookData = {
            to: realPhoneNumber,
            from: fromNumber,  // ← NUEVO: Número desde el que enviamos
            message_id: messageId,
            timestamp: timestamp,
            type: messageType,
            content: messageContent || 'Mensaje multimedia enviado',
            from_me: true  // Indicador importante para Django
        };

        console.log('📤 Mensaje saliente detectado:', webhookData);

        // Enviar a Django webhook para mensajes salientes
        try {
            await axios.post(`${DJANGO_BASE_URL}/webhooks/whatsapp-outgoing/`, webhookData);
            console.log('✅ Mensaje saliente notificado a Django');
        } catch (error) {
            console.error('❌ Error notificando mensaje saliente a Django:', error.message);
        }

    } catch (error) {
        console.error('❌ Error procesando mensaje saliente:', error);
    }
}

/**
 * ENDPOINTS HTTP
 */

// Estado de conexión
app.get('/status', (req, res) => {
    console.log('📊 Estado solicitado - isConnected:', isConnected, 'sock:', !!sock);
    res.json({
        connected: isConnected,
        hasQR: !!qrCodeData,
        timestamp: new Date().toISOString(),
        sockExists: !!sock,
        debug: {
            isConnectedVar: isConnected,
            qrCodeData: !!qrCodeData
        }
    });
});

// Obtener código QR
app.get('/qr', (req, res) => {
    if (qrCodeData) {
        res.json({
            qr: qrCodeData,
            timestamp: new Date().toISOString()
        });
    } else {
        res.status(404).json({
            error: 'No hay código QR disponible',
            connected: isConnected
        });
    }
});

// Enviar mensaje de texto
app.post('/send-message', async (req, res) => {
    try {
        if (!isConnected) {
            return res.status(400).json({
                success: false,
                error: 'WhatsApp no está conectado'
            });
        }

        const { to, message } = req.body;
        
        if (!to || !message) {
            return res.status(400).json({
                success: false,
                error: 'Faltan parámetros: to, message'
            });
        }

        // Normalizar número destino para evitar errores/tiempos de espera
        const normalizeTo = (raw) => {
            const str = String(raw || '').trim();
            if (str.includes('@')) return str; // ya es JID
            let digits = str.replace(/\D/g, '');
            if (!digits) return str;
            // Si es Colombia 10 dígitos -> anteponer 57
            if (digits.length === 10) digits = '57' + digits;
            // Aceptar 57xxxxxxxxxx (12) o 1xxxxxxxxxx (11) u otros >= 11
            if (digits.length < 11) return digits; // será rechazado abajo
            return digits;
        };

        const normalized = normalizeTo(to);
        if (!/^[0-9@.a-zA-Z_-]+$/.test(normalized) || (!normalized.includes('@') && normalized.length < 11)) {
            return res.status(400).json({ success: false, error: 'Número destino inválido' });
        }

        const jid = normalized.includes('@') ? normalized : `${normalized}@s.whatsapp.net`;
        
        // Enviar mensaje
        let result;
        try {
            // No esperar indefinidamente: responder como "queued" si tarda demasiado
            result = await withTimeout(sock.sendMessage(jid, { text: message }), 8000);
        } catch (err) {
            if (err && err.message === 'timeout') {
                const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
                console.log('⏱️ Envío tardando demasiado, respondiendo como queued:', { to: jid });
                return res.status(200).json({
                    success: true,
                    message_id: tempId,
                    timestamp: Math.floor(Date.now()/1000),
                    queued: true
                });
            }
            throw err;
        }
        
        console.log('📤 Mensaje enviado:', { to: jid, message });
        
        res.json({
            success: true,
            message_id: result.key.id,
            timestamp: result.messageTimestamp
        });

    } catch (error) {
        console.error('❌ Error enviando mensaje:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Enviar imagen
app.post('/send-image', async (req, res) => {
    try {
        if (!isConnected) {
            return res.status(400).json({
                success: false,
                error: 'WhatsApp no está conectado'
            });
        }

        const { to, image_url, caption } = req.body;
        
        if (!to || !image_url) {
            return res.status(400).json({
                success: false,
                error: 'Faltan parámetros: to, image_url'
            });
        }

        // Normalizar número destino
        const str = String(to || '').trim();
        let digits = str.includes('@') ? str : str.replace(/\D/g, '');
        if (!str.includes('@')) {
            if (digits.length === 10) digits = '57' + digits;
            if (digits.length < 11) {
                return res.status(400).json({ success: false, error: 'Número destino inválido' });
            }
        }
        const jid = str.includes('@') ? str : `${digits}@s.whatsapp.net`;
        
        let result;
        try {
            result = await withTimeout(sock.sendMessage(jid, {
                image: { url: image_url },
                caption: caption || ''
            }), 10000);
        } catch (err) {
            if (err && err.message === 'timeout') {
                const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
                console.log('⏱️ Envío de imagen tardando demasiado, respondiendo como queued:', { to: jid });
                return res.status(200).json({
                    success: true,
                    message_id: tempId,
                    timestamp: Math.floor(Date.now()/1000),
                    queued: true
                });
            }
            throw err;
        }
        
        console.log('📤 Imagen enviada:', { to: jid, image_url, caption });
        
        res.json({
            success: true,
            message_id: result.key.id,
            timestamp: result.messageTimestamp
        });

    } catch (error) {
        console.error('❌ Error enviando imagen:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Reiniciar conexión
app.post('/restart', async (req, res) => {
    try {
        if (sock) {
            sock.end();
        }
        
        setTimeout(() => {
            initializeWhatsApp();
        }, 2000);
        
        res.json({
            success: true,
            message: 'Reiniciando conexión de WhatsApp'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Iniciar servidor
app.listen(PORT, () => {
    console.log(`🚀 WhatsApp Bridge ejecutándose en puerto ${PORT}`);
    console.log(`📱 Inicializando conexión de WhatsApp...`);
    
    // Inicializar WhatsApp
    initializeWhatsApp();
});

// Manejar cierre graceful
process.on('SIGINT', () => {
    console.log('🛑 Cerrando WhatsApp Bridge...');
    if (sock) {
        sock.end();
    }
    process.exit(0);
});