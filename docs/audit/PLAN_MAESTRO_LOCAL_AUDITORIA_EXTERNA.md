# PRISLAB SaaS — Plan maestro (local primero) y guía para auditorías externas

**Versión:** 1.0  
**Alcance temporal:** Todo el trabajo descrito aquí asume **entorno local** hasta que el sistema funcione de forma estable en ese contexto. **No se incluyen acciones obligatorias sobre producción** en esta fase; las verificaciones y cambios en cloud se harán **después**, con baseline tomado de este documento.

> Nota de canon vigente: este plan es histórico y de soporte. El estado operativo actual y los pendientes vivos deben leerse en `docs/ai_coordination/`; si hay contradicción, manda el canon de coordinación más reciente.

**Objetivo del documento:**

1. Servir como **plan completo** para mejorar el producto de forma ordenada (arquitectura, funcionalidad, UX, comandos, pruebas).
2. Proveer **información suficiente** para que **auditores externos** (consultoría, pentest, ISO, revisión de código) puedan **determinar qué puede estar fallando** sin depender del conocimiento tribal del equipo.

---

## 1. Principios de la fase actual (solo local)

| Principio | Descripción |
|-----------|-------------|
| Local primero | Base de datos, dependencias y scripts validados en máquina de desarrollo o contenedor local reproducible. |
| Evidencia objetiva | Toda afirmación de “funciona” debe ir acompañada de comando ejecutado, salida relevante (o artefacto). |
| Sin cambios de producción | Variables de Cloud Run, Secret Manager, DNS y CORS de prod **no son parte del alcance inmediato**; el documento las menciona solo como **referencia futura**. |
| Trazabilidad | Incidencias enlazadas a módulo (app Django), ruta URL, comando o test. |

---

## 1.1 Estado de cierre actual (actualizado)

### H-005 — Suite de tests colgada

**Diagnóstico confirmado:** el bloqueo no era un bug simple de tests sino el costo de recrear y migrar todo el esquema Django sobre SQLite en cada corrida. El proyecto está diseñado para PostgreSQL; SQLite degrada fuerte en migraciones masivas y deja estados inconsistentes si se interrumpe una corrida.

**Estado actual:** `PARCIALMENTE CORREGIDO`

- **CI:** ya quedó encaminado a **PostgreSQL** como solución correcta para la ruta automatizada mediante [main.yml](C:/Users/jonil/Desktop/PRISLAB_SaaS-master/.github/workflows/main.yml) en el root del repositorio, apuntando al código en `PRISLAB_SaaS-master/`.
- **Local:** ya existen runners reproducibles en [run_quality_gate_postgres.ps1](C:/Users/jonil/Desktop/PRISLAB_SaaS-master/PRISLAB_SaaS-master/scripts/run_quality_gate_postgres.ps1) y [run_quality_gate_postgres.py](C:/Users/jonil/Desktop/PRISLAB_SaaS-master/PRISLAB_SaaS-master/scripts/run_quality_gate_postgres.py). Ambos replican la ruta CI sobre PostgreSQL; sigue pendiente contar con PostgreSQL real disponible en la máquina para ejecutar el gate completo.
- **Bootstrap operativo agregado:** [bootstrap_local_runtime.ps1](C:/Users/jonil/Desktop/PRISLAB_SaaS-master/PRISLAB_SaaS-master/scripts/bootstrap_local_runtime.ps1) concentra el flujo local de host: diagnóstico de WSL/Docker/PostgreSQL, preflight del stack y probe del gate PostgreSQL.
- **SQLite en memoria:** no resuelve la causa raíz; solo cambia el medio de almacenamiento, no el peso del grafo de migraciones.
- **Validación estática hecha:** el workflow root resuelve correctamente `working-directory: PRISLAB_SaaS-master` y encuentra `manage.py`, `requirements.txt` y `requirements-dev.txt`.

### Pendientes reales que siguen abiertos

