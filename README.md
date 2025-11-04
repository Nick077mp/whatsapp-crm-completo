# 📱 CRM WhatsApp - Plataforma de Mensajería Completa

Una plataforma CRM completa para WhatsApp que permite gestionar conversaciones bidireccionales con clientes, soporta LIDs (Local Identifiers) y maneja multimedia.

## 🌟 Características

- ✅ **Mensajería bidireccional** - Envía y recibe mensajes de WhatsApp
- ✅ **Soporte LID completo** - Compatible con WhatsApp Business API moderna
- ✅ **Procesamiento multimedia** - Maneja imágenes, videos, audios y documentos
- ✅ **Base de datos PostgreSQL** - Almacenamiento robusto y escalable
- ✅ **Bridge WhatsApp estable** - Conexión confiable usando Baileys
- ✅ **Dashboard web** - Interfaz completa para gestionar conversaciones
- ✅ **API REST** - Endpoints para integración con otros sistemas
- ✅ **Manejo de timeouts** - Sistema robusto con prevención de errores

## 🏗️ Arquitectura

```
┌─────────────────┐    HTTP/JSON    ┌─────────────────┐    WebSocket    ┌─────────────────┐
│                 │ ◄──────────────► │                 │ ◄──────────────► │                 │
│  Django Backend │                 │ WhatsApp Bridge │                 │ WhatsApp Servers│
│   (Puerto 8000) │                 │  (Puerto 3000)  │                 │                 │
└─────────────────┘                 └─────────────────┘                 └─────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────┐                 ┌─────────────────┐
│   PostgreSQL    │                 │   Auth Files    │
│    Database     │                 │   (Baileys)     │
└─────────────────┘                 └─────────────────┘
```

## 📋 Requisitos

### Software requerido:
- **Python 3.8+**
- **Node.js 16+**
- **PostgreSQL 12+**
- **Git**

### Servicios externos:
- **WhatsApp Business Account** (para obtener QR de conexión)

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/whatsapp-crm-completo.git
cd whatsapp-crm-completo
```

### 2. Configurar Django Backend
```bash
cd messaging_platform

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# o en Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar base de datos PostgreSQL
cp config/settings.py.example config/settings.py
# Editar settings.py con tus credenciales de PostgreSQL

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar Django
python manage.py runserver 0.0.0.0:8000
```

### 3. Configurar WhatsApp Bridge
```bash
cd whatsapp_bridge

# Instalar dependencias
npm install

# Iniciar bridge
node app.js
```

### 4. Conectar WhatsApp
1. Accede a `http://localhost:3000/qr`
2. Escanea el código QR con WhatsApp Business
3. ¡Listo! El sistema estará conectado

## 📱 Uso

### Dashboard Web
- Accede a `http://localhost:8000` 
- Usa el superusuario creado para ingresar
- Gestiona conversaciones desde la interfaz web

### API REST
```bash
# Enviar mensaje
curl -X POST http://localhost:8000/api/send-whatsapp-message/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+573001234567",
    "message": "¡Hola desde el CRM!"
  }'

# Obtener conversaciones
curl http://localhost:8000/api/conversations/
```

## 🔧 Configuración

### Variables de entorno (Django)
```python
# messaging_platform/config/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'whatsapp_crm',
        'USER': 'tu_usuario',
        'PASSWORD': 'tu_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Configuración del Bridge
```javascript
// whatsapp_bridge/app.js
const PORT = 3000;
const DJANGO_BASE_URL = 'http://localhost:8000';
```

## 📁 Estructura del proyecto

```
proyecto_completo/
├── messaging_platform/          # Backend Django
│   ├── config/                  # Configuración Django
│   ├── core/                    # App principal
│   │   ├── models.py           # Modelos de datos
│   │   ├── views.py            # Vistas y API
│   │   ├── services/           # Servicios WhatsApp
│   │   └── migrations/         # Migraciones DB
│   ├── templates/              # Templates HTML
│   ├── static/                 # Archivos estáticos
│   └── manage.py               # Comando Django
├── whatsapp_bridge/            # Bridge Node.js
│   ├── app.js                  # Aplicación principal
│   ├── package.json            # Dependencias
│   └── auth_info/              # Autenticación WhatsApp
├── documentacion/              # Documentación técnica
└── README.md                   # Este archivo
```

## 🛠️ Tecnologías utilizadas

### Backend
- **Django 4.2** - Framework web Python
- **Django REST Framework** - API REST
- **PostgreSQL** - Base de datos
- **Pillow** - Procesamiento de imágenes

### WhatsApp Bridge  
- **Node.js** - Runtime JavaScript
- **@whiskeysockets/baileys** - Librería WhatsApp Web
- **Express.js** - Servidor HTTP
- **Axios** - Cliente HTTP

### Frontend
- **HTML5/CSS3/JavaScript** - Interface web
- **Bootstrap** - Framework CSS
- **jQuery** - Manipulación DOM

## 🔒 Seguridad

- ✅ **Autenticación requerida** para acceder al dashboard
- ✅ **Validación de JIDs** para prevenir ataques
- ✅ **Sanitización de entrada** en todos los endpoints
- ✅ **CORS configurado** correctamente
- ✅ **Archivos de sesión protegidos** (.gitignore)

## 🐛 Troubleshooting

### Error: "WhatsApp no conectado"
1. Verifica que el bridge esté ejecutándose en puerto 3000
2. Regenera el QR: `GET http://localhost:3000/qr`
3. Escanea nuevamente con WhatsApp Business

### Error: "Database connection failed"
1. Verifica que PostgreSQL esté ejecutándose
2. Confirma credenciales en `settings.py`
3. Ejecuta migraciones: `python manage.py migrate`

### Mensajes no llegan al cliente
1. Verifica logs del bridge: `docker logs whatsapp-bridge`
2. Confirma que el número esté en formato correcto
3. Revisa que el contacto exista en la base de datos

## 📈 Escalabilidad

### Producción
- Usa **nginx** como proxy reverso
- Configura **gunicorn** para Django
- Implementa **Redis** para cache
- Usa **PM2** para el bridge Node.js
- Configura **PostgreSQL** con réplicas

### Docker (próximamente)
```bash
docker-compose up -d
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crea tu rama de feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 👥 Autores

- **Tu Nombre** - *Desarrollo inicial* - [@tu-usuario](https://github.com/tu-usuario)

## 🙏 Agradecimientos

- [Baileys](https://github.com/WhiskeySockets/Baileys) - Librería WhatsApp Web
- [Django](https://www.djangoproject.com/) - Framework web Python
- [WhatsApp Business](https://business.whatsapp.com/) - Plataforma de mensajería

---

⭐ **¡Deja una estrella si te gusta el proyecto!** ⭐