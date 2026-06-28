# Legacy Boundary — Cierre Fase 0 v8.5 (Core + laboratorio)

**Versión:** 1.0  
**Audiencia:** Jonathan, auditores, ingeniería.  
**Alcance:** Estado tras `core.0074_pagoorden_empresa_tenant_guard` y `lims` alineado (0007b/0008).  
**Política:** Sin squash de migraciones en caliente; cadena lineal en el sentido de **grafo acíclico** Django (puede haber *merge migrations*).

---

## 1. Inventario de migraciones `core`

| Métrica | Valor |
|--------|--------|
| Archivos `0xxx_*.py` en `core/migrations/` | **74** (recuento físico en repo) |
| Hoja actual del grafo (`showmigrations`) | **`core.0074_pagoorden_empresa_tenant_guard`** |
| Nota | El número “~45” de planes anteriores era orientativo; el históreal acumulado en `core` es mayor. |

---

## 2. ¿La cadena es aplicable de forma lineal y segura en producción?

### 2.1 Linealidad (Django)

- El planificador de Django aplica migraciones en **orden topológico** respetando `dependencies`.
- En `core` existen **nodos de fusión** (varios padres), lo cual es **normal** y no impide `migrate`:
  - `core.0001_initial` ← `auth` + `consultorio` (arranque estándar).
  - `core.0003_migrar_datos_laboratorio` ← `core.0002` + `laboratorio.0002`.
  - `core.0058_resultadoparametro_analito_lims` ← `core.0057` + `lims.0006`.
  - `core.0059_expediente_blindaje_v20` ← `core.0058` + `lims.0001_initial`.
  - `core.0068_detalleorden_lims_fk_columns` ← `core.0067` + `lims.0007`.
  - **`core.0073_conveniopreciolims_and_legacy_lab_drop`** ← `core.0072` + **`inventario.0007`** + **`lims.0007`** (orden crítico: inventario y LIMS deben estar al día antes de 0073).

No se requiere squash: basta **misma rama de código + `migrate`** en ventana de mantenimiento y backup previo.

### 2.2 Riesgos de datos (equivalente “estrategia LIMS”)

| Migración | Riesgo | Mitigación ya en código |
|-----------|--------|-------------------------|
| **`core.0058`** | Backfill masivo `ResultadoParametro` → `lims.Analito`; deduplicación y borrado de RP duplicados; **`atomic = False`** en Postgres por triggers/ALTER. | Placeholder `__PRISLAB_MIG_0058__` si no hay catálogo; revisar resultados tras import LIMS real. |
| **`core.0068` / `0069`** | Columnas legacy `estudio_id` en `DetalleOrden`; drops idempotentes vía SQL. | `SeparateDatabaseAndState` / `DROP COLUMN IF EXISTS` donde aplica. |
| **`core.0072` + `0073`** | Eliminación de `unique_together` y **borrado de modelos** `core.Estudio`, `core.Parametro`, `core.RangoReferencia`, etc. | Requiere que **no** queden FKs huérfanas en aplicación; dependencias `inventario` + `lims` forzadas en 0073. |

Si en producción aparece un fallo análogo a LIMS (datos que impiden NOT NULL o DeleteModel), la estrategia aprobada es: **migración intermedia solo DDL nullable + comando de amnistía de datos + migración final**, sin relajar el semáforo `audit_tenant_readiness`.

### 2.3 Confirmación operativa

Tras alinear dependencias (`lims`, `inventario`, `mantenimiento`, etc.), el criterio de “core limpio” para Fase 0 es:

1. `python manage.py migrate --noinput` sin error.  
2. `python manage.py audit_tenant_readiness` → **VERDE**.

---

## 3. Modelos legacy eliminados del estado Django (`core`)

Eliminados en **`core.0073_conveniopreciolims_and_legacy_lab_drop`** (ya no existen en `core.models` ni en el estado de migraciones):

| Modelo eliminado | Rol anterior |
|------------------|--------------|
| **`core.Estudio`** | Catálogo “maestro” de estudios en core (sustituido por flujo LIMS + catálogo `laboratorio.Estudio` donde aplica). |
| **`core.Parametro`** | Parámetro clínico ligado a estudio core (sustituido por `lims.Analito` + `core.ResultadoParametro.analito`). |
| **`core.RangoReferencia`** | Rangos ligados a `core.Parametro` (sustituidos por `lims.ValorReferenciaAnalito` y rangos en `laboratorio`). |
| **`core.ConvenioPrecioEstudio`** | Precios por convenio sobre estudio core → **`core.ConvenioPrecioLims`**. |
| **`core.SeccionLaboratorio`** | Secciones del catálogo legacy. |

