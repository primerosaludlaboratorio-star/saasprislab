# VEREDICTO_LIMS_CASCADE — Auditoría externa pasiva (READ-ONLY)

**IA/Auditor:** Cascade (Windsurf)  
**Modo:** Hunter — Solo Lectura  
**Alcance:** Módulos **6.3 (Laboratorio)** y **6.4 (LIMS App)** (evidencia en repo).  
**Fecha:** 2026-04-02

---

## Fallas Arquitectónicas (riesgos graves / código inescalable)

### 1) Catálogo clínico duplicado (3 “mundos” coexistiendo)
- **`core.models.catalogos`** contiene `Estudio`, `Parametro`, `RangoReferencia` (catálogo “SaaS dinámico”).
- **`laboratorio.models`** contiene `Estudio`, `Parametro`, `Orden`, etc. (catálogo y orden “legacy”).
- **`lims.models`** contiene `Analito`, `ValorReferenciaAnalito`, `PerfilLims`, `PaqueteLims`, `PrecioItem` (catálogo 4 niveles v7.5).

**Evidencia / impactos observables**
- En flujos de orden/captura se mezcla:
  - `core.models.Estudio` como fuente principal.
  - fallback a `laboratorio.models.Estudio` con **auto-migración** hacia `core.models.Estudio` al crear orden (`core/views/laboratorio.py` → `crear_orden_servicio`).
  - en captura/validación clínica se usa `core.models.Parametro` para persistir `core.models.laboratorio.ResultadoParametro`, pero la validación ISO 15189 utiliza `laboratorio.models.Parametro` resolviendo por **nombre** (`core/views/laboratorio.py` → `api_guardar_resultados` bloque ISO).

**Riesgo**
- Inconsistencias de nomenclatura (mismo parámetro con nombre diferente) rompen:
  - validación ISO 15189
  - alertas críticas
  - integración HL7/ASTM (mapeos)
- Complejidad operativa: Usuarios pueden “configurar” en dos o tres pantallas diferentes y obtener resultados distintos.

### 2) Doble escritura de resultados (fuente de verdad ambigua)
**Evidencia**
- `core/views/laboratorio.py` → `api_guardar_resultados`:
  - escribe `DetalleOrden.resultado` y `DetalleOrden.observaciones`
  - y además `ResultadoParametro.update_or_create(...)`.
  - existe comentario explícito de migración (“Fase 2”) y comando citado `migrar_resultados_legacy` que **no está presente** en repo (deuda ya reconocida en `DOCS_AUDIT_MAESTRO`).

**Riesgo**
- Divergencia de datos: el PDF y/o UI podrían leer de una u otra tabla según pantalla.
- Auditoría forense (y trazabilidad clínica ISO) se complica: ¿qué campo se considera “oficial”?

### 3) Validación clínica por rangos: dos motores paralelos
**Motores detectados**
- Motor ISO 15189: `laboratorio/services/iso15189.py` basado en `laboratorio.models.RangoReferenciaParametro` (si existe) con fallback a rangos estáticos en `laboratorio.models.Parametro`.
- Captura industrial (`core/views/laboratorio_captura.py`) pre-carga:
  - rangos en `core.models.RangoReferencia` (via `parametro.rangos_referencia`)
  - y “rangos ISO” desde `laboratorio.models.RangoReferenciaParametro`, pero mapeando por **nombre del parámetro**.

**Riesgo**
- El sistema puede mostrar rangos y/o marcar anormalidad usando un set, pero disparar alertas críticas usando otro set.

### 4) Diseño de inventario/reactivos: dos mecanismos que no se ven entre sí
**Hallazgo**
- Existe `laboratorio.models.InsumoEstudio`: relación Estudio→Producto con `cantidad` y `es_critico`.
- Pero el descuento automático real de reactivos se implementa en `inventario/signals.py` escuchando `post_save(core.ResultadoParametro)`:
  - usa `ConsumoEstudioReactivo`, `LoteReactivoLab`, `SalidaAnaliticaLab` (modelos del silo inventario).
  - aplica FEFO y crea `SalidaAnaliticaLab` por `parametro` validado.

