# Módulo Farmacia — Reporte Cascada — 2026-06-24

## Objetivo
Revisar, refactorizar donde aplique, clasificar evidencia, contradicciones, legacy y ruido del módulo Farmacia contra el canon oficial.

---

## Alcance — archivos revisados

| Archivo | Tamaño | Revisado |
|---------|--------|----------|
| `farmacia/__init__.py` | 172 B | ✅ |
| `farmacia/apps.py` | 406 B | ✅ |
| `farmacia/signals.py` | 3.9 KB | ✅ |
| `farmacia/forms.py` | 14.6 KB | ✅ (estructura) |
| `farmacia/models.py` | 52.4 KB | ✅ (estructura e imports) |
| `farmacia/tests.py` | 14.2 KB | ✅ corrido |
| `farmacia/urls.py` | 4.4 KB | ✅ |
| `farmacia/views/__init__.py` | 53.5 KB | ✅ (imports, clases principales) |
| `farmacia/views/soporte.py` | 32.5 KB | ✅ |
| `farmacia/views/corte_caja_api.py` | 2.6 KB | ✅ |
| `farmacia/views/semaforo.py` | 5.2 KB | ✅ |
| `farmacia/services/__init__.py` | 60 B | ✅ |
| `farmacia/services/venta_farmacia_service.py` | 293 B | ✅ |
| `farmacia/services/corte_caja_unificado.py` | 10.4 KB | ✅ |
| `farmacia/services/alertas.py` | 10.8 KB | ✅ |
| `farmacia/services/impresora_termica.py` | 8.7 KB | ✅ |
| `farmacia/management/commands/` | 8 archivos | ✅ (clasificados) |
| `core/services/ventas/venta_farmacia_service.py` | 58 KB | ✅ (dominio real) |

---

## Evidencia encontrada

### 1. Arquitectura de servicios — ALINEADA AL CANON

La migración v8.5 Fase 2 movió el dominio PDV a `core/services/ventas/venta_farmacia_service.py`.  
`farmacia/services/venta_farmacia_service.py` es un **shim de compatibilidad** correcto:
```python
from core.services.ventas.venta_farmacia_service import VentaFarmaciaService, ejecutar_venta_pdv
__all__ = ['VentaFarmaciaService', 'ejecutar_venta_pdv']
```
`farmacia/services/__init__.py` también re-exporta lo mismo. Consistente. Sin cambio necesario.

### 2. Signals — ALINEADAS

`farmacia/apps.py` tiene `ready()` correcto:
```python
def ready(self):
    try:
        import farmacia.signals
    except ImportError:
        pass
```
La signal `post_save` sobre `CierreTurnoFarmacia` usa `dispatch_uid` único — no hay riesgo de registro doble.  
El `fail_silently=True` en `send_mail` evita que un fallo de correo rompa el flujo. **Correcto.**

### 3. Tests — 18/18 PASANDO

```
Ran 18 tests in 18.162s — OK
```
El monkey-patch de `_store_rendered_templates_safe` para Python 3.14 + Django 5.0.x está bien estructurado — `_dj_test_client` importado antes de usarse. No es legacy ni ruido.

### 4. Comandos de carga — RUIDO / DUPLICACIÓN DOCUMENTAL

Hay 3 variantes de carga de inventario con solapamiento funcional:

| Comando | Formato | Estado |
|---------|---------|--------|
| `cargar_inventario.py` | CSV | Operativo (usa `tenant_strict`) |
| `cargar_inventario_excel.py` | XLSX (openpyxl) | Operativo |
| `cargar_productos_csv.py` | CSV | Probable overlap con `cargar_inventario.py` |
| `cargar_productos_farmacia.py` | Mixto | Probable overlap |
| `cargar_productos_pandas.py` | CSV/XLSX vía pandas | Herramienta alternativa |
| `importar_excel_inventario.py` | XLSX (más completo, 23 KB) | Más completo que `cargar_inventario_excel.py` |

