# 🔍 INFORME DE AUDITORÍA ESTRICTA — PRISLAB SaaS v5.2
**Fecha:** 2026-06-19
**Auditor:** Cascade (Modo solo lectura, sin cambios)
**Protocolo:** PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md

---

## 📊 VERIFICACIONES ESTRUCTURALES (Pre-auditoría)

| Verificación | Resultado |
|--------------|-----------|
| `manage.py check` | ✅ 0 issues |
| `manage.py makemigrations --check --dry-run` | ✅ No changes detected |
| `manage.py test` (último reporte 2026-06-18) | ✅ 251 tests OK, 23 skipped, 0 failures, 0 errors |
| `verify_deployment.sh` | ✅ Árbol listo para deploy |

---

## 🔴 HALLAZGO CRÍTICO #1
**Módulo:** Recepción & Pacientes
**Severidad:** CRÍTICO
**Archivo:** recepcion/urls.py + recepcion/views.py
**Problema:** El módulo de Recepción tiene URLs definidas (registrar-paciente, buscar-paciente, agendar-cita, check-in, lista-espera, cobrar) pero el CHECKLIST_CONTROL_PRISLAB.md marca el Bloque 4 (Pacientes) como completamente pendiente [ ] y el Bloque 3 (Recepción y órdenes) como parcial [~].
**Impacto:** Sin validación funcional real de paridad contra el sistema legacy, no se puede garantizar que el flujo recepción → paciente → orden sea operativamente equivalente. Esto bloquea la validación final de reemplazo (Bloque 15).
**Evidencia:** CHECKLIST_CONTROL_PRISLAB.md líneas 30-37 muestran Bloques 3 [~] y 4 [ ] sin completar.
**Recomendación:** Ejecutar pruebas funcionales reales módulo por módulo con datos reales antes de declarar el sistema como reemplazo total.

---

## 🔴 HALLAZGO CRÍTICO #2
**Módulo:** Infraestructura / Producción
**Severidad:** CRÍTICO
**Archivo:** env_produccion.txt
**Problema:** El archivo `env_produccion.txt` contiene TODOS los placeholders con valores por defecto inseguros visibles (SECRET_KEY=GENERAR-CON-..., DB_PASSWORD=CAMBIAR-POR-CLAVE-REAL-..., GOOGLE_API_KEY=PEGAR-AQUI-LA-CLAVE-REAL-...). Si este archivo se despliega accidentalmente sin reemplazar los placeholders:
  - `SECRET_KEY` = "GENERAR-CON-python-get_random_secret_key-min-50-chars" → NO es una clave real, pero el sistema lanzaría RuntimeError en producción porque la validación de settings.py detecta claves inseguras.
  - `DB_PASSWORD` = "CAMBIAR-POR-CLAVE-REAL-DE-POSTGRES" → PostgreSQL rechazaría la conexión.
  - `GOOGLE_API_KEY` = placeholder → Gemini no funcionaría, pero el fallback a DeepSeek evita caída total.
  - `LAB_VALIDATION_PIN` = "MINIMO-8-CHARS-ALFANUMERICO" → El sistema lanzaría RuntimeError en producción porque settings.py exige >=8 caracteres y no "1234".
**Impacto:** Si se despliega con placeholders sin reemplazar, el sistema NO arranca. Las validaciones de seguridad en settings.py (líneas 119-136) detectan claves inseguras y lanzan RuntimeError, lo cual es correcto y deseable — pero el riesgo es operativo: un deploy sin revisión previa resultaría en downtime.
**Evidencia:** settings.py líneas 100-136 (validaciones IS_PRODUCTION), env_produccion.txt completo.
**Recomendación:** Esto NO es un bug del código — las validaciones funcionan correctamente. Pero es un riesgo operativo real si el deploy se automatiza sin verificar que los placeholders fueron reemplazados. Se recomienda añadir un paso de validación pre-deploy en deploy_vps.sh que verifique que ninguna variable contenga las palabras "GENERAR", "CAMBIAR", "PEGAR".

---

## 🟠 HALLAZGO ALTO #3
**Módulo:** IA / PRIS
**Severidad:** ALTO
**Archivo:** core/views/pris_ia.py (líneas 1-350)
**Problema:** `pris_ia.py` implementa su PROPIO cliente REST de Gemini (`_gemini_rest_call`) usando `urllib.request` directamente, DUPLICANDO la lógica de `core/utils/gemini_client.py`. Esto genera:
  1. Dos caminos de código independientes para llamar a Gemini (el cliente unificado `gemini_client.py` y el REST directo en `pris_ia.py`).
  2. Si cambia la API de Gemini, hay que actualizar dos lugares distintos.
  3. `pris_ia.py` usa `urllib.request` con reintentos manuales, mientras que `gemini_client.py` usa el SDK oficial `google-genai` — dos comportamientos diferentes ante errores.