| Hallazgo | Estado | Acción real pendiente |
|---------|--------|-----------------------|
| H-005 | Parcial | Verificar corrida CI en GitHub sobre PostgreSQL y ejecutar `scripts/run_quality_gate_postgres.py` o `scripts/run_quality_gate_postgres.ps1` cuando haya PostgreSQL disponible; después evaluar `squash` de migraciones |
| H-008 | **PARCIAL** | Repo-side del stack validado con preflight; falta solo runtime local porque Docker no está instalado en esta máquina |
| H-009 | **CERRADO** | Gate reproducible activo con `radon`, `lizard` y `jscpd`; baseline persistido en `tools/last_runs/quality_metrics_gate.json` |
| H-013 | **CERRADO** | Capa de middlewares consolidada en código y documentación: legado exportado removido, `ApiRequestIdMiddleware` adelantado, `RateLimitMiddleware` atómico, `ActividadUsuarioMiddleware` sin escrituras por request y `SentinelTelemetryMiddleware` sin solapamiento de latencia. |

### Regla operativa

**No declarar cierre enterprise mientras H-005 siga solo en estado parcial.**  
CI sobre PostgreSQL desbloquea la ruta correcta, pero no sustituye la validación del entorno local reproducible ni el cierre de la deuda de migraciones.

### 1.1.1 H-007 — Dependencias de seguridad (estado: **CERRADO**)

**Corrección aplicada en código:**

- `playwright` quedó fijado en `1.60.0` en `package.json` y `package-lock.json`.
- `chromadb` salió de `requirements.txt`; ya no forma parte del baseline Python por defecto.
- `core/utils/rag_engine.py` ahora usa **SQLite persistente por defecto** y solo habilita Chroma si existe activación explícita con `PRISLAB_ENABLE_CHROMA`.
- Se agregó prueba de regresión en `core/tests/test_rag_engine_hardening.py` para impedir que Chroma vuelva a activarse implícitamente.

**Resultado operativo:**

- El flujo RAG sigue operativo con backend SQLite persistente.
- El riesgo de cadena de suministro por `chromadb` queda fuera del runtime estándar mientras no exista versión upstream corregida.
- La actualización de Playwright queda alineada con el lock real del repositorio.

### 1.1.2 H-009 — Métricas de complejidad y duplicidad (estado: **CERRADO**)

**Corrección aplicada en código:**

- `requirements-dev.txt` ahora declara `radon` y `lizard`.
- `package.json` fija `jscpd` en `devDependencies` y expone `quality:metrics`.
- `.github/workflows/main.yml` instala toolchain Node con `npm ci --ignore-scripts` y ejecuta `python tools/quality_metrics_gate.py`.
- `tools/quality_metrics_gate.py` quedó como gate reproducible del proyecto:
  - alcance: `core`, `farmacia`, `laboratorio`, `inventario`, `contabilidad`, `consultorio`, `lims`, `pacientes`, `config`
  - exclusiones: `migrations`, `tests`, `docs`, `node_modules`, `_archive_legacy`
  - thresholds congelados:
    - `radon_max_complexity = 130`
    - `lizard_max_ccn = 130`
    - `lizard_max_length = 700`
    - `lizard_max_params = 12`
    - `jscpd_max_percent = 4.5`

**Baseline validado:**

- estado del gate: `pass`
- complejidad máxima actual: `128`
- longitud máxima actual: `689`
- duplicidad actual (`jscpd`): `4.31%`
- evidencia persistida: `tools/last_runs/quality_metrics_gate.json`

### 1.1.3 H-008 — Validación del stack local (estado: **PARCIAL**)

**Corrección aplicada en código:**

- `nginx/conf.d/prislab.docker.conf` quedó alineado con los mounts reales de Compose:
  - `/static/` -> `/app/staticfiles/`
  - `/media/` -> `/app/media/`
  - `/favicon.ico` -> `/app/staticfiles/img/favicon.ico`
- `.env.example` y `.env.production.example` ahora incluyen `REDIS_PASSWORD`, requerido por `docker-compose.yml`.
- Se agregó `scripts/validate_local_stack_preflight.py` para verificar el stack local sin depender de inspección manual.

**Resultado del preflight local:**

- estado: `pass_with_warnings`
- servicios esperados presentes: `app`, `db`, `redis`, `nginx`, `certbot`
- Dockerfile, entrypoint, nginx y plantillas de entorno: `OK`
- único bloqueo restante: `docker` no está instalado en esta máquina

**Conclusión real:**

- La parte del repositorio quedó alineada y validada.
- El cierre completo de H-008 depende exclusivamente de disponer del runtime Docker/Compose para levantar el stack y ejecutar la validación viva.

