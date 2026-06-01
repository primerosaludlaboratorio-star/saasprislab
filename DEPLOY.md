# Guía de Despliegue en Vultr VPS

## Objetivo

Dejar PRISLAB corriendo en una VPS limpia con:
- Ubuntu
- Nginx
- Gunicorn
- PostgreSQL
- UFW
- Certbot / Let's Encrypt

Producción actual:
- `https://prislab.labcorecloud.com`
- `https://labcorecloud.com`
- Wildcard `*.labcorecloud.com` pendiente de activación con Cloudflare DNS

## Prerrequisitos

1. Tener acceso root a la VPS
2. Tener el repositorio clonado en el servidor
3. Contar con un archivo `.env` de producción
4. Tener un dominio apuntando a la IP de la VPS para activar SSL

## Flujo recomendado

### 1. Preparar el sistema

```bash
apt update && apt upgrade -y
apt install -y nginx postgresql postgresql-contrib python3 python3-pip python3-venv python3-dev build-essential git curl certbot python3-certbot-nginx ufw
```

### 2. Configurar firewall

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

### 3. Crear base de datos PostgreSQL

```bash
sudo -u postgres createuser prislab_user
sudo -u postgres createdb prislab_db -O prislab_user
sudo -u postgres psql -c "ALTER USER prislab_user WITH PASSWORD 'cambia-esta-clave';"
```

### 4. Configurar entorno Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configurar `.env`

Variables mínimas:
- `DEBUG=False`
- `SECRET_KEY=...`
- `ALLOWED_HOSTS=tu-dominio.com,IP_DE_LA_VPS`
- `DB_HOST=127.0.0.1`
- `DB_NAME=prislab_db`
- `DB_USER=prislab_user`
- `DB_PASSWORD=...`
- `GOOGLE_API_KEY=...` si usas Gemini
- `GOOGLE_DRIVE_FOLDER_ID=...` si vas a guardar archivos en Drive
- `GOOGLE_APPLICATION_CREDENTIALS=/opt/prislab/credentials/google-drive.json`

### 6. Migraciones y estáticos

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

### 7. Levantar Gunicorn

```bash
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --threads 4 --timeout 120
```

### 8. Configurar Nginx

Crear un server block que:
- sirva `static/` y `staticfiles/`
- haga reverse proxy a `127.0.0.1:8000`
- fuerce HTTPS después de emitir el certificado

### 9. Emitir SSL

```bash
certbot --nginx -d labcorecloud.com -d prislab.labcorecloud.com
```

### 10. Activar wildcard cuando tengas el token DNS de Cloudflare

```bash
CF_API_TOKEN="tu-token-cloudflare" bash /opt/prislab/scripts/activar_wildcard_ssl.sh
```

Este paso deja listo `*.labcorecloud.com` para futuros subdominios cuando el token tenga acceso a la zona DNS.

## Arranque automático recomendado

Usar `systemd` para:
- iniciar Gunicorn al arrancar el servidor
- reiniciar en fallos
- mantener logs en `journalctl`

## Integraciones Google que sí se conservan

- `Google API Key` para Gemini
- `Google Drive API` para archivos clínicos y respaldos

## Verificación final

1. Abrir `https://prislab.labcorecloud.com`
2. Confirmar login
3. Confirmar acceso a farmacia, laboratorio y consultorio
4. Probar carga de archivo a Drive
5. Validar que `nginx`, `postgresql`, `redis-server`, `gunicorn` y `celery` estén activos
