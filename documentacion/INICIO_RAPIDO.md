# Guía de Inicio Rápido

Esta guía te ayudará a poner en marcha la aplicación de mensajería multicanal en menos de 10 minutos.

## Requisitos Previos

- Python 3.10 o superior
- PostgreSQL 12 o superior instalado y en ejecución
- Git (opcional)

## Pasos de Instalación

### 1. Instalar PostgreSQL (si no está instalado)

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

### 2. Crear Base de Datos

```bash
sudo -u postgres psql
```

Dentro de PostgreSQL:
```sql
CREATE DATABASE messaging_platform;
CREATE USER postgres WITH PASSWORD 'postgres';
ALTER USER postgres WITH SUPERUSER;
GRANT ALL PRIVILEGES ON DATABASE messaging_platform TO postgres;
\q
```

### 3. Instalar Dependencias de Python

```bash
cd messaging_platform
pip3 install -r requirements.txt
```

### 4. Configurar Variables de Entorno

```bash
cp .env.example .env
```

Edita el archivo `.env` si necesitas cambiar las credenciales de la base de datos.

### 5. Aplicar Migraciones e Inicializar Datos

```bash
python3 manage.py migrate
python3 manage.py init_data
```

Este comando creará:
- Las tablas de la base de datos
- Las plataformas (WhatsApp, Facebook, Telegram)
- Un usuario administrador:
  - **Usuario**: admin
  - **Contraseña**: admin123
  - **Email**: admin@example.com

### 6. Ejecutar el Servidor

```bash
python3 manage.py runserver
```

### 7. Acceder a la Aplicación

Abre tu navegador y ve a:
- **Aplicación**: http://127.0.0.1:8000/
- **Panel de Administración**: http://127.0.0.1:8000/admin/

Inicia sesión con:
- **Email**: admin@example.com
- **Contraseña**: admin123

## Configurar APIs de Mensajería

1. Inicia sesión en el panel de administración
2. Ve a **Core** > **Api Configurations**
3. Selecciona la plataforma que deseas configurar
4. Ingresa las credenciales obtenidas de los proveedores
5. Marca como **Is active** y guarda

Para obtener las credenciales, consulta el archivo `CONFIGURACION_APIS.md`.

## Crear Usuarios Adicionales

### Desde el Panel de Administración

1. Ve a http://127.0.0.1:8000/admin/
2. Selecciona **Users** > **Add User**
3. Completa el formulario y asigna un rol (admin, agent, supervisor)

### Desde la Línea de Comandos

```bash
python3 manage.py createsuperuser
```

## Estructura de la Aplicación

- **Dashboard**: Métricas y resumen de actividad
- **Chats**: Conversaciones de todas las plataformas
- **Leads**: Gestión de prospectos y clientes
- **Plantillas**: Respuestas predefinidas
- **Embudos**: Seguimiento de ventas y soporte
- **Reportes**: Estadísticas y análisis

## Solución de Problemas Comunes

### Error de conexión a PostgreSQL

Verifica que PostgreSQL esté en ejecución:
```bash
sudo service postgresql status
```

Si no está activo, inícialo:
```bash
sudo service postgresql start
```

### Error "ModuleNotFoundError"

Asegúrate de haber instalado todas las dependencias:
```bash
pip3 install -r requirements.txt
```

### Error "CSRF verification failed"

Limpia las cookies del navegador y vuelve a intentar.

### No aparecen los estilos CSS

Ejecuta:
```bash
python3 manage.py collectstatic --noinput
```

## Próximos Pasos

1. **Cambiar la contraseña del administrador**: Ve a tu perfil y actualiza la contraseña
2. **Configurar las APIs**: Sigue la guía en `CONFIGURACION_APIS.md`
3. **Crear usuarios adicionales**: Agrega agentes y supervisores
4. **Personalizar plantillas**: Crea respuestas rápidas para tu equipo
5. **Configurar webhooks**: Para recibir mensajes en tiempo real

## Recursos Adicionales

- **README.md**: Documentación completa del proyecto
- **CONFIGURACION_APIS.md**: Guía detallada para configurar las APIs
- **SEGURIDAD.md**: Mejores prácticas de seguridad

## Soporte

Si encuentras problemas, revisa los logs de Django:
```bash
tail -f /ruta/al/proyecto/logs/django.log
```

O ejecuta el servidor en modo verbose:
```bash
python3 manage.py runserver --verbosity 3
```