**No** se usa `managed = False` para estos: fueron **borrados del estado**; las tablas físicas desaparecen al aplicar la migración (salvo restos documentados en SQL manual — fuera de alcance ORM).

---

## 4. Modelos “vivos” que sustituyen o conviven

| Necesidad | Modelo canónico actual |
|-----------|-------------------------|
| Catálogo operativo recepción / UI clásica lab | **`laboratorio.Estudio`** (y perfiles `laboratorio.PerfilLaboratorio`) |
| Ingeniería de analitos, perfiles/paquetes comerciales | **`lims.Analito`**, **`lims.PerfilLims`**, **`lims.PaqueteLims`**, **`lims.PrecioItem`** |
| Resultados en órdenes core | **`core.ResultadoParametro`** con **`analito`** → LIMS |
| Detalle de línea en orden | **`core.DetalleOrden`**: FKs **`analito`**, **`perfil_lims`**, **`paquete_lims`** (sin `estudio` core) |
| Rangos por analito | **`lims.ValorReferenciaAnalito`**; **`laboratorio.RangoReferenciaParametro`** para HL7/legacy interfaz |

---

## 5. Código y rutas: uso residual vs roto

### 5.1 Referencias seguras (try/except o tabla opcional)

- **`core/catalog.py`**: `_buscar_estudio_legacy` importa `core.models.Estudio` dentro de `try/except` → **no rompe** si el modelo no existe (retorna `None`).
- **`lims/management/commands/purgar_lims.py`**: cuenta tablas legacy con `try/except` → **`n/a`** si la tabla ya no existe.

### 5.2 Módulos corregidos en Fase 0 (import roto)

- **`core/management/commands/setup_roles.py`**: importaba `Estudio` desde `core.models` → **corregido** a **`laboratorio.models.Estudio`** (permisos Django sobre el catálogo que sí existe).
- **`core/views/catalogos_maestros.py`**: import muerto de `core.Estudio` → eliminado (solo se usa `laboratorio.Estudio`).
- **`core/views/paquetes.py`**: usaba `core.Estudio` → **corregido** a **`laboratorio.Estudio`** + `import json`.

### 5.3 Deuda P1 — refactor LIMS pendiente (no enlazado a URLs hoy)

| Archivo | Problema |
|---------|----------|
| **`consultorio/views_integracion_lab.py`** | Importaba `core.Estudio` y crea `DetalleOrden` con `estudio=…`; **`DetalleOrden.estudio` ya no existe**. El módulo **no** está registrado en `consultorio/urls.py` → no carga al arrancar rutas, pero **sí** es deuda si se vuelve a cablear. **Acción futura:** crear detalles con `analito` / `perfil_lims` / `paquete_lims` según API del consultorio. |

### 5.4 Herramientas / scripts legacy (solo desarrollo o archivo)

| Ruta | Nota |
|------|------|
| `core/management/commands/seed_parametros_lab.py` | Documentación y código referencian `core.Parametro` **eliminado** → comando obsoleto; no usar en prod hasta reescritura LIMS. |
| `core/management/commands/_archive_legacy/*` | Archivo; no parte del runtime. |
| `scripts_legacy/`, `smoke_test.py` | Pueden importar `core.Estudio`; actualizar o excluir de CI. |

### 5.5 HL7 y laboratorio

- **`laboratorio/views/hl7_receptor.py`**: usa **`laboratorio.Parametro`** y **`core.ResultadoParametro`** — coherente con boundary (no depende de `core.Parametro` eliminado).

---

## 6. Lectura “solo lectura” y `managed=False`

- Los modelos eliminados en **0073** no están en modo lectura: **dejaron de existir en el ORM**.  
- **No hay** compromiso de “solo lectura” que preserve tablas: la migración las elimina del esquema Django.  
- El sistema **no** se rompe **siempre que** no queden imports o FKs en código activo; los puntos corregidos arriba y la lista P1 cubren el riesgo residual.

---

## 7. Cierre Fase 0 — criterio “Core listo”

- [x] Cadena `core` documentada hasta **0074** con dependencias cruzadas (`lims`, `inventario`) explícitas.  
- [x] Riesgos de datos identificados (0058, 0073).  
- [x] Legacy Boundary documentado (modelos muertos vs vivos).  
- [x] Imports críticos de `setup_roles` / vistas huérfanas corregidos o clasificados.  
- [ ] **Pendiente consciente:** `consultorio/views_integracion_lab.py` y `seed_parametros_lab.py` — siguiente sprint antes de exponer rutas o ejecutar comandos.

**Listo para Fase 1 (Blindaje):** sí, desde el punto de vista de migraciones y semáforo, una vez `audit_tenant_readiness` verde en el entorno objetivo.

---

*Documento generado como entregable de cierre Fase 0 v8.5 — Cursor.*
