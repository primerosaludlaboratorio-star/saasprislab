# REPORTE AUDITORIA CODEX - 2026-06-20

## Alcance real ejecutado

- Verificacion tecnica base del proyecto local.
- Ejecucion de `manage.py check` y `makemigrations --check --dry-run`.
- Ejecucion parcial de pruebas unitarias y de regresion por bloques.
- Ejercicio directo de endpoints reales de laboratorio y consultorio usando `django.test.Client` bajo HTTPS.
- Revision de codigo de laboratorio, consultorio, almacenamiento Drive y Object Storage.
- Correccion puntual de hallazgos confirmados en buscador LIMS y payload de bitacora de laboratorio.

## Estado confirmado

### 1. Base tecnica

- `manage.py check` -> OK.
- `manage.py makemigrations --check --dry-run` -> OK.
- La suite via `pytest` no esta lista para coleccion directa sin bootstrap Django.
- La suite via `manage.py test` en Windows local sigue chocando con `UnicodeEncodeError` por salida Unicode durante migraciones / consola `cp1252`.

### 2. Laboratorio

Confirmado:

- El endpoint unificado `POST /laboratorio/api/crear-orden/` SI crea orden correctamente.
- El endpoint `GET /laboratorio/api/ordenes-recientes/` SI responde JSON correcto bajo HTTPS.
- La teoria de "todo laboratorio esta bloqueado por modo offline" NO quedo sustentada por evidencia tecnica local.

Hallazgos confirmados:

1. Busqueda operativa del catalogo LIMS tenia mala relevancia para aliases reales de trabajo:
   - `BH` no priorizaba `CITOMETRIA HEMATICA COMPLETA`.
   - `QS6` devolvia vacio.
2. La bitacora de recepcion consumia `orden.estado_icono` en frontend, pero el backend no mandaba esa clave.
3. Los endpoints de recepcion siguen marcando latencia alta con pocos queries:
   - `/api/pacientes/buscar/`
   - `/laboratorio/api/ordenes-recientes/`
   - `/laboratorio/api/crear-orden/`
   Esto apunta mas a costo de aplicacion / imports / middleware que a SQL puro.

Correcciones aplicadas:

- `core/lims_cart.py`
  - se agrego expansion de aliases operativos (`BH`, `QS3`, `QS4`, `QS6`, `QS12`, `QS19`, `QS32`, `EGO`)
  - se agrego ranking de resultados para priorizar coincidencias operativas
- `core/views/laboratorio.py`
  - `api_ordenes_recientes` ahora incluye `estado_icono` en el payload
- `core/tests/test_lims_cart_search.py`
  - nueva prueba para aliases LIMS
  - nueva prueba para payload de bitacora

Validacion manual posterior al fix:

- `search_lims_catalog('QS6')` ya devuelve `QUIMICA SANGUINEA 6`
- `search_lims_catalog('BH')` ya devuelve `CITOMETRIA HEMATICA COMPLETA`

### 3. Consultorio

Flujos ejercidos con cliente Django local:

- `POST /consultorio/api/crear-consulta-directa/` -> 200 OK
- `POST /consultorio/api/crear-paciente-y-consulta/` -> 200 OK
- `POST /consultorio/api/generar-certificado-inmediato/` -> 200 OK

Datos confirmados:

- Se genero `folio_consulta` real (`CONS-1-2026-00005` en prueba local).
- La consulta quedo persistida con medico asignado.
- El certificado inmediato se genero correctamente.

Conclusion:

- El modulo medico NO esta roto en su flujo base por endpoint.
- Sigue habiendo latencia alta de app incluso con pocas queries.

### 4. Farmacia

Estado actual de auditoria:

- Cobertura de regresion localizada:
  - `core/tests/test_devoluciones_farmacia_api.py`
  - `core/tests/test_farmacia_carga_masiva_excel.py`
- Riesgo arquitectonico sigue vigente:
  - existe flujo PDV en `core.views.farmacia`
  - existe flujo ERP en `farmacia/`
  - siguen coexistiendo rutas y modelos paralelos de devolucion

Conclusion:

- Farmacia sigue funcionalmente dividida en dos arboles.
- No se aplico unificacion arquitectonica en esta sesion.
- Este punto sigue siendo decision mayor, no parche pequeno.

### 5. Google Drive y almacenamiento

Confirmado en codigo:

- `config/drive_credentials.py` prioriza OAuth 2.0 y mantiene fallback a Service Account.
- `config/settings.py` deja `BufferLocalStorage` por defecto.
- Google Drive directo solo entra si:
  - hay credenciales validas
  - hay `GOOGLE_DRIVE_FOLDER_ID`
  - y se habilita `GOOGLE_DRIVE_DIRECT_STORAGE`
- Vultr Object Storage ya tiene arquitectura preparada:
  - `TenantS3Storage`
  - prioridad sobre Drive si esta completo

Estado real actual:

- En el entorno local de auditoria, Drive sigue en fallback local:
  - `No se encontraron credenciales validas para Google Drive`
- La integracion de Vultr Object Storage esta preparada en codigo, pero depende de variables reales en `.env` de produccion.

### 6. VPS / deploy

Se documento el estado real del servidor:

- codigo productivo en `/opt/prislab/app`
- no asumir repo en `/opt/prislab`
- si falta `.git`, la recuperacion validada es:
  - `git init`
  - `remote add`
  - `fetch --depth 1`
  - `reset --hard FETCH_HEAD`
  - reinicio de `prislab-gunicorn`, `prislab-celery`, `prislab-celerybeat`, `nginx`

Archivos de control actualizados localmente:

- `DEPLOY.md`
- `ACCESO_Y_DEPLOY_OPERATIVO_VPS.md`

## Hallazgos abiertos

### Criticos / altos

1. La automatizacion de pruebas en Windows sigue friccionada por `UnicodeEncodeError` durante `manage.py test`.
2. Farmacia sigue con doble arbol funcional (`core` vs `farmacia`).
3. Drive no puede marcarse como cerrado al 100% mientras no haya credenciales validas reales en el entorno destino.

### Medios

1. Latencia alta de endpoints operativos con bajo query count.
2. La suite `pytest` no esta lista para ejecutarse sola sin configurar Django.

## Archivos tocados en esta sesion

- `core/lims_cart.py`
- `core/views/laboratorio.py`
- `core/tests/test_lims_cart_search.py`
- `DEPLOY.md`
- `ACCESO_Y_DEPLOY_OPERATIVO_VPS.md`

## Recomendacion de siguiente bloque

1. Subir y desplegar los fixes de laboratorio y la documentacion operativa VPS.
2. Resolver la traba de ejecucion de tests en Windows (`UTF-8` / salida de migraciones).
3. Hacer siguiente ronda sobre farmacia con decision explicita:
   - unificar
   - o separar formalmente `PDV` y `ERP`
4. Cerrar Drive o Vultr Object Storage con variables reales de produccion y prueba de subida efectiva.
