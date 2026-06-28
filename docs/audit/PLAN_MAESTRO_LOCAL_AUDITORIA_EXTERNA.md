# PRISLAB SaaS — Plan maestro (local primero) y guía para auditorías externas

**Versión:** 1.0  
**Alcance temporal:** Todo el trabajo descrito aquí asume **entorno local** hasta que el sistema funcione de forma estable en ese contexto. **No se incluyen acciones obligatorias sobre producción** en esta fase; las verificaciones y cambios en cloud se harán **después**, con baseline tomado de este documento.

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

## 2. Inventario del sistema (contexto para auditores)

### 2.1 Stack técnico

| Capa | Tecnología principal |
|------|----------------------|
| Framework | Django 5.x |
| API estructurada | Django Ninja (`api/v3/`) |
| BD desarrollo típica | SQLite (según `config/settings.py` si no hay `DB_HOST`) |
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
3. Quality Gate de tests (o subconjunto acordado) en verde en máquina reproducible (idealmente Docker).  
4. Lista de `[WARN]` de `verificar_funcionalidades` **explicada** (dato ausente vs bug).  
5. Informe corto interno: “Flujos críticos probados manualmente” con capturas o notas por dominio (Fase D).

---

## 8. Contacto y custodia del documento

- **Custodio sugerido:** responsable de calidad / release.  
- **Frecuencia de revisión:** al cerrar cada sprint o antes de auditoría externa.  
- **Control de versiones:** cambios vía mismo repositorio (PR con revisión).

---

*Fin del documento — solo planificación y auditoría; sin obligación de cambios en producción en esta etapa.*
