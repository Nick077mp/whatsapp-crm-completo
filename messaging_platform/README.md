'''
# Plataforma de Mensajería Multicanal

Esta es una aplicación web desarrollada en Django para la gestión centralizada de interacciones con clientes a través de múltiples plataformas de mensajería como WhatsApp, Facebook Messenger y Telegram.

## Características Principales

- **Autenticación de Usuarios**: Sistema de login seguro para administradores y agentes.
- **Dashboard de Métricas**: Visualización en tiempo real de diálogos, tiempos de respuesta y actividad general.
- **Gestión de Leads**: Creación, edición y seguimiento de prospectos generados desde los chats.
- **Chat Integrado**: Interfaz para responder conversaciones de todas las plataformas desde un solo lugar.
- **Plantillas de Respuestas**: Sistema para crear y gestionar respuestas rápidas y autorizadas.
- **Embudos de Ventas y Soporte**: Clasificación y seguimiento de conversaciones según su etapa en el embudo.
- **Reportes de Actividad**: Estadísticas detalladas sobre la comunicación y el rendimiento de los agentes.
- **Configuración Dinámica de APIs**: Las credenciales de las APIs se gestionan desde el panel de administración de Django.

## Stack Tecnológico

- **Backend**: Django, Django REST Framework, Channels
- **Frontend**: HTML, CSS, JavaScript (con jQuery)
- **Base de Datos**: PostgreSQL
- **Asynchronous Tasks**: Celery con Redis (preparado para futuras implementaciones)

## Instalación y Configuración

Sigue estos pasos para poner en marcha la aplicación en un entorno de desarrollo local.

### 1. Prerrequisitos

- Python 3.10+
- PostgreSQL 12+
- Redis (opcional, para Channels y Celery)

### 2. Clonar el Repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd messaging_platform
```

### 3. Crear y Activar un Entorno Virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 5. Configurar la Base de Datos

- Inicia sesión en PostgreSQL y crea la base de datos:

```sql
CREATE DATABASE messaging_platform;
```

- Crea un usuario y otórgale privilegios (o usa un usuario existente):

```sql
CREATE USER miusuario WITH PASSWORD 'micontraseña';
GRANT ALL PRIVILEGES ON DATABASE messaging_platform TO miusuario;
```

### 6. Configurar Variables de Entorno

- Copia el archivo de ejemplo `.env.example` a `.env`:

```bash
cp .env.example .env
```

- Edita el archivo `.env` con tus propias credenciales. Presta especial atención a la configuración de la base de datos.

```ini
# messaging_platform/.env

# Database Configuration
DB_NAME=messaging_platform
DB_USER=miusuario
DB_PASSWORD=micontraseña
DB_HOST=localhost
DB_PORT=5432

# Django Configuration
SECRET_KEY=genera-una-clave-segura-aqui
DEBUG=True
```

### 7. Aplicar Migraciones y Crear Superusuario

- Ejecuta las migraciones para crear las tablas de la base de datos y inicializa los datos básicos:

```bash
python manage.py migrate
python manage.py init_data
```

El comando `init_data` crea las plataformas (`whatsapp`, `facebook`, `telegram`) y un superusuario por defecto con las siguientes credenciales:
- **Usuario**: `admin`
- **Contraseña**: `admin123`

### 8. Ejecutar el Servidor de Desarrollo

```bash
python manage.py runserver
```

La aplicación estará disponible en `http://127.0.0.1:8000/`.

## Configuración de APIs de Mensajería

Una vez que hayas iniciado sesión como administrador, puedes configurar las credenciales de las APIs directamente desde el panel de administración de Django (`/admin/`):

1.  Ve a la sección **Core** > **Api Configurations**.
2.  Selecciona la plataforma que deseas configurar (ej. WhatsApp).
3.  Introduce los tokens y IDs correspondientes obtenidos de los proveedores de las APIs.
4.  Activa la configuración y guarda los cambios.

### Configuración de Webhooks

Para que la aplicación reciba mensajes, debes configurar las URLs de los webhooks en las plataformas de los proveedores (Facebook for Developers, Telegram BotFather, etc.). Las URLs son:

- **WhatsApp**: `https://<TU_DOMINIO>/webhooks/whatsapp/`
- **Facebook**: `https://<TU_DOMINIO>/webhooks/facebook/`
- **Telegram**: `https://<TU_DOMINIO>/webhooks/telegram/`

Para desarrollo local, puedes usar una herramienta como `ngrok` para exponer tu servidor local a internet.

## Estructura del Proyecto

```
/messaging_platform
├── config/             # Configuración principal del proyecto Django
├── core/               # Aplicación principal del proyecto
│   ├── migrations/     # Migraciones de la base de datos
│   ├── services/       # Lógica de negocio para APIs externas
│   ├── management/     # Comandos de gestión personalizados
│   ├── admin.py        # Configuración del admin de Django
│   ├── models.py       # Modelos de la base de datos
│   ├── urls.py         # Rutas de la aplicación
│   ├── views.py        # Vistas principales
│   └── webhook_views.py # Vistas para los webhooks
├── static/             # Archivos estáticos (CSS, JS, imágenes)
├── templates/          # Plantillas HTML de Django
├── .env.example        # Archivo de ejemplo para variables de entorno
├── manage.py           # Script de gestión de Django
└── README.md           # Este archivo
```
'''