### 1.2 H-013 — Consolidación de middlewares custom (estado: **CERRADO**)

Fuente canónica de la cadena: `config/settings/base.py`.

**Middlewares custom activos en `MIDDLEWARE` (orden de ejecución real):**

1. `core.middleware.canonical_host.CanonicalHostMiddleware` — redirección a host canónico.
2. `core.api_contracts.middleware.ApiRequestIdMiddleware` — correlación `X-Request-ID`; ahora corre antes de autenticación.
3. `core.middleware.read_only.ReadOnlyMiddleware` — kill-switch solo lectura (`PRISLAB_READ_ONLY`).
4. `core.middleware.admin_access.AdminAccessMiddleware` — bastión `/admin/` por IP/grupo.
5. `core.middleware.rate_limit.RateLimitMiddleware` — rate limiting login/API por IP; contador atómico por ventana fija.
6. `core.middleware.empresa.EmpresaIdentityMiddleware` — tenant por usuario + sucursal, inyecta `request.modulos_activos`.
7. `core.middleware.suscripciones.SuscripcionMiddleware` — bloqueo por suscripción inactiva (402).
8. `core.middleware.feature_flags.FeatureFlagMiddleware` — bloquea módulos no contratados.
9. `core.middleware.json_response.JSONResponseMiddleware` — convierte errores HTML a JSON para XHR.
10. `core.middleware.actividad_usuario.ActividadUsuarioMiddleware` — rastrea actividad usuario con sesión, sin `save()` por request.
11. `core.middleware.sentinel.SentinelTelemetryMiddleware` — captura errores y auto-reparación.
12. `core.middleware.performance.PerformanceMiddleware` — diagnóstico de latencia + conteo SQL.
13. `core.middleware.pris_context.PrisContextMiddleware` — contexto para agente PRIS.
14. `core.middleware.mantenimiento.MaintenanceModeMiddleware` — modo mantenimiento.
15. `core.middleware.seguridad.SessionTimeoutMiddleware` — logout por inactividad 8h.
16. `core.middleware.seguridad.TenantStorageMiddleware` — inyecta slug empresa en storage Drive.
17. `core.middleware.blindaje_expediente.BlindajeExpedienteMiddleware` — bloquea modificaciones a notas selladas.
18. `core.middleware.blindaje_expediente.SnapshotMiddleware` — captura metadatos request para SHA.

**Middlewares fuera de la cadena:**

- `core.middleware.tenant_subdomain.TenantSubdomainMiddleware`: archivo existe, no activo en `MIDDLEWARE`; resolución tenant por subdominio no se usa en la cadena canónica actual.

**Cambios realizados para cerrar H-013:**

- `SuscripcionMiddleware`: se mantiene activo en la cadena (tiene tests propios). No se eliminó porque aporta control de pago.
- `core/middleware/admin_access_restrict.py`: eliminado; era un re-export redundante de `AdminAccessMiddleware`.
- `LogAccesoExpedienteMiddleware`: eliminado del módulo `core/middleware/seguridad.py` y de `core/middleware/__init__.py`. La trazabilidad NOM-024 de **modificaciones** queda cubierta por `BlindajeExpedienteMiddleware` + señales + `SnapshotMiddleware`.
- Medición de latencia/request consolidada:
  - `PerformanceMiddleware`: diagnóstico detallado (queries SQL, umbrales, `IncidenciaSentinel` >5s).
  - `SentinelTelemetryMiddleware`: solo captura de errores, auto-reparación y registro de incidencias; se eliminó su medición de latencia y auto-cleanup duplicados.
- `ActividadUsuarioMiddleware`: reescrito para usar la sesión (`_actividad_inicio`) en lugar de `usuario.save()` por cada request autenticado.
- `ApiRequestIdMiddleware`: movido antes de `AuthenticationMiddleware` para garantizar trazabilidad desde el inicio útil del request.
- `config/settings.py` sigue existiendo en el repo; la cadena activa de middlewares está definida en `config/settings/base.py`.
- `RateLimitMiddleware`: reescrito para usar contador atómico por ventana fija (`cache.add` + `cache.incr`) en lugar de lista no atómica; se eliminó la condición de carrera. El límite de `/api/` ahora aplica a todos los métodos HTTP y devuelve header `Retry-After`.
- Se verificó `python manage.py check`, el barrido de referencias huérfanas y las pruebas aisladas de `core.tests.test_rate_limit_middleware`, `core.tests.test_actividad_usuario_middleware` y `core.tests.test_auto_repair_tenant_guard`. Todas pasaron.

