# Integración Google Contacts API

## Resumen
Esta integración permite que cuando un cliente contacte por WhatsApp, el sistema busque automáticamente el número en Google Contacts y muestre el nombre real del contacto en lugar del número telefónico.

## Configuración en Google Console

### 1. Crear Proyecto OAuth 2.0

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la API de Google People (Contacts API)

### 2. Configurar OAuth 2.0

En la consola de Google, ve a **APIs & Services > Credentials**:

**Tipo de aplicación:** Aplicación web

**Nombre:** Cliente web para WhatsApp CRM (o el nombre que prefieras)

**Orígenes autorizados de JavaScript:**
```
http://localhost:8000
http://127.0.0.1:8000
http://192.168.1.176:8000
https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer
```

**URIs de redireccionamiento autorizados:**
```
http://localhost:8000/auth/google/callback/
http://127.0.0.1:8000/auth/google/callback/
http://192.168.1.176:8000/auth/google/callback/
https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/auth/google/callback/
```

### 3. Obtener Credenciales

1. Descarga el archivo JSON de credenciales
2. Copia el `client_id` y `client_secret`

## Configuración en el Servidor

### Variables de Entorno

Configura estas variables de entorno en tu sistema:

```bash
export GOOGLE_OAUTH2_CLIENT_ID="tu_client_id.googleusercontent.com"
export GOOGLE_OAUTH2_CLIENT_SECRET="tu_client_secret"
```

O agrégalas a tu archivo `.env` si usas python-dotenv.

## Uso

### 1. Autorizar la Aplicación

1. Ve al Dashboard
2. En la sección "Integración Google Contacts"
3. Haz clic en "Conectar Google Contacts"
4. Autoriza el acceso a tus contactos
5. Serás redirigido de vuelta al dashboard

### 2. Sincronización Automática

Una vez conectado:
- Cuando recibas un mensaje de WhatsApp, el sistema buscará automáticamente el número en tus contactos de Google
- Si encuentra el contacto, mostrará el nombre real en lugar del número
- La sincronización es automática y ocurre en segundo plano

### 3. Sincronización Manual

También puedes sincronizar contactos específicos:
- Ve a la lista de conversaciones
- Busca el contacto que quieres sincronizar
- Usa la API `/api/google-contacts/sync/{contact_id}/` para forzar la sincronización

## Funciones Implementadas

### Búsqueda Automática
- Se ejecuta cuando se recibe un mensaje nuevo
- Busca el número en Google Contacts
- Actualiza el nombre del contacto si lo encuentra
- Funciona con números internacionales

### Normalización de Números
- Maneja diferentes formatos de números (+57, 57, etc.)
- Compatible con números colombianos e internacionales
- Busca coincidencias parciales en Google Contacts

### Gestión de Tokens
- Los tokens OAuth se almacenan de forma segura
- Se renuevan automáticamente cuando es posible
- Manejo de errores de tokens expirados

## APIs Disponibles

### Estado de Conexión
```
GET /api/google-contacts/status/
```

### Buscar Contacto
```
POST /api/google-contacts/search/
Content-Type: application/json

{
    "phone_number": "+573001234567"
}
```

### Sincronizar Contacto Específico
```
POST /api/google-contacts/sync/{contact_id}/
```

### Desconectar
```
POST /api/google-contacts/disconnect/
```

## Seguridad

- Los tokens OAuth se almacenan encriptados en la base de datos
- Solo usuarios autenticados pueden acceder a las APIs
- Los tokens expiran automáticamente según la configuración de Google
- No se almacenan contraseñas ni información sensible

## Solución de Problemas

### Error "Verification failed"
- Verifica que las URLs de callback estén correctamente configuradas en Google Console
- Asegúrate de que el dominio coincida exactamente

### Token expirado
- Ve al dashboard y reconecta Google Contacts
- Los tokens se renuevan automáticamente cuando es posible

### Contactos no encontrados
- Verifica que el contacto esté guardado en Google Contacts
- Asegúrate de que el número esté en formato internacional
- Algunos números pueden tener formatos diferentes entre WhatsApp y Google Contacts

## Logs de Debug

Para ver los logs de sincronización:
- Los mensajes de debug aparecen en la consola del servidor
- Busca mensajes que comiencen con "🔍", "✅", o "❌"

## Consideraciones de Rendimiento

- La búsqueda se hace en segundo plano para no bloquear mensajes
- Los contactos se sincronizan máximo una vez cada 24 horas
- La API de Google tiene límites de uso que debes considerar para gran volumen