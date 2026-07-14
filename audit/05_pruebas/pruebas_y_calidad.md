# Auditoría de Pruebas y Calidad — PRISLAB SaaS

**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## EV-TEST-001 — `python manage.py check --deploy`

**Criticidad:** MEDIA  
**Archivo:** N/A (comando)  
**Estado:** EJECUTADO — 4 advertencias  
**Comando ejecutado:**
```bash
python manage.py check --deploy
```
**Output real:**
```
System check identified some issues:

WARNINGS:
?: (security.W004) You have not set a value for the SECURE_HSTS_SECONDS setting. If your entire site is served only over SSL, you may want to consider setting a value and enabling HTTP Strict Transport Security. Be sure to read the documentation first; enabling HSTS carelessly can cause serious, irreversible problems.
?: (security.W008) Your SECURE_SSL_REDIRECT setting is not set to True. Unless your site should be available over both SSL and non-SSL connections, you may want to either set this setting True or configure a load balancer or reverse-proxy server to redirect all connections to HTTPS.
?: (security.W012) SESSION_COOKIE_SECURE is not set to True. Using a secure-only session cookie makes it more difficult for network traffic sniffers to hijack user sessions.
?: (security.W016) You have 'django.middleware.csrf.CsrfViewMiddleware' in your MIDDLEWARE, but you have not set CSRF_COOKIE_SECURE to True. Using a secure-only CSRF cookie makes it more difficult for network traffic sniffers to steal the CSRF token.

System check identified 4 issues (0 silenced).
```
**Explicación:** Las advertencias son esperadas porque el entorno de auditoría no tiene configuradas las variables de producción (`SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`). En producción con las variables correctas no deberían aparecer.
**Confianza:** ★★★★★ (ejecutado)
**Riesgos:** Si se despliega sin configurar estas variables, las cookies y redirecciones SSL no serán seguras.
**Estado:** NO EJECUTABLE EN PRODUCCIÓN POR ENTORNO (advertencias por falta de env vars)

---

## EV-TEST-002 — Suite de tests de Django

**Criticidad:** ALTA  
**Archivo:** Múltiples `tests.py`, `tests/`  
**Estado:** NO EJECUTABLE EN ESTE ENTORNO  
**Comando intentado:**
```bash
python manage.py test core lims --verbosity=1
```
**Resultado:** El comando no finalizó en el tiempo de espera permitido (más de 90 segundos) y fue terminado.
**Explicación:** Sin base de datos PostgreSQL real, Django usa SQLite fallback. La suite `core lims` incluye muchos tests y posiblemente intentos de conexión a servicios externos, causando timeouts. No se pudo obtener un reporte de cobertura.
**Confianza:** ★★★★★ (intentado)
**Riesgos:** No se pudo validar regresión funcional localmente.
**Estado:** NO EJECUTABLE EN ESTE ENTORNO

---

## EV-TEST-003 — Archivos de test

**Criticidad:** INFORMATIVA  
**Archivo:** Múltiples  
**Estado:** IMPLEMENTADO  
**Explicación:** Existen archivos de test en varias apps (`core/tests_e2e.py`, `core/tests_e2e_playwright.py`, `consultorio/tests.py`, `farmacia/tests.py`, etc.). No se realizó conteo exacto por limitaciones de tiempo.
**Confianza:** ★★★☆☆ (parcial)
**Riesgos:** Ninguno; solo falta ejecución.

---

## EV-TEST-004 — CI/CD quality gate

**Criticidad:** ALTA  
**Archivo:** `.github/workflows/main.yml`  
**Estado:** IMPLEMENTADO  
**Explicación:** El workflow ejecuta checks de calidad, tests, migraciones y otras validaciones en cada PR/push a `release/v1.0-local` y `main`.
**Confianza:** ★★★☆☆ (código, no verificado en ejecución reciente)
**Riesgos:** Depende de secretos y runners disponibles. Requiere validación con Antigravity/Fase 4.

---

## EV-TEST-005 — Métricas de complejidad y duplicidad

**Criticidad:** MEDIA  
**Archivo:** N/A  
**Estado:** NO VERIFICABLE  
**Herramientas intentadas:**
- `radon` — no instalado
- `lizard` — no instalado
- `jscpd` — no instalado
**Explicación:** No se pudieron obtener métricas de complejidad ciclomática, duplicidad de código ni deuda técnica por falta de herramientas en el entorno.
**Confianza:** ★★★★★ (ejecutado)
**Riesgos:** Sin estas métricas no se puede cuantificar la deuda técnica ni identificar hotspots de complejidad.
**Estado:** NO VERIFICABLE
