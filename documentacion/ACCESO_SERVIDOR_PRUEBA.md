# Acceso al Servidor de Prueba

## 🌐 URL de Acceso

**URL Principal**: https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer

## 🔑 Credenciales de Acceso

### Usuario Administrador
- **Email**: `admin@example.com`
- **Contraseña**: `admin123`

## 📱 Páginas Disponibles

### Páginas Públicas
- **Login**: https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/login/

### Páginas Protegidas (requieren autenticación)
- **Dashboard**: https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/dashboard/
- **Chats**: https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/chat/
- **Leads**: https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/leads/
- **Plantillas**: https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/templates/
- **Embudos**: https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/funnels/
- **Reportes**: https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/reports/

### Panel de Administración de Django
- **Admin**: https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/admin/

## 🧪 Cómo Probar la Aplicación

### 1. Iniciar Sesión
1. Ve a la URL principal
2. Serás redirigido automáticamente al login
3. Ingresa las credenciales del administrador
4. Haz clic en "Iniciar Sesión"

### 2. Explorar el Dashboard
- Verás métricas de conversaciones (actualmente en 0 porque no hay datos)
- Podrás ver recordatorios pendientes
- Listado de conversaciones recientes

### 3. Gestionar Leads
1. Ve a la sección "Leads"
2. Haz clic en "+ Nuevo Lead"
3. Nota: Necesitarás crear un contacto primero desde el admin

### 4. Crear Plantillas
1. Ve a "Plantillas"
2. Haz clic en "+ Nueva Plantilla"
3. Completa el formulario:
   - Nombre: "Saludo Inicial"
   - Contenido: "Hola, ¿en qué puedo ayudarte?"
   - Categoría: "Ventas"
4. Guarda la plantilla

### 5. Explorar Embudos
1. Ve a "Embudos"
2. Alterna entre "Ventas" y "Soporte"
3. Verás las diferentes etapas de cada embudo

### 6. Ver Reportes
1. Ve a "Reportes"
2. Cambia el período de tiempo (7, 30, 90 días)
3. Explora las estadísticas por plataforma, tipo de lead, etc.

### 7. Panel de Administración
1. Ve a `/admin/`
2. Usa las mismas credenciales
3. Desde aquí puedes:
   - Crear contactos manualmente
   - Configurar las APIs de mensajería
   - Gestionar usuarios
   - Ver logs de actividad

## 🔧 Configurar APIs de Mensajería

Para probar las integraciones con WhatsApp, Facebook y Telegram:

1. Ve al panel de administración
2. Navega a **Core** > **Api Configurations**
3. Selecciona la plataforma (whatsapp, facebook o telegram)
4. Ingresa tus credenciales:
   - Para WhatsApp: Phone Number ID, Business Account ID, Access Token
   - Para Facebook: Page ID, Page Access Token, App Secret
   - Para Telegram: Bot Token
5. Marca como "Is active"
6. Guarda los cambios

### URLs de Webhooks

Una vez configuradas las APIs, configura estos webhooks en las plataformas:

- **WhatsApp**: `https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/webhooks/whatsapp/`
- **Facebook**: `https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/webhooks/facebook/`
- **Telegram**: `https://8000-isd3q9b53rtrwh3wsth2s-29d03aeb.manusvm.computer/webhooks/telegram/`

## 📊 Crear Datos de Prueba

Para ver la aplicación con datos, puedes crear registros desde el admin:

### Crear un Contacto
1. Admin > Core > Contacts > Add Contact
2. Completa:
   - Name: "Juan Pérez"
   - Platform: whatsapp
   - Platform user id: "1234567890"
   - Phone: "+593987654321"
   - Country: "Ecuador"
3. Guarda

### Crear una Conversación
1. Admin > Core > Conversations > Add Conversation
2. Selecciona el contacto creado
3. Status: "active"
4. Asigna a un usuario
5. Guarda

### Crear un Lead
1. Admin > Core > Leads > Add Lead
2. Selecciona el contacto
3. Case type: "sale"
4. Status: "new"
5. Agrega notas
6. Guarda

### Crear un Mensaje
1. Admin > Core > Messages > Add Message
2. Selecciona la conversación
3. Sender type: "contact"
4. Sender name: "Juan Pérez"
5. Content: "Hola, necesito información"
6. Guarda

## 🎨 Características Responsive

La aplicación es completamente responsive. Pruébala en:
- Desktop (1920x1080)
- Tablet (768x1024)
- Móvil (375x667)

## ⚠️ Notas Importantes

1. **Servidor de Prueba**: Este es un servidor temporal para demostración
2. **Datos**: Los datos se perderán cuando se reinicie el servidor
3. **Seguridad**: Las configuraciones de seguridad están en modo desarrollo
4. **Performance**: El servidor puede ser más lento que un entorno de producción
5. **Webhooks**: Los webhooks funcionarán si configuras las APIs correctamente

## 🐛 Solución de Problemas

### Error 502 Bad Gateway
- El servidor Django se detuvo
- Contacta al administrador para reiniciarlo

### No se cargan los estilos CSS
- Refresca la página con Ctrl+F5 (forzar recarga)
- Limpia la caché del navegador

### No puedo iniciar sesión
- Verifica que estés usando el email correcto: `admin@example.com`
- La contraseña es: `admin123`
- Asegúrate de que las cookies estén habilitadas

### Error CSRF
- Limpia las cookies del navegador
- Intenta en modo incógnito

## 📞 Soporte

Si encuentras algún problema o tienes preguntas sobre la aplicación, por favor documenta:
- La URL donde ocurrió el error
- Los pasos para reproducir el problema
- Capturas de pantalla si es posible

## ✅ Checklist de Pruebas

- [ ] Iniciar sesión exitosamente
- [ ] Ver el dashboard
- [ ] Crear una plantilla
- [ ] Navegar por todas las secciones
- [ ] Crear un contacto desde el admin
- [ ] Crear un lead
- [ ] Ver los embudos
- [ ] Explorar los reportes
- [ ] Probar en móvil
- [ ] Cerrar sesión

---

**Fecha de despliegue**: 26 de Octubre, 2025  
**Versión**: 1.0.0  
**Estado**: Activo ✅