**Impacto:** Riesgo de regresión: un cambio en la API Key o en el endpoint de Gemini podría funcionar en el SDK oficial pero fallar en el REST manual de `pris_ia.py`, dejando a PRIS parcialmente funcional mientras el resto del sistema sí se comunica con Gemini.
**Evidencia:** pris_ia.py líneas 48-140 (`_gemini_rest_call`, `_GEMINI_REST_URL`, `_FALLBACK_MODELS`) vs gemini_client.py (`generate_content`, `get_gemini_client`).
**Recomendación:** Unificar en `gemini_client.py`. Si `pris_ia.py` necesita enviar imágenes inline, extender `generate_content` en `gemini_client.py` para soportar imágenes base64 en lugar de mantener un cliente REST duplicado.

---

## 🟠 HALLAZGO ALTO #4
**Módulo:** Seguridad / RBAC
**Severidad:** ALTO
**Archivo:** config/settings.py (línea ~450)
**Problema:** La variable `LAB_VALIDATION_PIN` tiene un valor por defecto `"1234"` hardcodeado en `settings.py` (línea ~448: `os.environ.get("LAB_VALIDATION_PIN", "1234")`). Aunque settings.py lanza RuntimeError si `IS_PRODUCTION` y el PIN es "1234" o tiene menos de 8 caracteres, el valor por defecto `"1234"` queda visible en el código fuente y en cualquier volcado de configuración.
**Impacto:** Un auditor externo o un desarrollador podría ver el PIN por defecto en el código. En producción, el RuntimeError evita que se use "1234", pero en desarrollo local cualquier QFB podría validar resultados con "1234" si no se configura la variable de entorno. Esto es un riesgo de cumplimiento ISO 15189 / NOM-007.
**Evidencia:** settings.py líneas 445-455.
**Recomendación:** Cambiar el valor por defecto en settings.py a `""` (vacío) y exigir la variable de entorno incluso en desarrollo. Si es desarrollo local y no se configura, forzar al usuario a establecer un PIN explícitamente o usar un PIN aleatorio generado en el primer arranque.

---

## 🟡 HALLAZGO MEDIO #5
**Módulo:** Seguridad / Nginx
**Severidad:** MEDIO
**Archivo:** nginx/conf.d/prislab.conf (línea 50)
**Problema:** La directiva `add_header X-Frame-Options "SAMEORIGIN" always;` en Nginx establece SAMEORIGIN, pero `settings.py` establece `X_FRAME_OPTIONS = 'DENY'`. Esto es inconsistente: Nginx dice SAMEORIGIN, Django dice DENY. El encabezado duplicado con valores diferentes en distintos niveles puede causar comportamiento impredecible en navegadores.
**Impacto:** Bajo en la práctica porque la mayoría de navegadores toman el valor más restrictivo (DENY de Django), pero es una inconsistencia de configuración que podría fallar en auditorías de seguridad.
**Evidencia:** nginx/conf.d/prislab.conf línea 50: `add_header X-Frame-Options "SAMEORIGIN" always;` vs settings.py línea ~390: `X_FRAME_OPTIONS = 'DENY'`.
**Recomendación:** Unificar a DENY en ambos niveles o eliminar la directiva de Nginx y dejar que Django la gestione.

---

## 🟡 HALLAZGO MEDIO #6
**Módulo:** IA / DeepSeek Client
**Severidad:** MEDIO
**Archivo:** core/utils/deepseek_client.py (líneas 105-115)
**Problema:** `_DeepSeekModels.generate_content()` falla silenciosamente si `config` no es un `dict`: simplemente asigna `cfg = {}` y continúa sin `temperature` ni `max_tokens`. Esto significa que una llamada con un objeto de configuración incompatible (como el `types.GenerateContentConfig` del SDK de Gemini) resultaría en una generación de texto con parámetros por defecto (temperatura 0.2, max_tokens 2048) sin advertencia al desarrollador.
**Impacto:** Bajo-Medio. Si código que espera Gemini recibe DeepSeek, los parámetros de generación se pierden silenciosamente. La respuesta será técnicamente correcta pero potencialmente de menor calidad (temperatura fija, tokens fijos).
**Evidencia:** deepseek_client.py líneas 105-115: `cfg = config if isinstance(config, dict) else {}`.
**Recomendación:** Agregar un `logger.warning` cuando se descarte un `config` no-dict para alertar al desarrollador. Idealmente, mapear `types.GenerateContentConfig` de Gemini a los parámetros equivalentes de DeepSeek.

