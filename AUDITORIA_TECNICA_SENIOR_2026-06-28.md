# PRISLAB SaaS — Auditoría Técnica Senior / Arquitecto
**Fecha:** 2026-06-28  
**Versión auditada:** v5.2 (`release/v1.0-local`)  
**Auditor:** Copilot CLI — Claude Sonnet 4.6  
**Alcance:** Arquitectura · Seguridad · Infraestructura · CI/CD · Rendimiento · Deuda técnica

---

## 📊 Resumen Ejecutivo

| Categoría | P0 Crítico | P1 Alto | P2 Medio | P3 Bajo |
|---|---|---|---|---|
| Seguridad | 2 | 3 | 2 | 1 |
| Infraestructura | 1 | 2 | 1 | 2 |
| Rendimiento | 0 | 2 | 2 | 1 |
| CI/CD | 0 | 1 | 2 | 0 |
| Deuda técnica | 0 | 1 | 3 | 3 |
| **TOTAL** | **3** | **9** | **10** | **7** |

**Estado producción VPS actual:** ✅ Operativa  
**Estado nuevo deploy Docker:** ⛔ BLOQUEADO sin fix P0-1

---

## 🔴 P0 — CRÍTICOS

### P0-1 · Docker build SIEMPRE falla — entrypoint inexistente
**Archivo:** `Dockerfile` líneas 84-87  
El Dockerfile referencia `scripts/cloudrun_web_entrypoint.sh` que **no existe**. El archivo real es `scripts/web_entrypoint.sh`. Todo `docker compose up --build` falla con `exit 127`.

```diff
- RUN sed -i 's/\r$//' /app/scripts/cloudrun_web_entrypoint.sh && chmod +x /app/scripts/cloudrun_web_entrypoint.sh
- CMD ["/app/scripts/cloudrun_web_entrypoint.sh"]
+ RUN sed -i 's/\r$//' /app/scripts/web_entrypoint.sh && chmod +x /app/scripts/web_entrypoint.sh
+ CMD ["/app/scripts/web_entrypoint.sh"]
```

### P0-2 · Nginx Docker Compose no alcanza la app (502)
**Archivo:** `nginx/conf.d/prislab.conf` línea 2  
En Docker Compose el contenedor `nginx` NO puede conectar a `127.0.0.1:8000` (localhost dentro del contenedor nginx no tiene nada). Debe usar el nombre de servicio `app:8000`.

```diff
 upstream prislab_app {
-    server 127.0.0.1:8000;
+    server app:8000;   # nombre del servicio en docker-compose.yml
 }
```
**Fix:** Creado `nginx/conf.d/prislab.docker.conf` para Docker Compose. VPS bare-metal sigue con `prislab.conf`.  
**Acción en docker-compose.yml:** Montar `./nginx/conf.d/prislab.docker.conf` en vez de la carpeta entera.

### P0-3 · Secretos reales en `.env` de desarrollo
El `.env` tiene tokens y claves criptográficas con valores reales activos:
`FERNET_KEY`, `VAPID_PRIVATE_KEY/PUBLIC_KEY`, `PRISLAB_API_TOKEN`, `PRISCI_WEBHOOK_TOKEN`, `CRON_SECRET`, `HL7_API_KEY`, `LAB_VALIDATION_PIN`.  
Aunque está gitignoreado, si el repo se clona sin `.gitignore` aplicado o se hace un backup comprimido del directorio, quedan expuestos.  
**Fix:** Ejecutar `scripts/rotate_secrets.sh` y actualizar la VPS.

---

## 🟠 P1 — ALTOS

### P1-1 · config/settings.py (50 KB) + config/settings/ coexisten
El monolito `config/settings.py` es código muerto — Python resuelve `DJANGO_SETTINGS_MODULE=config.settings` al **paquete** `config/settings/__init__.py`. 50 KB de código obsoleto confunden IDEs, linters y nuevos desarrolladores.  
**Fix:** Renombrar a `config/_settings_LEGACY_DEPRECATED.py`.

### P1-2 · CI Python 3.11 vs Dockerfile Python 3.12
Tests corren en 3.11, producción en 3.12. Divergencia silenciosa de comportamiento.

```yaml
# .github/workflows/main.yml
- python-version: "3.11"
+ python-version: "3.12"
```

### P1-3 · Sesiones en DB cuando Redis está disponible
`SESSION_ENGINE = 'django.contrib.sessions.backends.db'` es incondicional. Con Redis activo, cada request hace un `SELECT`+`UPDATE` innecesario en PostgreSQL.

```python
# config/settings/cache.py — DESPUÉS del bloque if REDIS_URL:
if REDIS_URL:
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
```

### P1-4 · DB_CONN_MAX_AGE=0 en producción
Sin persistent connections. Con 4 workers × 4 threads = 16 conexiones/request en el peor caso.

```python
# config/settings/database.py
- db_conn_max_age = _env_int('DB_CONN_MAX_AGE', 0 if IS_PRODUCTION else 60)
+ db_conn_max_age = _env_int('DB_CONN_MAX_AGE', 60)
```

### P1-5 · nginx X-Forwarded-For incorrecto
`$remote_addr` rompe la detección de IP real del cliente para audit trail, rate limiting y baneos.

```nginx
- proxy_set_header X-Forwarded-For $remote_addr;
+ proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

### P1-6 · Sin Content-Security-Policy (sistema clínico ISO 15189)
Sin CSP, XSS exitoso puede exfiltrar tokens y datos de pacientes. Falla auditoría ISO.

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' wss:; frame-ancestors 'none';" always;
```

