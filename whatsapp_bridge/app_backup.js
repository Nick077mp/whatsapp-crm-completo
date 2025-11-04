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

// ==================== FUNCIONES AUXILIARES GLOBALES ====================

// Actualizar mapeo JID en Django
const updateJidMapping = async (jid, pushName, phoneNumber, needsManualReview = false) => {
    try {
        await axios.post(`${DJANGO_BASE_URL}/api/update-jid-mapping/`, {
            jid: jid,
            push_name: pushName,
            phone_number: phoneNumber,
            needs_manual_review: needsManualReview
        });
        console.log("📝 Mapeo JID actualizado:", jid, "->", phoneNumber);
    } catch (error) {
        console.log("⚠️ Error actualizando mapeo JID:", error.message);
    }
};

// Extraer número de teléfono desde pushName
const extractPhoneFromPushName = (pushName) => {
    if (!pushName) return null;
    
    // Patrones para números en pushName
    const patterns = [
        /(\+57\s*3\d{2}\s*\d{3}\s*\d{4})/,  // +57 3XX XXX XXXX
        /(\+57\s*\d{3}\s*\d{3}\s*\d{4})/,   // +57 XXX XXX XXXX
        /(57\s*3\d{9})/,                     // 57 3XXXXXXXXX
        /(3\d{9})/                           // 3XXXXXXXXX
    ];
    
    for (const pattern of patterns) {
        const match = pushName.match(pattern);
        if (match) {
            let number = match[1].replace(/\D/g, '');
            if (number.length === 10 && number.startsWith('3')) {
                return formatRealPhoneNumber('57' + number);
            } else if (number.length === 12 && number.startsWith('573')) {
                return formatRealPhoneNumber(number);
            }
        }
    }
    return null;
};

// Formatear número de teléfono real
const formatRealPhoneNumber = (phoneNumber) => {
    console.log("📱 Formateando número real:", phoneNumber);
    
    // Remover cualquier carácter no numérico
    const cleanNumber = phoneNumber.replace(/\D/g, '');
    
    if (cleanNumber.startsWith('57') && cleanNumber.length === 12) {
        // Número colombiano: 573007341192 -> +57 300 734 1192
        const formatted = `+57 ${cleanNumber.substring(2, 5)} ${cleanNumber.substring(5, 8)} ${cleanNumber.substring(8)}`;
        console.log("🇨🇴 Número colombiano formateado:", formatted);
        return formatted;
    } else if (cleanNumber.startsWith('1') && cleanNumber.length === 11) {
        // Número USA/Canadá: 15551234567 -> +1 555 123 4567
        const formatted = `+1 ${cleanNumber.substring(1, 4)} ${cleanNumber.substring(4, 7)} ${cleanNumber.substring(7)}`;
        console.log("🇺🇸 Número USA/Canadá formateado:", formatted);
        return formatted;
    } else if (cleanNumber.length === 10) {
        // Número de 10 dígitos (asume Colombia): 3007341192 -> +57 300 734 1192
        const formatted = `+57 ${cleanNumber.substring(0, 3)} ${cleanNumber.substring(3, 6)} ${cleanNumber.substring(6)}`;
        console.log("🇨🇴 Número colombiano (10 dígitos) formateado:", formatted);
        return formatted;
    }
    
    // Si no se puede formatear, devolver tal como está
    return phoneNumber;
};

