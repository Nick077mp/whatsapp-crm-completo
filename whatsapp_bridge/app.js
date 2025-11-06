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
const DJANGO_BASE_URL = 'http://172.27.32.23:8000';

// Directorio para archivos multimedia temporales
const MEDIA_DIR = path.join(__dirname, 'media');

// Asegurar que exista el directorio de media
fs.ensureDirSync(MEDIA_DIR);

/**
 * REINGENIERÍA COMPLETA - Solo números reales colombianos @s.whatsapp.net
 * NO más LIDs, NO más WA-IDs, NO más duplicaciones
 */

/**
 * SOPORTE INTERNACIONAL COMPLETO
 */
const INTERNATIONAL_COUNTRIES = {
    '1': { name: 'USA/Canadá', length: 11 },
    '52': { name: 'México', length: 12 },
    '57': { name: 'Colombia', length: 12 },
    '58': { name: 'Venezuela', length: 12 },
    '54': { name: 'Argentina', length: 13 },
    '55': { name: 'Brasil', length: 13 },
    '56': { name: 'Chile', length: 11 },
    '51': { name: 'Perú', length: 11 },
    '593': { name: 'Ecuador', length: 12 },
    '507': { name: 'Panamá', length: 11 },
    '34': { name: 'España', length: 11 },
    '33': { name: 'Francia', length: 12 },
    '44': { name: 'Reino Unido', length: 13 },
    '49': { name: 'Alemania', length: 13 },
    '39': { name: 'Italia', length: 13 },
};

/**
 * Detectar código de país de un número
 */
function detectCountryCode(cleanNumber) {
    // Probar códigos de 3 dígitos primero, luego 2, luego 1
    const codes = Object.keys(INTERNATIONAL_COUNTRIES).sort((a, b) => b.length - a.length);
    
    for (const code of codes) {
        if (cleanNumber.startsWith(code)) {
            return code;
        }
    }
    return null;
}

/**
 * Formatear número internacional según su país
 */
function formatInternationalNumber(rawNumber) {
    console.log("� Formateando número internacional:", rawNumber);
    
    // Limpiar número (solo dígitos)
    const cleanNumber = rawNumber.replace(/\D/g, '');
    
    if (cleanNumber.length < 10) {
        throw new Error(`Número muy corto: ${rawNumber}`);
    }
    
    // Detectar código de país
    const countryCode = detectCountryCode(cleanNumber);
    if (!countryCode) {
        throw new Error(`Código de país no reconocido: ${rawNumber}`);
    }
    
    const countryInfo = INTERNATIONAL_COUNTRIES[countryCode];
    
    // Validar longitud (permitir ±1 dígito de variación)
    if (cleanNumber.length < countryInfo.length - 1 || cleanNumber.length > countryInfo.length + 1) {
        console.warn(`⚠️ Longitud no estándar para ${countryInfo.name}: ${cleanNumber.length} vs ${countryInfo.length} esperada`);
    }
    
    // Formatear según el país
    const formatted = formatByCountry(cleanNumber, countryCode);
    console.log(`✅ Número ${countryInfo.name} formateado:`, formatted);
    return formatted;
}

/**
 * Aplicar formato específico por país
 */
function formatByCountry(cleanNumber, countryCode) {
    switch (countryCode) {
        case '1': // USA/Canadá
            return `+1 ${cleanNumber.substring(1, 4)} ${cleanNumber.substring(4, 7)} ${cleanNumber.substring(7, 11)}`;
        
        case '52': // México
            return `+52 ${cleanNumber.substring(2, 4)} ${cleanNumber.substring(4, 8)} ${cleanNumber.substring(8, 12)}`;
        
        case '57': // Colombia
            return `+57 ${cleanNumber.substring(2, 5)} ${cleanNumber.substring(5, 8)} ${cleanNumber.substring(8, 12)}`;
        
        case '44': // Reino Unido
            return `+44 ${cleanNumber.substring(2, 6)} ${cleanNumber.substring(6, 12)}`;
        
        case '34': // España
            return `+34 ${cleanNumber.substring(2, 5)} ${cleanNumber.substring(5, 8)} ${cleanNumber.substring(8, 11)}`;
        
        case '51': // Perú
            return `+51 ${cleanNumber.substring(2, 5)} ${cleanNumber.substring(5, 8)} ${cleanNumber.substring(8, 11)}`;
        
        case '507': // Panamá
            return `+507 ${cleanNumber.substring(3, 7)} ${cleanNumber.substring(7, 11)}`;
        
        default:
            // Formato genérico
            const rest = cleanNumber.substring(countryCode.length);
            if (rest.length >= 6) {
                const mid = Math.floor(rest.length / 2);
                return `+${countryCode} ${rest.substring(0, mid)} ${rest.substring(mid)}`;
            } else {
                return `+${countryCode} ${rest}`;
            }
    }
}