**Riesgo**
- `InsumoEstudio` parece un “cerebro” declarado, pero no se observó como fuente de descuento en el flujo principal.
- Potencial duplicación: si en el futuro alguien activa consumo por `InsumoEstudio` + ya existe consumo por `ConsumoEstudioReactivo`, se descuenta doble.

### 5) Escalabilidad / rendimiento (hotspots)
- `core/views/laboratorio.py` es un archivo monolítico muy grande (múltiples endpoints críticos en un solo módulo).
- En `lims/views/precios.py` hay `PrecioItem.objects.filter(...).exists()` dentro de loop para cada analito (potencial N+1 a gran escala), aunque en esta auditoría solo se reporta como riesgo.
- `laboratorio/services/iso15189.py` dispara alertas en un thread daemon por evento crítico (no hay cola/retry; riesgo de pérdida silenciosa).

---

## Fugas de Seguridad / Datos (brechas de aislamiento)

### 1) Configuración de catálogo (LIMS SaaS dinámico) sin control de permisos robusto
**Evidencia**
- `core/views/laboratorio_config.py`:
  - Múltiples vistas de configuración (`lista_pruebas`, `configurar_prueba`, `configurar_rangos`, `api_rangos_parametro`, `api_buscar_parametros`) tienen **solo `@login_required`**.
  - El único control fuerte observado es en `api_soft_delete_parametro`: exige `is_superuser` o `is_staff`.

**Impacto**
- Cualquier usuario autenticado (incl. roles no clínicos) podría potencialmente:
  - crear/editar estudios
  - editar parámetros
  - versionar rangos

Esto es una brecha severa de integridad clínica (alteración del catálogo afecta interpretación de resultados y PDF).

### 2) Catálogo `core.Estudio` y `core.Parametro` parecen globales (sin `empresa`)
**Evidencia**
- En `core/views/tarifas.py` se afirma explícitamente: “**Estudio no tiene campo empresa; catálogo global**”.
- En el modelo `core.models.catalogos.Estudio` y `Parametro` (segmento revisado), no se observa `empresa`.

**Riesgo / fuga**
- Si el sistema es multi-tenant, un catálogo global puede ser válido solo si está intencionalmente compartido.
- Pero entonces la **edición** del catálogo por una empresa impacta a todas (riesgo de sabotaje o error humano cross-tenant).

### 3) LIMS App v7.5 (`lims`) sin multi-tenant
**Evidencia**
- `lims.models` no incluye `empresa`.
- `lims.views.*` valida permisos por rol/grupo, pero no hay scoping por empresa.

**Riesgo**
- Si dos empresas usan el mismo deployment, el catálogo v7.5 es compartido.
- Un usuario autorizado en una empresa puede modificar precios/perfiles/paquetes que afectan otra.

### 4) Riesgo de bypass por “tenant context” en modelos TenantModel
**Evidencia**
- Existe un framework `core/tenant.py` con `TenantModel` y managers con bypass.

**Riesgo**
- Si se usan `objects_all` o `tenant_bypass()` en vistas sin un control adicional, se abre fuga de datos.
- En los fragmentos críticos revisados (órdenes/cobro/guardar resultados) se filtra explícitamente por `empresa`, lo cual mitiga parcialmente.

---

## Deuda Clínica y Técnica (lógica frágil o incompleta)

### 1) Cálculo de edad/rangos pediátricos inconsistente
**Evidencia**
- `core/views/laboratorio_captura.py` calcula edad en **años** (resta de años, sin meses/días).
- ISO 15189 dinámico en `laboratorio/services/iso15189.py` usa edad como Decimal (años) pero si `edad` es None, default `30`.

**Riesgo clínico**
- Pediatría y neonatos requieren rangos por días/meses; convertir a “años redondeados” es clínicamente riesgoso.
- Default de 30 años en ISO (cuando no hay edad) puede clasificar incorrectamente.

