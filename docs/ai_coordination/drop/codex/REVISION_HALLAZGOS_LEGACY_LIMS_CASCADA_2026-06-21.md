# Revision Codex - Hallazgos legacy LIMS reportados por Cascada - 2026-06-21

## Objetivo

Validar los hallazgos de Cascada sobre referencias legacy `detalle.estudio` / `detalles__estudio` antes de aplicar cambios.

## Resultado ejecutivo

La alerta fue util, pero no todo lo reportado corresponde a flujo activo de produccion.

Estado final:

- H1 templates criticos `detalle.estudio`: **parcial / no confirmado en ruta activa**.
- H2 `prefetch_related('detalles__estudio')`: **ya corregido en rutas activas**.
- H3 doble arquitectura farmacia: **confirmado como deuda arquitectonica**, no se corrige en parche minimo.

## Evidencia H1 - Templates de captura/resultados

Ruta activa en `config/urls.py`:

```python
path('laboratorio/captura/<int:orden_id>/', captura_views.captura_resultados_industrial, name='captura_resultados')
```

Vista activa:

```python
core.views.laboratorio_captura.captura_resultados_industrial
```

Template activo:

```text
core/templates/core/captura_resultados_industrial.html
```

La vista activa no depende de `detalle.estudio`. Construye un objeto seguro `item.estudio` con `_estudio_like(detalle)`:

```python
def _estudio_like(detalle):
    if detalle.analito_id:
        a = detalle.analito
        return SimpleNamespace(nombre=a.nombre, codigo=a.codigo or '', ...)
    return SimpleNamespace(nombre=detalle_orden_etiqueta(detalle), codigo='', ...)
```

Por eso, el uso de `{{ item.estudio.nombre }}` en el template activo es seguro.

## Evidencia H2 - Prefetch legacy

Se revisaron las rutas señaladas.

`pacientes/portal_views.py` actualmente usa:

```python
prefetch_related('detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims')
```

`consultorio/views_integracion_lab.py` en `ver_resultados_lab_en_consulta` actualmente usa:

```python
prefetch_related('detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims')
```

`core/utils/estandares_industriales.py` actualmente usa:

```python
prefetch_related('detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims')
```

No queda `prefetch_related('detalles__estudio')` en rutas activas revisadas.

## Legacy real detectado

`consultorio/views_integracion_lab.py` conserva codigo legacy para crear ordenes desde consulta usando `Estudio` y `DetalleOrden(estudio=...)`.

El propio archivo declara:

```text
LEGACY / NO CABLEADO EN urls.py (2026)
```

Busqueda de rutas:

```text
No hay referencia a crear_orden_lab_desde_consulta en config/urls.py ni core/urls.py.
```

Conclusion: no esta activo en produccion, pero si se reconecta en el futuro debe migrarse a `analito`, `perfil_lims` y `paquete_lims` antes de exponerlo.

## Decision de ingenieria

No se aplico parche sobre templates activos porque el flujo actual ya esta usando compatibilidad segura.

No se toca `consultorio/views_integracion_lab.py` en esta ronda porque:

- No esta cableado en URLs.
- Es un modulo legacy declarado.
- Tocar esa integracion requiere decision funcional sobre preordenes LIMS desde consulta.

## Estado

Clasificacion final:

- `detalle.estudio` en flujo activo de captura: **NO CONFIRMADO**.
- `detalles__estudio` en rutas activas revisadas: **CERRADO / YA MIGRADO**.
- `consultorio/views_integracion_lab.py`: **LEGACY NO CABLEADO / PENDIENTE SI SE REACTIVA**.

## Recomendacion siguiente

Si se quiere reactivar integracion Consultorio -> Laboratorio:

1. No usar `Estudio` legacy.
2. Recibir tokens LIMS (`analito`, `perfil_lims`, `paquete_lims`).
3. Crear `DetallePreOrden` o `DetalleOrden` con esos campos.
4. Agregar pruebas contra `DetalleOrden` sin campo `estudio`.