/**
 * Formatear números (ACTUALIZADO CON SOPORTE INTERNACIONAL)
 */
function formatColombianNumber(rawNumber) {
    console.log("📱 Formateando número (internacional):", rawNumber);
    
    try {
        // Intentar formateo internacional primero
        return formatInternationalNumber(rawNumber);
    } catch (error) {
        console.warn("⚠️ Formateo internacional falló, usando formato legacy:", error.message);
        
        // Fallback al formato original colombiano
        const digits = rawNumber.replace(/\D/g, '');
        
        if (digits.startsWith('57') && digits.length === 12) {
            const formatted = `+57 ${digits.substring(2, 5)} ${digits.substring(5, 8)} ${digits.substring(8)}`;
            console.log("✅ Número colombiano formateado:", formatted);
            return formatted;
        }
        
        throw new Error(`Número no válido: ${rawNumber}`);
    }
}

/**
 * Funciones utilitarias para manejar JIDs y LIDs
 */
function isLidUser(jid) {
    return jid && jid.includes('@lid');
}

function isJidUser(jid) {
    return jid && jid.includes('@s.whatsapp.net');
}

function isGroupJid(jid) {
    return jid && jid.includes('@g.us');
}

/**
 * Validar JID (acepta tanto LIDs como JIDs estándar) y extraer información de contacto
 */