// ==================== FIN FUNCIONES AUXILIARES ====================

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
        // Intentar obtener el número real del contacto con mapeo JID
        const getRealPhoneNumber = async (jid, message) => {
            try {
                console.log("🔥 [ENTRANTE] MODO DEFINITIVO: Usando WA-ID único para:", jid);
                
                // Limpiar JID
                const cleanJid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '');
                
                // 🔥 SIEMPRE usar WA-ID único - NO resolver números reales
                const uniqueId = `WA-${cleanJid}`;
                
                console.log("🆔 [ENTRANTE] ID único definitivo:", uniqueId);
                
                // Obtener número real solo para información adicional (no para identificación)
                let realNumberInfo = null;
                try {
                    // Intentar detectar número real solo como información
                    if (cleanJid.match(/^57\d{10}$/)) {
                        realNumberInfo = formatRealPhoneNumber(cleanJid);
                        console.log("📱 [ENTRANTE] Número real detectado (solo info):", realNumberInfo);
                    } else if (sock && sock.onWhatsApp) {
                        const contactInfo = await sock.onWhatsApp(jid);
                        if (contactInfo && contactInfo.length > 0) {
                            const contact = contactInfo[0];
                            if (contact.jid && contact.jid !== jid) {
                                const realNumber = contact.jid.replace('@s.whatsapp.net', '');
                                if (realNumber.match(/^\d+$/)) {
                                    realNumberInfo = formatRealPhoneNumber(realNumber);
                                    console.log("📱 [ENTRANTE] Número real resuelto (solo info):", realNumberInfo);
                                }
                            }
                        }
                    }
                    
                    // También intentar extraer de pushName si existe
                    if (message.pushName || message.notifyName) {
                        const pushName = message.pushName || message.notifyName;
                        const extractedNumber = extractPhoneFromPushName(pushName);
                        if (extractedNumber && !realNumberInfo) {
                            realNumberInfo = extractedNumber;
                            console.log("📱 [ENTRANTE] Número extraído de pushName (solo info):", realNumberInfo);
                        }
                    }
                } catch (infoError) {
                    console.log("⚠️ [ENTRANTE] No se pudo obtener info del número real:", infoError.message);
                }
                
                // Registrar mapeo con número real como información adicional
                await updateJidMapping(jid, message?.pushName || message?.notifyName || null, uniqueId, false, realNumberInfo);
                
                return uniqueId;
                
            } catch (error) {
                console.error("❌ [ENTRANTE] Error obteniendo identificador:", error);
                // Fallback: usar JID limpio como identificador único
                const cleanJid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '');
                const uniqueId = `WA-${cleanJid}`;
                console.log("🆔 [ENTRANTE] Fallback definitivo:", uniqueId);
                return uniqueId;
            }
        };

        sock.ev.on('messages.upsert', async (m) => {
            try {
                try {
                    const mappingResponse = await axios.post(`${DJANGO_BASE_URL}/api/resolve-jid/`, {
                        jid: jid,
                        clean_jid: cleanJid,
                        push_name: message.pushName || message.notifyName
                    });
                    
                    if (mappingResponse.data.success && mappingResponse.data.phone_number) {
                        console.log("✅ Número resuelto desde mapeo JID:", mappingResponse.data.phone_number);
                        return mappingResponse.data.phone_number;
                    }
                } catch (mappingError) {
                    console.log("⚠️ Error consultando mapeo JID:", mappingError.message);
                }
                
                // PASO 2: Intentar resolver con WhatsApp API
                if (sock && sock.onWhatsApp) {
                    try {
                        const contactInfo = await sock.onWhatsApp(jid);
                        console.log("📋 Info de contacto:", contactInfo);
                        
                        if (contactInfo && contactInfo.length > 0) {
                            const contact = contactInfo[0];
                            if (contact.jid && contact.jid !== jid) {
                                const realNumber = contact.jid.replace('@s.whatsapp.net', '');
                                if (realNumber.match(/^\d+$/)) {
                                    const formattedNumber = formatRealPhoneNumber(realNumber);
                                    console.log("✅ Número real encontrado:", formattedNumber);
                                    
                                    // Actualizar mapeo JID para futura referencia
                                    await updateJidMapping(jid, message.pushName, formattedNumber);
                                    return formattedNumber;
                                }
                            }
                        }
                    } catch (contactError) {
                        console.log("⚠️ No se pudo obtener info de contacto:", contactError.message);
                    }
                }
                
                // PASO 3: Si el JID limpio parece un número válido
                if (cleanJid.match(/^57\d{10}$/)) {
                    console.log("📞 JID parece número colombiano válido");
                    const formattedNumber = formatRealPhoneNumber(cleanJid);
                    await updateJidMapping(jid, message.pushName, formattedNumber);
                    return formattedNumber;
                }
                
                if (cleanJid.match(/^1\d{10}$/)) {
                    console.log("📞 JID parece número USA válido");
                    const formattedNumber = formatRealPhoneNumber(cleanJid);
                    await updateJidMapping(jid, message.pushName, formattedNumber);
                    return formattedNumber;
                }
                
                // PASO 3.5: Intentar extraer número de JIDs complejos
                // Buscar patrones de números dentro del JID
                const numberMatches = cleanJid.match(/(\d{10,12})/g);
                if (numberMatches) {
                    for (const match of numberMatches) {
                        // Número colombiano de 12 dígitos (57XXXXXXXXXX)
                        if (match.length === 12 && match.startsWith('57')) {
                            console.log("📞 Número colombiano encontrado en JID complejo");
                            const formattedNumber = formatRealPhoneNumber(match);
                            await updateJidMapping(jid, message.pushName, formattedNumber);
                            return formattedNumber;
                        }
                        // Número colombiano de 10 dígitos (XXXXXXXXXX)
                        if (match.length === 10 && match.startsWith('3')) {
                            console.log("📞 Número móvil colombiano encontrado en JID");
                            const formattedNumber = formatRealPhoneNumber('57' + match);
                            await updateJidMapping(jid, message.pushName, formattedNumber);
                            return formattedNumber;
                        }
                    }
                }
                
                // PASO 4: Analizar pushName para extraer número
                if (message.pushName || message.notifyName) {
                    const pushName = message.pushName || message.notifyName;
                    console.log("👤 Verificando pushName:", pushName);
                    
                    const extractedNumber = extractPhoneFromPushName(pushName);
                    if (extractedNumber) {
                        console.log("📞 Número extraído de pushName:", extractedNumber);
                        await updateJidMapping(jid, pushName, extractedNumber);
                        return extractedNumber;
                    }
                }
                
                // PASO 5: Como último recurso, usar el JID limpio como identificador único
                console.log("🆔 No se pudo determinar número real para:", cleanJid);
                console.log("📱 Usando JID limpio como identificador único");
                
                // Crear un identificador único basado en el JID
                const uniqueId = `WA-${cleanJid}`;
                
                // Registrar en mapeo para seguimiento
                await updateJidMapping(jid, message.pushName, uniqueId, true);
                return uniqueId;
                
            } catch (error) {
                console.error("❌ Error obteniendo número real:", error);
                // Fallback: usar JID limpio como identificador único
                const cleanJid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '');
                const uniqueId = `WA-${cleanJid}`;
                console.log("🆔 Fallback de error, usando:", uniqueId);
                return uniqueId;
            }
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

        // 🔥 SOLUCIÓN DEFINITIVA: SIEMPRE usar WA-ID único, nunca resolver números reales
        const getConsistentContactId = async (jid, message) => {
            try {
                console.log("� [SALIENTE] MODO DEFINITIVO: Usando WA-ID único para:", jid);
                
                // Limpiar JID
                const cleanJid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '');
                
                // 🔥 SIEMPRE usar WA-ID único - NO resolver números reales
                const uniqueId = `WA-${cleanJid}`;
                
                console.log("🆔 [SALIENTE] ID único definitivo:", uniqueId);
                
                // Obtener número real solo para información adicional (no para identificación)
                let realNumberInfo = null;
                try {
                    if (cleanJid.match(/^57\d{10}$/)) {
                        realNumberInfo = formatRealPhoneNumber(cleanJid);
                        console.log("📱 [SALIENTE] Número real detectado (solo info):", realNumberInfo);
                    } else if (sock && sock.onWhatsApp) {
                        const contactInfo = await sock.onWhatsApp(jid);
                        if (contactInfo && contactInfo.length > 0) {
                            const contact = contactInfo[0];
                            if (contact.jid && contact.jid !== jid) {
                                const realNumber = contact.jid.replace('@s.whatsapp.net', '');
                                if (realNumber.match(/^\d+$/)) {
                                    realNumberInfo = formatRealPhoneNumber(realNumber);
                                    console.log("📱 [SALIENTE] Número real resuelto (solo info):", realNumberInfo);
                                }
                            }
                        }
                    }
                } catch (infoError) {
                    console.log("⚠️ [SALIENTE] No se pudo obtener info del número real:", infoError.message);
                }
                
                // Registrar mapeo con número real como información adicional
                await updateJidMapping(jid, message?.pushName || null, uniqueId, false, realNumberInfo);
                
                return uniqueId;
                
            } catch (error) {
                console.error("❌ [SALIENTE] Error obteniendo identificador:", error);
                // Fallback: usar JID limpio como identificador único
                const cleanJid = jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@c.us', '');
                const uniqueId = `WA-${cleanJid}`;
                console.log("🆔 [SALIENTE] Fallback definitivo:", uniqueId);
                return uniqueId;
            }
        };
        


        // ⭐ Obtener el identificador consistente del destinatario (igual que mensajes entrantes)
        const consistentContactId = await getConsistentContactId(to, message);
        
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
            to: consistentContactId,  // ⭐ Usar el mismo identificador que mensajes entrantes
            from: fromNumber,  // Número desde el que enviamos
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
    res.json({
        connected: isConnected,
        hasQR: !!qrCodeData,
        timestamp: new Date().toISOString()
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