# Entornos PRISLAB SaaS

**Versión:** 1.1
**Fecha:** 2026-07-29
**Rama:** `release/v1.0-local`

---

## 1. Resumen de entornos

La fuente única de verdad local está definida en
[`CANONICAL_SOURCE_OF_TRUTH.md`](CANONICAL_SOURCE_OF_TRUTH.md). Todas las
ediciones y despliegues deben salir del checkout canónico indicado allí.

| Entorno | Propósito | Rama | URL típica | Base de datos |
|---------|-----------|------|------------|---------------|
| **local** | Desarrollo en máquina del desarrollador | `feature/*` | `http://localhost:8000` | SQLite |
| **staging** | Validación previa a producción | `release/v1.0-local` | `https://staging.tu-dominio.com` | PostgreSQL dedicado |
| **production** | Operación real | `release/v1.0-local` (tag) | `https://tu-dominio.com` | PostgreSQL dedicado + backups |

---

## 2. Local

### Requisitos

- Python 3.12+
- SQLite (incluido)
- Redis opcional (puede usarse LocMemCache)

### Setup

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# Editar .env con valores locales
python manage.py migrate
python manage.py runserver
```

### Variables clave

```env
PRISLAB_ENV=development
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=sqlite
REDIS_URL=                      # vacío para usar LocMemCache
```

---

## 3. Staging

### Propósito

- Validar PRs y features antes de producción.
- Ejecutar pruebas con datos representativos.
- Probar el stack de monitoreo.

### Infraestructura

- VPS compartido o dedicado pequeño.
- PostgreSQL + Redis en contenedores.
- App Django + Gunicorn en contenedor.
- Nginx + Certbot.
- Prometheus + Grafana + Alertmanager (monitoring stack).

### Deploy

```bash
# El despliegue operativo vigente es local -> VPS:
.\scripts\deploy_local_to_vps.ps1 -User root
```

### Variables clave

Ver `.env.staging.example`:

```env
PRISLAB_ENV=staging
DEBUG=False
ALLOWED_HOSTS=staging.tu-dominio.com
SITE_URL=https://staging.tu-dominio.com
DB_HOST=db
REDIS_URL=redis://redis:6379/0
SECURE_SSL_REDIRECT=False
```

### Población de datos de prueba

```bash
# Catálogo LIMS
python manage.py ensamblar_lims_v75 --dry-run
python manage.py ensamblar_lims_v75
```

---

## 4. Production

### Propósito

- Operación real del laboratorio/farmacias/consultorios.
- Alta disponibilidad y seguridad.

### Infraestructura

- VPS dedicado o múltiples instancias.
- PostgreSQL con backups automatizados (`scripts/backup/backup_postgres.sh`).
- Redis con persistencia.
- Nginx + Certbot SSL.
- Prometheus + Grafana + Alertmanager.

### Deploy

```bash
# Despliegue operativo vigente desde Windows:
.\scripts\deploy_local_to_vps.ps1 -User root
# El script ejecuta migraciones, collectstatic, reinicio de servicios y health check.
```

### Variables clave

Ver `.env.production.example`:

```env
PRISLAB_ENV=production
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
SITE_URL=https://tu-dominio.com
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Seguridad adicional

- `.env` debe tener permisos `600`.
- `SECRET_KEY` generado con `get_random_secret_key()`.
- `FERNET_KEY` generado con `Fernet.generate_key()`.
- No exponer puertos de DB/Redis/RedisInsight al exterior.

---

## 5. Flujo de cambios entre entornos

```
feature/*  -->  release/v1.0-local  -->  staging  -->  production
   ↑                (PR)                (deploy)      (deploy)
   │                  │                    │             │
   └─ developer ──────┴─ Editor 1/2 ──────┴─ CI/CD ─────┘
```

1. Desarrollador crea `feature/*` desde `release/v1.0-local`.
2. Abre PR a `release/v1.0-local`.
3. Se ejecutan status checks: quality gate, SRE, backup, secret scan, SBOM.
4. Merge a `release/v1.0-local` dispara deploy a production por defecto en el workflow actual.
5. `staging` queda como ruta manual solo si el entorno tiene secretos configurados.
6. Validación en producción según la revisión registrada por el script local.

---

## 6. Variables de entorno por ambiente

| Variable | Local | Staging | Production |
|----------|-------|---------|------------|
| `DEBUG` | `True` | `False` | `False` |
| `ALLOWED_HOSTS` | `localhost` | `staging.*` | dominio real |
| `SECURE_SSL_REDIRECT` | `False` | `False` | `True` |
| `SECURE_HSTS_SECONDS` | `0` | `0` | `31536000` |
| `DB_HOST` | SQLite | `db` | `127.0.0.1` |
| `REDIS_URL` | vacío | `redis://redis:6379/0` | `redis://127.0.0.1:6379/0` |
| `GUNICORN_WORKERS` | N/A | `2` | `4+` |

---

## 7. Checklist de apertura de un nuevo entorno

- [ ] Servidor con Docker y Docker Compose.
- [ ] Dominio + DNS apuntando al servidor.
- [ ] Certificado SSL (Let's Encrypt/Certbot).
- [ ] Archivo `.env` creado desde el ejemplo correspondiente.
- [ ] Base de datos creada y usuario configurado.
- [ ] Migraciones ejecutadas.
- [ ] Static/media configurados.
- [ ] Backup automático configurado.
- [ ] Monitoreo levantado.
- [ ] Health checks responden correctamente.