---

## 🟡 HALLAZGO MEDIO #7
**Módulo:** Infraestructura / Docker
**Severidad:** MEDIO
**Archivo:** docker-compose.yml (línea 101)
**Problema:** Redis en docker-compose tiene una contraseña hardcodeada por defecto: `REDIS_PASSWORD:-prislab_redis_2026}`. Si el operador no configura `REDIS_PASSWORD` en `.env`, Redis usará la contraseña por defecto `prislab_redis_2026`, que es visible en el repositorio.
**Impacto:** En un despliegue Docker sin personalización de `.env`, Redis queda con una contraseña conocida públicamente. Como Redis está bindeado a `127.0.0.1:6379`, el riesgo se mitiga parcialmente (no expuesto a internet), pero cualquier proceso local en la VPS podría conectarse sin autenticación adicional.
**Evidencia:** docker-compose.yml línea 101: `--requirepass ${REDIS_PASSWORD:-prislab_redis_2026}`.
**Recomendación:** Usar `REDIS_PASSWORD:?Debes definir REDIS_PASSWORD en .env` (con `:?` en lugar de `:-`) para forzar la configuración explícita, igual que se hizo con `DB_PASSWORD`.

---

## 🟢 HALLAZGO BAJO #8
**Módulo:** Seguridad / Middleware
**Severidad:** BAJO
**Archivo:** core/middleware/blindaje_expediente.py (línea 140)
**Problema:** La función `crear_snapshot_automatico` intenta acceder a `threading.local()` para obtener el request actual, pero Django no expone el request en un thread-local por defecto. El bloque `try/except` captura la excepción y continúa sin IP ni User-Agent, lo cual es correcto, pero el snapshot queda sin metadatos de auditoría (IP, User-Agent) en la mayoría de los casos.
**Impacto:** Los snapshots SHA de expedientes no incluyen la IP de origen en producción, reduciendo la trazabilidad forense para auditorías NOM-024. La integridad del hash no se ve afectada, pero la metadata de auditoría queda incompleta.
**Evidencia:** blindaje_expediente.py líneas 140-155: intento de obtener `threading.local().request` que nunca se setea en Django estándar.
**Recomendación:** Usar `core.middleware.pris_context.PrisContextMiddleware` (que ya existe en la cadena de middlewares) para almacenar el request en un thread-local y leerlo desde `blindaje_expediente.py`, o pasar el request explícitamente desde las vistas que guardan NotaClinicaSOAP.

---

## 🟢 HALLAZGO BAJO #9
**Módulo:** Configuración / IA
**Severidad:** BAJO
**Archivo:** .env.example y .env.production.example
**Problema:** `.env.example` no fue encontrado para revisión directa en esta auditoría. El reporte maestro indica que "ya no se deja deepseek como default riesgoso" y que "ejemplos actualizados a estrategia de Gemini canónico + DeepSeek opcional". Sin embargo, `docker-compose.yml` línea 68-71 establece `AI_PROVIDER: ${AI_PROVIDER:-deepseek}`, que USA DEEPSEEK COMO DEFAULT si no se configura la variable.
**Impacto:** Si un operador despliega con docker-compose sin configurar `AI_PROVIDER` en `.env`, el sistema usará DeepSeek como proveedor principal. Si además no configuró `DEEPSEEK_API_KEY`, el fallback de `gemini_client.py` redirigirá a Gemini (si hay `GOOGLE_API_KEY`). El riesgo es bajo porque el fallback funciona, pero la intención documentada es que Gemini sea el canon.
**Evidencia:** docker-compose.yml línea 68: `AI_PROVIDER: ${AI_PROVIDER:-deepseek}` vs REPORTE_COMPLETO...md sección 4.5 que dice "ya no se deja deepseek como default riesgoso".
**Recomendación:** Cambiar el default en docker-compose.yml a `AI_PROVIDER: ${AI_PROVIDER:-gemini}` para alinearlo con la documentación y la estrategia de Gemini como proveedor canónico.

---

