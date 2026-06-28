# Reporte — Seguridad perimetral, cierre inventario y deuda §9.1 (PRISLAB v7.5)

**Fecha:** 2026-04-04  
**Alcance:** Fase de saneamiento previa al **Punto 10** (fórmulas LIMS).  
**Referencias:** `config/urls.py`, `core/middleware/rate_limit.py`, `core/views/cron_tasks.py`, `DOCS_AUDIT_MAESTRO.md`, `GUARDIAN_360_REPORT.md`.

---

## 1. Resumen ejecutivo

| Frente | Estado | Notas |
| :--- | :--- | :--- |
| Manual en `docs/manual/` | **Hecho (archivo)** | Creado `docs/manual/MODULO_INVENTARIO_FEDERADO.md`. `docs/audit/MANUAL_INVENTARIO_FEDERADO_v75.md` quedó como **puntero**. |
| `.cursorignore` | **Pendiente (Programador)** | No fue posible editar `.cursorignore` desde el entorno de la IA (permiso denegado). Debe añadirse manualmente: `!docs/manual/`, `!docs/manual/**` y excepciones `*.md` equivalentes a las de `docs/audit/`. |
| Auditoría Zero Trust (`urls.py`) | **Documentada** | No hay “login en `urls.py`”: la protección está en **vistas** y **middleware**. Véase §2. |
| Cron stock crítico (staging) | **Pendiente (Programador)** | Validar `GET/POST` a `/cron/check-stock-critico/` con `X-Cron-Secret` y comprobar War Room / `NotificacionDiscrepancia`. |
| Migraciones periféricas | **Hecho (solo apps acordadas)** | Generadas y aplicadas: `bienestar.0003`, `ia.0003`, `iot.0003`. **No** se incorporó la cadena masiva `core`/`lims`/`inventario` que Django propuso al ejecutar `makemigrations ia` en bloque (§3). |

---

## 2. Perímetro HTTP (`config/urls.py`) — hallazgos

### 2.1 Falso positivo de la auditoría “sin `@login_required`”

Django **no** declara autenticación en `urlpatterns`. Las rutas apuntan a vistas; el decorador (o permisos de clase) vive en el **módulo de vista**. Por tanto, contar líneas en `urls.py` sin decorador **no** mide exposición real.

### 2.2 Rutas públicas **intencionales** (diseño)

| Prefijo / ruta | Motivo |
| :--- | :--- |
| `''`, `/login/`, logout, 2FA | Acceso y sesión. |
| `/kiosko/`, `/kiosko/check-in/<token>/` | Sala de espera sin sesión (`laboratorio/views/imprimir_zpl.py`: sin `@login_required` en kiosko). |
| `/validar/resultado/<uuid>/` | Enlace firmado por token UUID para paciente. |
| `/facturacion/autofactura/` | Portal paciente (`autofactura_publica` sin login). |
| `/media/`, estáticos, favicon | Entrega de assets (DEBUG: media local). |

### 2.3 Endpoints con modelo distinto a “sesión de usuario”

| Ruta | Mecanismo |
| :--- | :--- |
| `/cron/*` | `X-Cron-Secret` o cabeceras Google Scheduler / App Engine (`core/views/cron_tasks.py::_verificar_cron`). |
| `/api/iot/hl7/` | `csrf_exempt`; con `HL7_ACTIVE=True`: API key / IP (`laboratorio/views/hl7_receptor.py`). En standby devuelve **503**. |
| `/api/sentinel/shield-telemetry/` | `csrf_exempt`, sin login: telemetría best-effort (riesgo: **spam de logs**, no ejecución arbitraria). |
| `/api/sentinel/reset/`, `/api/sentinel/diagnostico/` | `admin_token` = primeros 16 caracteres de `SECRET_KEY` **o** superusuario en sesión. **Riesgo:** si el token corto se filtra, impacto administrativo alto; recomendación: token dedicado rotativo, no derivado de `SECRET_KEY`. |

### 2.4 APIs de negocio muestreadas (sesión requerida)

Ejemplos verificados en código: impresión ZPL (`@login_required`), corte caja unificado (`farmacia/views/corte_caja_api.py`), push VAPID/suscribir (`core/views/push.py`), creación de notificaciones (`core/views/notificaciones.py`).

### 2.5 Rate limiting existente (`core/middleware/rate_limit.py`)

- Login y rutas de rescate: límites por IP en **POST**.
- **`/api/*` + POST:** hasta **120** req/min por IP.
- **`/ia/*` + POST:** hasta **20** req/min (chat).

**Brecha menor:** rutas públicas que son sobre todo **GET** (`/kiosko/`, `/facturacion/autofactura/`, `/validar/...`) **no** entran en el bucket global de `/api/` POST. Para endurecer anti-DDoS superficial, valorar límites por IP en GET para esos prefijos o capa WAF (Cloud Armor / CDN).

---

## 3. Migraciones periféricas (sin tocar deuda `core` masiva)

- **`bienestar.0003_diarioemocional_anonimizado_and_more`:** campos NOM-035 (anonimización).
- **`ia.0003_alter_cotizacionocr_orden_asociada_and_more`:** alineación de FKs a `core.OrdenDeServicio`.
- **`iot.0003_alter_transaccionhl7_options_and_more`:** metadatos HL7 / kiosco.

Al ejecutar `makemigrations ia`, Django generó también migraciones pendientes en **`lims`**, **`inventario`** y **`core`** (cadena grande §9.1). Esas **no** se conservaron: se eliminaron los archivos generados y se ajustó la dependencia de `ia.0003` e `iot.0003` a **`core.0064_consentimiento_marketing_y_orden_opcional`**.

**Comando local de aplicación:** `migrate bienestar`, luego `migrate ia`, luego `migrate iot` (un `app_label` por invocación).

---

## 4. Acciones para el Programador (checklist)

1. Editar **`.cursorignore`**: desbloquear `docs/manual/**` (y `*.md` bajo esa ruta) como en §1.
2. **Staging:** invocar cron de stock crítico con secreto configurado; verificar alertas en War Room.
3. **Sentinel:** planificar sustitución del `admin_token` basado en prefijo de `SECRET_KEY` por secreto de operaciones independiente.

---

## 5. Cierre respecto al Punto 10

Con este reporte y las migraciones periféricas aplicadas, la **deuda de esquema masivo en `core`** permanece **aislada** para un hito futuro controlado. **No** se avanza a fórmulas LIMS (Punto 10) en este documento; solo se deja el perímetro y el inventario/cron **documentados y parcialmente cerrados en código**.

*Versión documento: 1.0*