**Riesgos mitigados:**

- `ActividadUsuarioMiddleware` ya no genera `UPDATE` en cada request autenticado.
- `ApiRequestIdMiddleware` ahora asigna `X-Request-ID` antes de `AuthenticationMiddleware`.
- `SentinelTelemetryMiddleware` dejó de medir latencia y ejecutar auto-cleanup; ya no solapa con `PerformanceMiddleware`.
- `RateLimitMiddleware` ya no depende de listas de timestamps compartidas sin atomicidad; usa contador atómico por ventana fija (`cache.add`/`cache.incr`).

---

## 2. Inventario del sistema (contexto para auditores)

### 2.1 Stack técnico

| Capa | Tecnología principal |
|------|----------------------|
| Framework | Django 5.x |
| API estructurada | Django Ninja (`api/v3/`) |
| BD desarrollo típica | SQLite fallback si no hay `DB_HOST`; **recomendado para cierre real: PostgreSQL local/Docker** |
| BD producción (futuro) | PostgreSQL / Cloud SQL |
| Caché / colas / WS (opcional) | Redis (si `REDIS_URL`); sin Redis: LocMem, Channels en memoria, Celery “eager” |
| Media | Google Drive / GCS / local según configuración |
| Frontend incrustado | Templates Django + Bootstrap 5 + JS estático |

### 2.2 Apps de negocio relevantes (INSTALLED_APPS)

Incluyen entre otras: `core`, `farmacia`, `pacientes`, `laboratorio`, `lims`, `seguridad`, `iot`, `ia`, `recepcion`, `consultorio`, `inventario`, `contabilidad`, `bienestar`, `mantenimiento`, `marketing`, etc.

### 2.3 Rutas de entrada del código

| Artefacto | Función |
|-----------|---------|
| `manage.py` | CLI Django |
| `config/settings.py` | Configuración central (BD, CORS, seguridad, Celery, Channels) |
| `config/urls.py` | Árbol de URLs HTTP |
| `core/templates/base.html` | Layout principal y UX base |
| `.github/workflows/main.yml` | Quality Gate en CI (referencia; ejecutable también en local) |

---

## 3. Plan completo por fases (mejora continua)

### Fase A — Baseline local reproducible

**Meta:** Cualquier desarrollador o auditor puede levantar el proyecto y obtener el mismo tipo de verificación.

**Entregables:**

- Entorno Python acordado (p. ej. 3.11, alineado con CI).
- PostgreSQL disponible para la ruta de pruebas completa; SQLite queda solo como fallback de desarrollo liviano.
- Instalación documentada de dependencias del sistema donde aplique (p. ej. librerías para WeasyPrint en Linux; en Windows pueden requerirse wheels o WSL/Docker).
- Archivo `.env` de ejemplo **solo con claves necesarias para local** (sin secretos reales); lista explícita de variables opcionales vs obligatorias para features concretas (IA, Drive, etc.).

**Comandos de baseline (local):**

```text
python manage.py check
python manage.py migrate
python manage.py verificar_sistema_completo
python manage.py verificar_funcionalidades
```

Notas:

- `verificar_funcionalidades` puede mostrar `[WARN]` en BD vacía; es **esperado** hasta poblar datos o usar `--strict` solo cuando corresponda.
- Si `psycopg2-binary` falla en Windows, registrar Python exacto y alternativa (Docker Compose en repo, WSL).
- Para la suite grande, **no usar SQLite como baseline de cierre**: la ruta correcta es PostgreSQL local/Docker o CI con PostgreSQL.

### Fase B — Integridad de datos y multitenant

**Meta:** Evitar fugas entre empresas y datos huérfanos.

**Actividades:**

- Ejecutar `python manage.py verificar_integridad` (modo completo en PostgreSQL local cuando exista).
- Revisar middleware de tenant (`EmpresaIdentityMiddleware`, shadow mode `PRISLAB_TENANT_SHADOW_MODE`).
- Tests existentes relacionados con aislamiento (p. ej. `verificar_aislamiento_multitenant` si aplica).

