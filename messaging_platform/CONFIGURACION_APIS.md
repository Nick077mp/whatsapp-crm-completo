# Guía de Configuración de APIs de Mensajería

Este documento proporciona instrucciones detalladas para configurar las credenciales de las APIs de WhatsApp Business, Facebook Messenger y Telegram en la aplicación.

## WhatsApp Business API

### Requisitos Previos

- Una cuenta de Meta Business
- Acceso a la plataforma Meta for Developers
- Una aplicación de WhatsApp Business configurada

### Obtener Credenciales

1. Ve a [Meta for Developers](https://developers.facebook.com/)
2. Selecciona tu aplicación o crea una nueva
3. Agrega el producto "WhatsApp"
4. En la sección de WhatsApp, encontrarás:
   - **Phone Number ID**: ID del número de teléfono de WhatsApp Business
   - **WhatsApp Business Account ID**: ID de tu cuenta de negocio
   - **Access Token**: Token de acceso temporal o permanente

### Configurar Webhook

1. En la configuración de WhatsApp, ve a "Configuration"
2. Configura la URL del webhook: `https://tu-dominio.com/webhooks/whatsapp/`
3. Genera un **Verify Token** (cualquier cadena segura que elijas)
4. Suscríbete a los eventos: `messages`

### Ingresar Credenciales en la Aplicación

1. Inicia sesión en el panel de administración: `http://tu-dominio.com/admin/`
2. Ve a **Core** > **Api Configurations**
3. Selecciona la configuración de **whatsapp**
4. Completa los campos:
   - **Whatsapp phone number id**: El Phone Number ID obtenido
   - **Whatsapp business account id**: El WhatsApp Business Account ID
   - **Whatsapp access token**: El Access Token generado
   - **Whatsapp webhook verify token**: El Verify Token que creaste
5. Marca como **Is active** y guarda

---

## Facebook Messenger API

### Requisitos Previos

- Una página de Facebook
- Una aplicación en Meta for Developers
- Permisos de administrador en la página

### Obtener Credenciales

1. Ve a [Meta for Developers](https://developers.facebook.com/)
2. Selecciona tu aplicación
3. Agrega el producto "Messenger"
4. En la sección de Messenger:
   - **Page ID**: ID de tu página de Facebook
   - **Page Access Token**: Token de acceso de la página
   - **App Secret**: Secreto de la aplicación (en Settings > Basic)

### Configurar Webhook

1. En la configuración de Messenger, ve a "Webhooks"
2. Configura la URL del webhook: `https://tu-dominio.com/webhooks/facebook/`
3. Genera un **Verify Token** (cualquier cadena segura)
4. Suscríbete a los eventos: `messages`, `messaging_postbacks`, `message_reads`

### Ingresar Credenciales en la Aplicación

1. Inicia sesión en el panel de administración
2. Ve a **Core** > **Api Configurations**
3. Selecciona la configuración de **facebook**
4. Completa los campos:
   - **Facebook page id**: El Page ID
   - **Facebook page access token**: El Page Access Token
   - **Facebook app secret**: El App Secret
   - **Facebook verify token**: El Verify Token que creaste
5. Marca como **Is active** y guarda

---

## Telegram Bot API

### Requisitos Previos

- Una cuenta de Telegram

### Crear un Bot y Obtener Credenciales

1. Abre Telegram y busca [@BotFather](https://t.me/botfather)
2. Envía el comando `/newbot`
3. Sigue las instrucciones para crear tu bot
4. BotFather te proporcionará un **Bot Token** (ej: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Configurar Webhook

Puedes configurar el webhook de dos formas:

#### Opción 1: Desde la aplicación (recomendado)

Una vez que hayas ingresado el Bot Token en la configuración, puedes usar el siguiente comando para configurar el webhook automáticamente:

```python
from core.services.telegram_service import TelegramService
service = TelegramService()
result = service.set_webhook('https://tu-dominio.com/webhooks/telegram/')
print(result)
```

#### Opción 2: Manualmente con cURL

```bash
curl -X POST "https://api.telegram.org/bot<TU_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://tu-dominio.com/webhooks/telegram/"}'
```

### Ingresar Credenciales en la Aplicación

1. Inicia sesión en el panel de administración
2. Ve a **Core** > **Api Configurations**
3. Selecciona la configuración de **telegram**
4. Completa los campos:
   - **Telegram bot token**: El Bot Token proporcionado por BotFather
   - **Telegram webhook url**: `https://tu-dominio.com/webhooks/telegram/`
5. Marca como **Is active** y guarda

---

## Verificación de Configuración

### Probar WhatsApp

Envía un mensaje al número de WhatsApp Business configurado. Deberías ver la conversación aparecer en la aplicación.

### Probar Facebook Messenger

Envía un mensaje a tu página de Facebook desde Messenger. La conversación debería aparecer en la aplicación.

### Probar Telegram

Busca tu bot en Telegram y envíale un mensaje con `/start`. La conversación debería aparecer en la aplicación.

---

## Solución de Problemas

### Los webhooks no reciben mensajes

1. Verifica que las URLs de webhook sean accesibles públicamente (usa HTTPS)
2. Revisa los logs de Django para ver si hay errores
3. Verifica que los tokens de verificación coincidan
4. Asegúrate de que las configuraciones estén marcadas como **Is active**

### Error de autenticación

1. Verifica que los tokens no hayan expirado
2. Regenera los tokens si es necesario
3. Asegúrate de que los permisos de la aplicación sean correctos

### Los mensajes no se envían

1. Verifica que tengas permisos para enviar mensajes en la plataforma
2. Revisa los límites de tasa de la API
3. Verifica que el formato del mensaje sea correcto

---

## Seguridad

- **Nunca compartas tus tokens públicamente**
- Usa variables de entorno para almacenar credenciales sensibles en producción
- Regenera los tokens periódicamente
- Implementa rate limiting en tus endpoints
- Usa HTTPS para todas las comunicaciones

---

## Recursos Adicionales

- [Documentación de WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
- [Documentación de Facebook Messenger API](https://developers.facebook.com/docs/messenger-platform)
- [Documentación de Telegram Bot API](https://core.telegram.org/bots/api)

