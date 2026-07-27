# Guía de Despliegue en Vultr VPS

> **Nota:** esta es la guía canónica actual para VPS. Los documentos de Cloud Run, Railway y Nixpacks quedan solo como histórico.

## Estado verificado 2026-07-27

### Estado vigente del ultimo cambio

El checkout local `release/v1.0-local` en `8a0e3e80a73a1e478ce015e6d4c050b6cb84af73` fue desplegado directamente desde esta maquina al VPS el 2026-07-27 mediante `scripts/deploy_local_to_vps.ps1 -User root`.
La evidencia remota confirma las migraciones `ia.0004` y `laboratorio.0017` aplicadas, `collectstatic` correcto, Gunicorn/Celery/Celery Beat activos y `/live/`, `/ready/` y `/health/` publicos en HTTP 200 con base de datos y cache disponibles.
La revision desplegada queda registrada en `/opt/prislab/app/DEPLOYED_REVISION`.

## Objetivo

La unica ruta vigente esta documentada en [DESPLIEGUE_UNICO_PRISLAB_VPS_LOCAL.md](DESPLIEGUE_UNICO_PRISLAB_VPS_LOCAL.md). Ese documento es la fuente operativa para acceso, despliegue y verificacion.

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

### Deploy directo desde el checkout local, sin GitHub

La ruta local empaqueta el checkout actual y lo transfiere por SSH. No hace `git pull` en la VPS ni depende de GitHub Actions. Requiere que la clave SSH de esta maquina este autorizada para `prislab@216.238.89.243`:

```powershell
.\scripts\deploy_local_to_vps.ps1
```

El script conserva `.env`, `.venv`, `media`, `staticfiles` y `logs` del servidor; actualiza el codigo, escribe `DEPLOYED_REVISION`, ejecuta migraciones y `collectstatic`, reinicia Gunicorn/Celery/Celery Beat, recarga Nginx y valida `/health/`.

Si el preflight responde `Permission denied`, no se transfiere ningun archivo. Debe autorizarse la clave en `/home/prislab/.ssh/authorized_keys` desde la consola de Vultr o usarse una clave que ya este autorizada.

Los archivos `DESPLEGAR_A_PRODUCCION.bat`, `EJECUTAR_EN_SERVIDOR.sh` y `docs/manual/SOP_DESPLIEGUE_SEGURO.md` contienen instrucciones historicas de Google Cloud/Cloud Run y no son el procedimiento vigente para `prislab.labcorecloud.com` en Vultr. No usar sus credenciales temporales ni sus comandos para este servidor.

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
- si no existe, no se debe inicializar ni reconstruir un repositorio remoto: el script de despliegue sincroniza el artefacto local y conserva los metadatos operativos de la VPS

### 5. Configurar `.env`

Variables mínimas:
- `DEBUG=False`
- `SECRET_KEY=...`
- `ALLOWED_HOSTS=tu-dominio.com,IP_DE_LA_VPS`
- `DB_HOST=127.0.0.1`
- `DB_NAME=prislab_db`
- `DB_USER=prislab_user`
- `DB_PASSWORD=...`
- `DEEPSEEK_API_KEY=...` si se usa DeepSeek como proveedor de PRIS
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
