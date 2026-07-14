# Auditoría de Base de Datos y Modelos — PRISLAB SaaS

**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## EV-DB-001 — Modelo de usuario custom

**Criticidad:** ALTA  
**Archivo:** `core/models/base.py` (presunto), `config/settings.py`  
**Línea:** `AUTH_USER_MODEL = 'core.Usuario'`  
**Explicación:** El sistema usa un modelo `Usuario` custom en `core`. Esto es correcto para un SaaS multi-tenant, pero requiere que todas las FK y referencias a usuarios usen `settings.AUTH_USER_MODEL` o `get_user_model()`.
**Confianza:** ★★★★☆ (código)
**Estado:** IMPLEMENTADO
**Riesgos:** Referencias a `User` de Django en lugar de `Usuario` podrían causar inconsistencias. No se verificó exhaustivamente.

---

## EV-DB-002 — Migraciones de LIMS recientes

**Criticidad:** ALTA  
**Archivo:** `lims/migrations/0011_perfilanalito_alter_perfillims_analitos_and_more.py`  
**Explicación:** Migración reciente crea modelo `PerfilAnalito` como tabla intermedia (through) entre `PerfilLims` y `Analito`. Añade campo `orden` y unique_together `(perfil, analito)`. Esto permite ordenar analitos dentro de un perfil para reportes.
**Confianza:** ★★★★☆ (código)
**Estado:** IMPLEMENTADO
**Riesgos:** Cambios en la relación M2M requieren que el importador y vistas la consuman correctamente. Antigravity reportó refactorización en este área.

---

## EV-DB-003 — Configuración de base de datos

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`  
**Línea:** 330-355  
**Fragmento:**
```python
if os.environ.get('DB_HOST'):
    db_host = os.environ.get('DB_HOST', '')
    db_conn_max_age = _env_int('DB_CONN_MAX_AGE', 0 if IS_PRODUCTION else 60)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'prislab_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': db_host,
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': db_conn_max_age,
            'CONN_HEALTH_CHECKS': _env_bool('DB_CONN_HEALTH_CHECKS', True),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {'timeout': 60},
        }
    }
```
**Explicación:** PostgreSQL cuando `DB_HOST` está configurado; SQLite como fallback local. `CONN_MAX_AGE` y `CONN_HEALTH_CHECKS` configurables.
**Confianza:** ★★★★☆ (código)
**Estado:** IMPLEMENTADO
**Riesgos:** En producción, si `DB_HOST` no está definido, cae a SQLite sin advertencia. Debe garantizarse que `DB_HOST` siempre esté en producción.

---

## EV-DB-004 — Integridad referencial

**Criticidad:** MEDIA  
**Archivo:** Múltiples modelos en `core/models/`, `lims/models.py`, etc.  
**Explicación:** Django maneja integridad referencial mediante `ForeignKey` con `on_delete`. No se pudo verificar el esquema real ni detectar claves foráneas ausentes por falta de acceso a PostgreSQL.
**Confianza:** ★★☆☆☆ (no verificable por entorno)
**Estado:** NO VERIFICABLE
**Riesgos:** Posible divergencia entre modelo Django y esquema real si se aplicaron migraciones manuales o se saltaron constraints.

---

## EV-DB-005 — Tenant por empresa

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`, `core/middleware/tenant_subdomain.py`  
**Explicación:** Sistema multi-tenant basado en subdominio/header con `Empresa` como tenant. Middleware `TenantSubdomainMiddleware` resuelve el tenant por request. `PRISLAB_TENANT_STRICT_MODE` activa validaciones estrictas.
**Confianza:** ★★★☆☆ (código, no ejecutado)
**Estado:** IMPLEMENTADO
**Riesgos:** Errores en resolución de tenant pueden exponer datos entre empresas. Requiere pruebas exhaustivas de aislamiento.

---

## EV-DB-006 — Backup y restauración

**Criticidad:** ALTA  
**Archivo:** `scripts/backup/backup_postgres.sh`, `.github/workflows/backup-restore-test.yml`  
**Explicación:** Existe script de backup de PostgreSQL y workflow de CI que prueba backup/restore.
**Confianza:** ★★★☆☆ (código)
**Estado:** IMPLEMENTADO
**Riesgos:** El workflow depende de secretos y entorno. No se ejecutó en este entorno.
