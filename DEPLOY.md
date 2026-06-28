# Guía de Despliegue en Vultr VPS

> **Nota:** esta es la guía canónica actual para VPS. Los documentos de Cloud Run, Railway y Nixpacks quedan solo como histórico.

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
2. Tener el repositorio clonado en `/opt/prislab/app`
3. Contar con un archivo `.env` de producción en `/opt/prislab/app/.env`
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
cd /opt/prislab/app
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Nota operativa real:

- en esta VPS el codigo productivo vive en `/opt/prislab/app`
- no asumir que `/opt/prislab` es el repo Git
- si `git pull` falla con `not a git repository`, revisar si `/opt/prislab/app/.git` existe
- si no existe, inicializar el repo y hacer `fetch + reset` contra `release/v1.0-local`

Secuencia de recuperacion ya validada:

```bash
sudo -u prislab git -C /opt/prislab/app init
sudo -u prislab git -C /opt/prislab/app remote add origin https://github.com/primerosaludlaboratorio-star/saasprislab.git
sudo -u prislab git -C /opt/prislab/app fetch --depth 1 origin release/v1.0-local
chown -R prislab:prislab /opt/prislab/app
sudo -u prislab git -C /opt/prislab/app reset --hard FETCH_HEAD
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
python scripts/run_manage_with_env.py migrate --noinput
python scripts/run_manage_with_env.py collectstatic --noinput
```

Importante:

- en esta VPS no debe usarse `source .env` para tareas operativas, porque `SECRET_KEY` y otras variables pueden contener caracteres especiales válidos para `systemd` pero no para `bash`
- para cualquier comando manual de producción usar `python scripts/run_manage_with_env.py ...`
- esto evita caer por error en una configuración parcial y terminar trabajando contra `sqlite` local en vez de PostgreSQL productivo

### 7. Configurar Nginx, servicios y SSL

Usar los scripts del repo:

```bash
sudo bash /opt/prislab/app/scripts/deploy_vps.sh
```

Para aplicar fixes y reiniciar servicios después de un pull:

```bash
sudo bash /opt/prislab/app/scripts/aplicar_fixes_produccion.sh
```

Si el arbol se actualizo via `fetch + reset` en vez de `git pull`, los reinicios siguen siendo obligatorios:

```bash
systemctl restart prislab-gunicorn
systemctl restart prislab-celery
systemctl restart prislab-celerybeat
systemctl reload nginx
```

Si necesitas sincronizar usuarios de auditoría directamente en la base real de producción:

```bash
cd /opt/prislab/app
.venv/bin/python scripts/run_manage_with_env.py sync_usuarios_auditoria \
  --empresa-id 1 \
  --admin-password 'CAMBIAR' \
  --jonathan-password 'CAMBIAR' \
  --olga-password 'CAMBIAR' \
  --admin-director-password 'CAMBIAR'
```

Si ya existe el dominio y solo quieres el certificado wildcard:

```bash
CF_API_TOKEN="tu-token-cloudflare" bash /opt/prislab/app/scripts/activar_wildcard_ssl.sh
```

Renovación manual del wildcard, si hiciera falta:

```bash
sudo certbot renew --dry-run
sudo systemctl reload nginx
```

El certificado wildcard actual usa `labcorecloud-wildcard` y cubre:

- `labcorecloud.com`
- `*.labcorecloud.com`

Servicios reales:
- `prislab-gunicorn`
- `prislab-celery`
- `prislab-celerybeat`

## Arranque automático recomendado

Usar `systemd` para:
- iniciar Gunicorn, Celery y Celery Beat al arrancar el servidor
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
5. Validar que `nginx`, `postgresql`, `redis-server`, `prislab-gunicorn`, `prislab-celery` y `prislab-celerybeat` estén activos