**Evidencia para auditoría:** Salida del comando de integridad, extractos de logs de shadow tenant, resultados de tests.

### Fase C — Seguridad aplicativa (local + revisión estática)

**Meta:** Superficie de ataque conocida y documentada.

**Áreas de revisión externa:**

| Área | Qué revisar |
|------|-------------|
| Autenticación / sesión | Duración de cookie, 2FA, timeouts |
| CSRF | Endpoints exentos y mitigación alternativa |
| Endpoints `@csrf_exempt` | HL7, Sentinel, APIs públicas — autenticación por token, IP o firma |
| Subida de archivos | Límites (`FILE_UPLOAD_MAX_MEMORY_SIZE`), tipos MIME, almacenamiento |
| SQL dinámico | Uso de `cursor.execute`, `.extra()` — origen de strings |
| Secretos | Ausencia en repo; uso de variables de entorno |
| CORS | Comportamiento **en local** vs **futuro prod** (documentado, sin imponer cambios en prod ahora) |

**Herramientas sugeridas (auditores):** `bandit`, `pip-audit`, revisión manual de `config/settings.py` y vistas con `grep` por patrones de riesgo.

### Fase D — Funcionalidad por dominio (humano-operativo)

**Meta:** Cada flujo crítico tiene dueño, pasos y criterio de aceptación.

**Dominios sugeridos (checklist):**

1. Recepción / citas  
2. Laboratorio: orden → captura → validación → entrega  
3. Farmacia: inventario FEFO / caducidades / PDV  
4. Expediente / NOM-024 / blindaje de notas  
5. Inventario federado / compras  
6. Facturación / CFDI (sandbox en local)  
7. Bienestar NOM-035  
8. IA / voz / OCR (degradación elegante si falta API key)  

Para cada dominio el auditor debe registrar: **rol de usuario**, **pasos**, **resultado esperado**, **fallo observado**, **logs** (nivel INFO/WARNING/ERROR).

### Fase E — UX, accesibilidad y fiabilidad percibida

**Meta:** Coherencia con flujo humano (fatiga, interrupciones, errores).

**Revisiones:**

- Navegación por teclado, foco visible, landmarks (`main`, saltar contenido).
- Mensajes de error **honestos** (no “éxito” si la operación no persistió).
- Modo offline / cola de sincronización: mensajes al usuario cuando falle el backend.

### Fase F — Automatización de pruebas

**Meta:** Quality Gate reproducible en local.

**Referencia CI:** `.github/workflows/main.yml`  
**Suite ampliada local:** `python scripts_cursor_e2e/run_cursor_reliability_suite.py`  
**Omni / Playwright:** `npm run omni:local` (requiere servidor local y credenciales de prueba documentadas).

**Actualización actual:** la solución correcta para H-005 ya quedó orientada a **PostgreSQL en CI**.  
El siguiente cierre de esta fase es:

1. Verificar en GitHub que el workflow nuevo corre sobre PostgreSQL sin atasco en migraciones.
2. Ejecutar `scripts/run_quality_gate_postgres.ps1` en local con PostgreSQL disponible (Docker o instalación local).
3. Si se requiere runner multiplataforma o evidencia JSON del bloqueo, usar `scripts/run_quality_gate_postgres.py`; la salida queda en `tools/last_runs/postgres_quality_gate_local.json`.
3. Evaluar `squash` de migraciones como deuda técnica posterior para acelerar setup.

### Fase G — Producción (posterior; solo planificación aquí)

Cuando local sea estable:

1. Congelar versión/commit verificado.  
2. Paridad de variables de entorno (tabla diff local vs prod).  
3. Prueba de humo en staging con mismos comandos que Fase A.  
4. Ventana de auditoría externa con acceso de solo lectura a logs y métricas acordadas.

---

## 4. Paquete de información para auditorías externas

### 4.1 Qué debe entregar el equipo interno al auditor