function validateAndExtractNumber(jid, remoteJidAlt = null) {
    console.log("🔍 VALIDANDO JID:", jid);
    console.log("🔍 remoteJidAlt:", remoteJidAlt);
    console.log("🔍 isLidUser:", isLidUser(jid));
    console.log("🔍 isJidUser:", isJidUser(jid));
    console.log("🔍 JID incluye @g.us:", jid.includes('@g.us'));
    
    // ✅ ACTUALIZADO: Acepta tanto LIDs como JIDs estándar y grupos
    if (!(isLidUser(jid) || isJidUser(jid) || isGroupJid(jid))) {
        console.log(`❌ JID RECHAZADO: ${jid} - Motivo: Formato no soportado`);
        throw new Error(`JID rechazado - Formato no válido: ${jid}`);
    }
    
    // 🔍 EXTRAER NÚMERO REAL - Para LIDs, usar remoteJidAlt
    console.log("📞 EXTRAYENDO NÚMERO REAL - JID:", jid);
    console.log("📞 EXTRAYENDO NÚMERO REAL - remoteJidAlt:", remoteJidAlt);
    
    let extractedNumber = null;
    let sendToJid = null;
    
    if (remoteJidAlt && !remoteJidAlt.includes('@lid')) {
        // Para LIDs, el número real está en remoteJidAlt
        extractedNumber = remoteJidAlt.replace('@s.whatsapp.net', '');
        sendToJid = remoteJidAlt;
        console.log("✅ Número extraído de remoteJidAlt:", extractedNumber);
    } else if (isJidUser(jid)) {
        // Para JIDs tradicionales, extraer directamente
        extractedNumber = jid.replace('@s.whatsapp.net', '');
        sendToJid = jid;
        console.log("✅ Número extraído del JID principal:", extractedNumber);
    } else if (isLidUser(jid)) {
        // LID sin remoteJidAlt válido - usar LID como contactId
        console.log("⚠️ LID sin remoteJidAlt válido, usando LID como identificador");
        return {
            phoneNumber: null,
            contactId: jid,
            sendToJid: jid,
            isLid: true,
            isGroup: false
        };
    }
    
    if (!extractedNumber) {
        throw new Error(`No se pudo extraer número del JID: ${jid}`);
    }
    
    // Formatear número usando el sistema internacional completo
    let formattedNumber = null;
    if (extractedNumber.length >= 10 && extractedNumber.length <= 15) {
        try {
            formattedNumber = formatColombianNumber(extractedNumber);
            console.log("📞 Número internacional extraído:", formattedNumber);
        } catch (error) {
            console.warn("⚠️ No se pudo formatear como número internacional:", error.message);
            // Fallback básico
            formattedNumber = `+${extractedNumber}`;
            console.log("📞 Número básico extraído:", formattedNumber);
        }
    }

    // Usar número formateado como contactId si está disponible
    const contactId = formattedNumber || extractedNumber;
    console.log("🆔 Contact ID asignado:", contactId);
    
    return {
        phoneNumber: formattedNumber,
        contactId: contactId,
        sendToJid: sendToJid,
        isLid: isLidUser(jid),
        isGroup: isGroupJid(jid)
    };
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
                        
                        // Validar y procesar JID (acepta LIDs y JIDs)
                        const remoteJidAlt = message.key.remoteJidAlt;
                        const contactInfo = validateAndExtractNumber(cleanJid, remoteJidAlt);
                        
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
                            to: contactInfo.phoneNumber || contactInfo.contactId, // Usar número si está disponible, sino usar contactId
                            contact_id: contactInfo.contactId, // LID/JID normalizado como ID principal
                            phone_number: contactInfo.phoneNumber, // Número real si está disponible
                            from: '+57 302 2620031',
                            message_id: messageId,
                            timestamp: Math.floor(timestamp / 1000),
                            type: messageType,
                            content: messageContent,
                            from_me: true,
                            is_lid: contactInfo.isLid
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
                    
                    // ✅ CRÍTICO: Extraer remoteJidAlt que contiene el número real para envío
                    const remoteJidAlt = message.key.remoteJidAlt;
                    const participantPn = (message.key).participantPn ?? message.participantPn ?? null;
                    
                    // VALIDACIÓN ACTUALIZADA: Acepta tanto LIDs como JIDs estándar
                    const contactInfo = validateAndExtractNumber(from, remoteJidAlt);
                    
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
                    
                    console.log("🎯 NÚMERO REAL PARA ENVÍO detectado en remoteJidAlt:", contactInfo.sendToJid);
                    
                    const webhookData = {
                        from: contactInfo.phoneNumber || contactInfo.contactId, // Usar número si está disponible, sino contactId
                        contact_id: contactInfo.contactId, // LID/JID normalizado como ID principal
                        phone_number: contactInfo.phoneNumber, // Número real si está disponible
                        send_to_jid: contactInfo.sendToJid, // ✅ JID REAL para envío de respuestas
                        remote_jid_alt: remoteJidAlt, // JID alternativo (número real)
                        participant_pn: participantPn, // Número de participante si está disponible
                        received_at: '+57 302 2620031', // Número fijo del negocio
                        message_id: messageId,
                        timestamp: timestamp,
                        type: mediaInfo.messageType,
                        content: textContent || mediaInfo.content,
                        media_url: mediaInfo.mediaUrl,
                        is_lid: contactInfo.isLid,
                        is_group: contactInfo.isGroup,
                        original_jid: from
                    };
                    
                    console.log("📨 Mensaje procesado:", webhookData);
                    
                    // **CACHE: Guardar mensaje para referencia futura en mensajes salientes**
                    const cacheKey = `${messageId}`;
                    recentMessagesCache.set(cacheKey, {
                        content: textContent || mediaInfo.content,
                        type: mediaInfo.messageType,
                        timestamp: timestamp,
                        contactId: contactInfo.contactId,
                        phoneNumber: contactInfo.phoneNumber
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
                        
                        // VALIDACIÓN: Procesar JIDs válidos (LIDs y JIDs estándar)
                        const contactInfo = validateAndExtractNumber(cleanJid);
                        
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
                            to: contactInfo.phoneNumber || contactInfo.contactId,
                            contact_id: contactInfo.contactId,
                            phone_number: contactInfo.phoneNumber,
                            from: '+57 302 2620031',
                            message_id: messageId,
                            timestamp: Math.floor(timestamp / 1000),
                            type: messageType,
                            content: messageContent,
                            from_me: true,
                            is_lid: contactInfo.isLid
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
        const { to, message = '', type = 'text', media_url, filename } = req.body;
        
        if (!to) {
            return res.status(400).json({
                success: false,
                error: 'Falta parámetro: to'
            });
        }
        
        // Para multimedia, el message puede estar vacío
        if (type === 'text' && !message) {
            return res.status(400).json({
                success: false,
                error: 'Para mensajes de texto se requiere el parámetro message'
            });
        }
        
        if (!isConnected || !sock) {
            return res.status(500).json({
                success: false,
                error: 'WhatsApp no está conectado'
            });
        }
        
        // Normalizar número para envío (CON SOPORTE INTERNACIONAL)
        let targetJid;
        if (to.includes('@')) {
            targetJid = to;
        } else {
            // Convertir número formateado a JID - ahora con soporte internacional
            const cleanNumber = to.replace(/\D/g, '');
            
            // Validar longitud mínima y máxima para números internacionales
            if (cleanNumber.length >= 10 && cleanNumber.length <= 15) {
                // Verificar si es un código de país reconocido
                const countryCode = detectCountryCode(cleanNumber);
                if (countryCode && INTERNATIONAL_COUNTRIES[countryCode]) {
                    targetJid = `${cleanNumber}@s.whatsapp.net`;
                    console.log(`✅ Número ${INTERNATIONAL_COUNTRIES[countryCode].name} válido para envío: ${targetJid}`);
                } else {
                    // Fallback para números no reconocidos pero con longitud válida
                    targetJid = `${cleanNumber}@s.whatsapp.net`;
                    console.log(`⚠️ Número internacional no reconocido, enviando de todos modos: ${targetJid}`);
                }
            } else {
                throw new Error('Número no válido para envío: longitud incorrecta');
            }
        }
        
        console.log("📤 Enviando mensaje:", { to: targetJid, message, type, media_url });
        
        let sentMessage;
        
        // Enviar según el tipo de mensaje
        if (type === 'text') {
            // Mensaje de texto simple
            sentMessage = await sock.sendMessage(targetJid, { text: message });
        } else if (media_url) {
            // Mensaje multimedia
            console.log(`📎 Enviando ${type} desde URL: ${media_url}`);
            
            try {
                // Descargar el archivo desde la URL
                const axios = require('axios');
                console.log(`🌐 Descargando archivo desde: ${media_url}`);
                const response = await axios.get(media_url, { responseType: 'arraybuffer' });
                const mediaBuffer = Buffer.from(response.data);
                console.log(`📦 Archivo descargado, tamaño: ${mediaBuffer.length} bytes`);
                
                // Preparar mensaje multimedia según el tipo
                let messageContent;
                
                if (type === 'image') {
                    messageContent = {
                        image: mediaBuffer,
                        caption: message,
                        fileName: filename || 'image.jpg'
                    };
                } else if (type === 'video') {
                    messageContent = {
                        video: mediaBuffer,
                        caption: message,
                        fileName: filename || 'video.mp4'
                    };
                } else if (type === 'audio') {
                    messageContent = {
                        audio: mediaBuffer,
                        fileName: filename || 'audio.mp3'
                    };
                } else if (type === 'document') {
                    messageContent = {
                        document: mediaBuffer,
                        fileName: filename || 'document.pdf',
                        caption: message
                    };
                } else {
                    throw new Error(`Tipo de multimedia no soportado: ${type}`);
                }
                
                console.log(`📤 Enviando ${type} a ${targetJid}`);
                sentMessage = await sock.sendMessage(targetJid, messageContent);
                
            } catch (mediaError) {
                console.error(`❌ Error procesando multimedia:`, mediaError);
                throw new Error(`Error procesando archivo multimedia: ${mediaError.message}`);
            }
        } else {
            throw new Error('Para mensajes multimedia se requiere media_url');
        }
        
        console.log(`✅ Mensaje ${type} enviado exitosamente:`, sentMessage.key.id);
        
        res.json({
            success: true,
            message_id: sentMessage.key.id,
            target: targetJid,
            type: type
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