### P1-7 · HSTS inconsistente nginx (2 años) vs Django (1 año)
Nginx: `max-age=63072000`. Django: `SECURE_HSTS_SECONDS=31536000`. Unificar a 1 año.

### P1-8 · IP pública del servidor hardcodeada en nginx conf
`216.238.89.243` en `server_name` del conf de nginx está en historial git permanentemente.  
**Fix:** Eliminar la IP del `server_name` (nginx ya resuelve por dominio).

### P1-9 · numpy duplicado en requirements.txt
Dos líneas: `numpy>=1.26.4` y `numpy>=1.26.0`. Eliminar la segunda.

---

## 🟡 P2 — MEDIOS

### P2-1 · CI sin verificación de migraciones pendientes
Añadir al quality gate:
```yaml
- name: Check pending migrations
  run: python manage.py migrate --check
```

### P2-2 · migrate en entrypoint sin lock distribuido
4 workers Gunicorn ejecutan `migrate --noinput` simultáneamente al arrancar. Puede causar race conditions en migraciones complejas.  
**Fix:** Usar un init-container o `PRISLAB_SKIP_MIGRATE_ON_STARTUP=1` con migrate manual controlado.

### P2-3 · gdrive_credentials.json en repo root
Gitignoreado pero presente. Mover a `/opt/prislab/secrets/`.

### P2-4 · Celery Beat — solo 1 tarea periódica
Faltan: backup diario, limpieza de sesiones DB, health check HL7.

### P2-5 · Archivos temporales en raíz del repo
15+ `.md` de auditoría, scripts one-shot `.py`, carpetas `auditoria_ui_*`, `cert.pem`, `key.pem` en la raíz.

### P2-6 · SESSION_COOKIE_AGE = 30 días para sistema clínico
ISO 27001 recomienda ≤ 8 horas para sistemas con datos de pacientes.

### P2-7 · Sin healthcheck en contenedor `app`
Si Gunicorn arranca pero falla silenciosamente, el stack aparece "saludable".

### P2-8 · certbot sin `networks:` definida en docker-compose

---

## 🔵 P3 — BAJOS

### P3-1 · Gunicorn gthread (WSGI) con Django Channels (ASGI)
`--worker-class gthread` es WSGI. Channels necesita ASGI. Verificar si WebSockets usan Daphne/Uvicorn separado o solo long-polling.

### P3-2 · Sin pip-compile / lock file
Dos deploys distintos pueden instalar versiones diferentes.

### P3-3 · Dependabot no cubre npm (package.json presente)

### P3-4 · Docker logs sin límite de tamaño → disco lleno eventual

### P3-5 · PRISLAB_ESCUDO_USUARIO_ID no documentado en .env.example
Variable **obligatoria en producción** que lanza RuntimeError, pero ausente del .env.example.

### P3-6 · gunicorn --timeout 300 enmascara requests colgadas

---

## 📅 Plan de Implementación

### Semana 1 — Bloqueantes P0
1. Fix Dockerfile (entrypoint) → `Dockerfile`
2. Fix nginx Docker upstream → `nginx/conf.d/prislab.docker.conf`
3. Rotar secretos comprometidos → `scripts/rotate_secrets.sh`
4. Smoke test Docker build end-to-end

### Semana 2 — Seguridad P1
1. Redis sessions + DB_CONN_MAX_AGE
2. CI → Python 3.12 + migration check
3. nginx: X-Forwarded-For, CSP, HSTS
4. Renombrar settings.py legacy + numpy dedup

### Semana 3 — Deuda P2
1. Celery Beat: backup + session cleanup
2. Healthcheck app + Docker logs limit
3. SESSION_COOKIE_AGE → 8h
4. Limpiar raíz del repo

### Semana 4 — Optimización P3
1. pip-compile lock, Dependabot npm
2. Expandir quality gate (farmacia, pacientes)
3. Documentación arquitectura
4. Release candidate final

---

## ✅ Checklist Final de Release

### Obligatorio pre-deploy
- [ ] `docker compose build` exitoso sin errores
- [ ] `python manage.py check --deploy` sin errores
- [ ] `python manage.py migrate --check` limpio
- [ ] Todos secretos P0-3 rotados en VPS `/opt/prislab/.env`
- [ ] `PRISLAB_ENV=production`, `DEBUG=False`
- [ ] `SECRET_KEY` ≥ 50 chars, no es el fallback dev
- [ ] `FERNET_KEY` nuevo (rotado)
- [ ] `ALLOWED_HOSTS` con dominio real
- [ ] `CSRF_TRUSTED_ORIGINS` con `https://tu-dominio.com`
- [ ] `PRISLAB_ESCUDO_USUARIO_ID` definido
- [ ] `LAB_VALIDATION_PIN` ≥ 8 chars, rotado

### Docker Compose
- [ ] nginx monta `prislab.docker.conf` (no `prislab.conf`)
- [ ] Healthcheck app: `/health/` → HTTP 200
- [ ] Redis con contraseña activa
- [ ] Logging limits en todos los servicios

### VPS bare-metal
- [ ] `nginx -t` limpio
- [ ] SSL ≥ 30 días vigentes
- [ ] Todos los servicios systemd activos
- [ ] Backup PostgreSQL verificado restaurable

### Post-deploy (verificación activa)
- [ ] `curl -I https://dominio.com` muestra HSTS, X-Frame-Options, CSP
- [ ] Login + WebSocket de notificaciones funcionando
- [ ] Resultado de laboratorio con PDF generado correctamente
- [ ] Celery Beat ejecutando tareas periódicas

---

*PRISLAB Auditoría Técnica Senior — 2026-06-28 — Copilot CLI*