### 2) Validación numérica “deprecada” en estudio vs parámetros
**Evidencia**
- `api_guardar_resultados` valida numericidad usando `estudio.valor_minimo` (marcado como DEPRECADO en `core.models.catalogos.Estudio`).

**Riesgo**
- La validación puede ser inconsistente con el verdadero tipo de dato de `Parametro` (NUMERICO/TEXTO/...)

### 3) Mapeo ISO 15189 por nombre
**Evidencia**
- En `api_guardar_resultados`, se toma `core.ResultadoParametro.parametro.nombre` y se busca un `laboratorio.Parametro` por nombre.

**Riesgo**
- Cambios de nombre rompen alertas críticas.
- Homónimos entre secciones producen match incorrecto.

### 4) Flujo de consumo de reactivos ligado a validación de parámetro
**Evidencia**
- `inventario/signals.py`: descuenta FEFO al guardar `core.ResultadoParametro` con `validado=True`.

**Riesgo**
- Si una orden se valida con resultados parciales o se re-valida, el mecanismo depende de deduplicación por `SalidaAnaliticaLab` (existe) pero el diseño es sensible a re-ediciones.
- No se encontró integración explícita con `laboratorio.InsumoEstudio`.

### 5) Alertas críticas: canal externo sin garantías
**Evidencia**
- `laboratorio/services/iso15189.py` envía Telegram con `urllib.request` en thread daemon.

**Riesgo**
- Sin retry/circuit breaker, se puede perder notificación sin persistencia formal.

---

## Veredicto y Recomendación de Cirugía (plan propuesto, sin implementarlo)

### Severidad general
- **Laboratorio (6.3):** Riesgo **ALTO** por doble escritura, motores de rangos múltiples y validación clínica parcialmente deprecada.
- **LIMS App (6.4):** Riesgo **ALTO** en multi-tenant/seguridad si el deployment es SaaS multi-empresa; riesgo **MEDIO** si el despliegue es single-tenant.

### Cirugía recomendada (pasos propuestos)
1) **Definir una única fuente de verdad de catálogo clínico**
   - Elegir entre:
     - `core.Estudio/core.Parametro/core.RangoReferencia` (catálogo dinámico), o
     - `lims.Analito` (v7.5), y definir un “bridge” claro hacia órdenes/resultados.
   - Congelar (read-only) los otros catálogos o migrarlos.

2) **Eliminar doble escritura de resultados**
   - Hacer `ResultadoParametro` canónico.
   - Migrar `DetalleOrden.resultado` a derivado o eliminarlo.
   - Crear el comando real `migrar_resultados_legacy` (o retirar su referencia).

3) **Reforzar permisos en `core/views/laboratorio_config.py`**
   - Todas las vistas de configuración deben requerir rol/grupo explícito (ej. `DIRECTOR_QC`/`LIMS`/`ADMIN`).
   - Logging forense de cambios de catálogo (quién cambió qué rango, cuándo, desde qué IP).

4) **Aislamiento multi-tenant del catálogo**
   - Si el catálogo debe ser por empresa, agregar `empresa` y migración.
   - Si el catálogo es global, bloquear edición a superusuarios globales y aplicar workflow de cambios.

5) **Unificar consumo de reactivos/insumos**
   - Decidir si el “cerebro” es `laboratorio.InsumoEstudio` o `inventario.ConsumoEstudioReactivo`.
   - Eliminar/archivar el no usado o crear sincronización formal para evitar doble descuento.

6) **Rangos pediátricos/neonatales**
   - Cambiar edad a unidad consistente (días/meses/años) y aplicar rangos por unidad.
   - Evitar default de 30 años cuando no hay edad: marcar como “edad desconocida” y requerir validación manual.

---

## Instrucción de Cierre

**Cascade** — *"He analizado el contexto. Entro en Modo Hunter de Solo Lectura. Procedo a generar el Veredicto del Laboratorio y LIMS"*.