| Entregable | Descripción |
|------------|-------------|
| Commit hash | Versión exacta del código auditado |
| `requirements.txt` + lock | Dependencias de runtime |
| Resultado `manage.py check` | Salida texto |
| Resultado smoke | `verificar_sistema_completo`, `verificar_integridad` |
| Resultado tests | Subconjunto al menos igual al Quality Gate |
| Modelo de datos | Diagrama o `django-extensions graph_models` si está disponible |
| Lista de URLs sensibles | Export desde inventario de rutas si existe (`tools/` relacionados) |
| Cuentas de prueba | Roles: recepción, lab, farmacia, director (solo entorno local/staging) |
| Política de backups | Comando/documentación de `backup_database` si aplica |

### 4.2 Preguntas guía para el auditor (qué puede estar fallando)

**Arquitectura**

- ¿Hay código muerto o comandos que reportan éxito sin ejecutar lógica útil?
- ¿Las migraciones están al día con los modelos?
- ¿Celery/Channels degradan de forma segura sin Redis?

**Seguridad**

- ¿Algún endpoint permite escalada de privilegios por parámetro ID sin comprobar empresa?
- ¿Las APIs públicas (QR, HL7) tienen rate limit y autenticación acorde?

**Datos**

- ¿Existen FK huérfanas en tablas de pagos, ventas u órdenes?
- ¿El modelo multitenant filtra siempre por `empresa_id` en consultas sensibles?

**UX / confianza**

- ¿Las respuestas JSON dicen “success” cuando falló persistencia o validación?
- ¿Los errores 500 muestran información sensible en DEBUG local?

### 4.3 Limitaciones conocidas del entorno local

| Limitación | Impacto en auditoría |
|------------|----------------------|
| SQLite vs PostgreSQL | Comportamiento de concurrencia y algunos checks SQL distintos |
| Sin Redis | WebSockets y caché no equivalentes a prod |
| Sin Google APIs | IA, Drive, Vision pueden estar desactivados o en modo degradado |
| Windows vs Linux | Compilación de dependencias nativas (p. ej. psycopg2, WeasyPrint) |

El auditor debe **explicitar el SO y versiones** en el informe final.

---

## 5. Matriz rápida: síntoma → dónde mirar

| Síntoma | Primer sitio a revisar |
|---------|------------------------|
| “Guardé pero no aparece” | Middleware solo lectura `PRISLAB_READ_ONLY`, logs `django.request`, transacciones en vista |
| Datos de otra empresa | Tenant middleware, managers `TenantModel`, queries sin `.filter(empresa=…)` |
| CORS / API desde otro puerto | Config CORS (solo relevante cuando se pruebe SPA separada; prod futuro) |
| PDF no genera | WeasyPrint / ReportLab, logs, versión OS |
| Celery no corre | `REDIS_URL`, `CELERY_TASK_ALWAYS_EAGER` |
| Login bucle | `CanonicalHostMiddleware`, `SESSION_COOKIE_*`, `CSRF_TRUSTED_ORIGINS` |

---

## 6. Documentación interna ya existente (referencias cruzadas)

Para profundizar sin duplicar todo el repositorio:

- `docs/audit/` — Informes y reconocimientos previos  
- `docs/manual/` — Runbooks y despliegue (consulta futura; no obligatorio para fase local pura)  
- `docs/LEVANTAMIENTO_TOPOGRAFICO_PRISLAB_SAAS.md` — Topología general  
- `RESUMEN_SCRIPTS_AUDITORIA.md` — Scripts de verificación  

Los auditores externos deben priorizar **este plan** como índice y contrastar con los hallazgos históricos en `docs/audit/`.

---

## 7. Criterios de salida de la fase “solo local”

Se considera lista la transición hacia preparación de producción cuando:

1. `python manage.py check` sin errores.  
2. Migraciones aplicadas en BD local de referencia.  
3. Quality Gate de tests (o subconjunto acordado) en verde en máquina reproducible **sobre PostgreSQL** (idealmente Docker).  
4. Lista de `[WARN]` de `verificar_funcionalidades` **explicada** (dato ausente vs bug).  
5. Informe corto interno: “Flujos críticos probados manualmente” con capturas o notas por dominio (Fase D).

---

## 8. Contacto y custodia del documento

- **Custodio sugerido:** responsable de calidad / release.  
- **Frecuencia de revisión:** al cerrar cada sprint o antes de auditoría externa.  
- **Control de versiones:** cambios vía mismo repositorio (PR con revisión).

---

*Fin del documento — solo planificación y auditoría; sin obligación de cambios en producción en esta etapa.*