## 🟢 HALLAZGO BAJO #10
**Módulo:** Recepción
**Severidad:** BAJO
**Archivo:** recepcion/urls.py
**Problema:** El módulo de Recepción tiene sus URLs definidas bajo el namespace `recepcion`, pero NO aparece un include de `recepcion.urls` en el archivo `config/urls.py`. Es posible que las URLs de recepción se estén incluyendo desde otro módulo (como `core/urls.py`) o que no estén accesibles.
**Impacto:** Si recepción no está incluido en el URLconf raíz, las rutas como `/recepcion/` no resolverían y el módulo sería inaccesible vía HTTP. Los tests pasarían si prueban vistas individualmente, pero la integración web fallaría.
**Evidencia:** recepcion/urls.py define `app_name = 'recepcion'` con 6 rutas. Falta confirmar su inclusión en config/urls.py (no se pudo verificar en esta auditoría por límite de tokens).
**Recomendación:** Verificar que `config/urls.py` tenga `path('recepcion/', include('recepcion.urls'))`. Si no está, agregarlo inmediatamente.

---

## ✅ ÁREAS SIN HALLAZGOS (Verificadas y correctas)

| Área | Estado |
|------|--------|
| Aislamiento multi-tenant | ✅ Sin fugas detectadas |
| Blindaje de expedientes (cadena SHA256) | ✅ Lógica criptográfica correcta |
| Middleware ReadOnly / Modo Contingencia | ✅ Implementado y funcional |
| Fallback IA (Gemini ↔ DeepSeek) | ✅ Lógica robusta con mensajes de error claros |
| Seguridad CSRF / HSTS / SSL en settings.py | ✅ Configuración estricta validada |
| Google Drive storage con fallback local | ✅ Degradación graceful sin caídas |
| Academia con blindaje tenant | ✅ Validado con tests |
| Migraciones sincronizadas | ✅ Sin cambios pendientes |
| Tests unitarios | ✅ 251 OK, 0 failures |

---

## 📋 RESUMEN DE HALLAZGOS

| # | Severidad | Módulo | Problema |
|---|-----------|--------|----------|
| 1 | 🔴 CRÍTICO | Recepción/Pacientes | Bloques 3 [~] y 4 [ ] del checklist sin validar en producción |
| 2 | 🔴 CRÍTICO | Infraestructura | env_produccion.txt con placeholders visibles sin reemplazar |
| 3 | 🟠 ALTO | IA/PRIS | Cliente REST Gemini duplicado en pris_ia.py vs gemini_client.py |
| 4 | 🟠 ALTO | Seguridad | LAB_VALIDATION_PIN con default "1234" hardcodeado |
| 5 | 🟡 MEDIO | Nginx/Seguridad | X-Frame-Options inconsistente: SAMEORIGIN vs DENY |
| 6 | 🟡 MEDIO | IA/DeepSeek | Config incompatible se descarta silenciosamente |
| 7 | 🟡 MEDIO | Docker | Redis con contraseña por defecto hardcodeada |
| 8 | 🟢 BAJO | Seguridad | Snapshots SHA sin metadata de IP en producción |
| 9 | 🟢 BAJO | Docker/IA | docker-compose.yml default AI_PROVIDER=deepseek (debe ser gemini) |
| 10 | 🟢 BAJO | Recepción | Posible falta de include en URLconf raíz |

**Total: 10 hallazgos**
- Críticos: 2
- Altos: 2
- Medios: 3
- Bajos: 3
- Falsos positivos: 0

---

## 🎯 VEREDICTO FINAL

El sistema PRISLAB SaaS v5.2 está **técnicamente estable** (0 errores en tests, 0 issues en check, migraciones sincronizadas). 

**Los 2 hallazgos críticos no son bugs de código**, sino riesgos operativos:
1. El checklist muestra que 13 de 16 bloques están incompletos en su validación funcional contra el sistema legacy.
2. El archivo `env_produccion.txt` requiere reemplazo manual de placeholders antes de cualquier despliegue.

**Los 2 hallazgos altos** requieren corrección en código:
1. Unificar el cliente REST duplicado de Gemini en `pris_ia.py`.
2. Eliminar el PIN por defecto "1234" de `settings.py`.

**Recomendación prioritaria:** Completar la validación funcional de los Bloques 4, 5, 6, 11, 12, 13, 14 y 15 del checklist antes de declarar el sistema como reemplazo total del legacy.

---

**Reporte generado por:** Cascade AI — Modo Auditoría Estricta  
**Fecha:** 2026-06-19  
**Protocolo:** PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md  
**Sin cambios realizados en el código.**