**Clasificación:** `importar_excel_inventario.py` es el más completo y reciente. Los demás son variantes de distintas fases del proyecto. No se eliminan sin autorización del usuario — se marcan como **LEGACY_CANDIDATE** para revisión.

### 5. `corte_caja_api.py` — import lazy correcto

El servicio `cerrar_turno_unificado` se importa dentro de la función, no a nivel de módulo:
```python
# corte_caja_api.py:52
from farmacia.services.corte_caja_unificado import cerrar_turno_unificado
```
Patrón correcto para evitar dependencias circulares.

### 6. `views/__init__.py` — 53 KB como vista monolítica

Este archivo contiene todas las vistas del módulo en un solo archivo de 53 KB. Funciona y los tests pasan, pero es un candidato a refactorización en módulos separados en una ronda futura. **No se toca ahora sin autorización** — no hay bug, solo deuda estructural.

---

## Clasificación — Legacy / Ruido / Canon

| Elemento | Clasificación | Acción |
|----------|--------------|--------|
| `farmacia/services/venta_farmacia_service.py` | CANON — shim de compatibilidad | Sin cambio |
| `farmacia/services/__init__.py` | CANON | Sin cambio |
| `farmacia/signals.py` | CANON — activo, signal conectada | Sin cambio |
| `farmacia/apps.py` | CANON | Sin cambio |
| `farmacia/tests.py` (18 tests) | CANON | Sin cambio |
| `importar_excel_inventario.py` | CANON — más completo | Sin cambio |
| `cargar_inventario.py` | LEGACY_CANDIDATE | Marcar, no eliminar |
| `cargar_inventario_excel.py` | LEGACY_CANDIDATE | Marcar, no eliminar |
| `cargar_productos_csv.py` | LEGACY_CANDIDATE | Marcar, no eliminar |
| `cargar_productos_farmacia.py` | LEGACY_CANDIDATE | Marcar, no eliminar |
| `cargar_productos_pandas.py` | LEGACY_CANDIDATE | Marcar, no eliminar |
| `views/__init__.py` (53 KB monolítico) | DEUDA_ESTRUCTURAL | No tocar sin autorización |

---

## Contradicciones detectadas

**Ninguna.** La arquitectura de servicios está alineada: dominio real en `core/services/ventas/`, acceso desde farmacia vía shim de compatibilidad. Tests confirman alineación en runtime.

---

## Cambios aplicados

**Ninguno.** El módulo Farmacia está alineado al canon. Los 18 tests pasan. No hay desalineación que requiera corrección inmediata.

Los 5 comandos de carga legacy son **candidatos a archivado**, no a eliminación — requieren decisión del usuario.

---

## Riesgos detectados

| Riesgo | Severidad | Estado |
|--------|-----------|--------|
| 5 comandos de carga con overlap funcional | BAJO | Documentado — LEGACY_CANDIDATE |
| `views/__init__.py` monolítico de 53 KB | BAJO — deuda estructural | Documentado, sin cambio |
| `corte_caja_unificado` llama a `impresora_termica` en runtime — si el socket TCP falla, el corte puede quedar a medias | MEDIO | Existente, fuera de alcance de esta ronda |

---

## Qué quedó cerrado

- Arquitectura de servicios farmacia confirmada como alineada al canon v8.5.
- 18/18 tests pasando — sin regresión.
- Signals correctamente conectadas.
- Clasificación de todos los comandos de carga.

---

## Qué quedó pendiente

- Decisión del usuario sobre archivado de 5 comandos LEGACY_CANDIDATE.
- Refactorización de `views/__init__.py` (53 KB) a módulos separados — deuda estructural, requiere autorización.

---

## Siguiente módulo

**Laboratorio** — según plan de reparto modular.

---

## Para Codex

- **Sin cambios de código en este módulo.** Todo alineado.
- Pendiente de usuario: decisión sobre archivado de `cargar_inventario.py`, `cargar_inventario_excel.py`, `cargar_productos_csv.py`, `cargar_productos_farmacia.py`, `cargar_productos_pandas.py`.
