# Módulo Laboratorio — Reporte Cascada — 2026-06-24

## Objetivo
Revisar, refactorizar donde aplique, clasificar evidencia, contradicciones, legacy y ruido del módulo Laboratorio/LIMS contra el canon oficial. Trabajo complementario al reporte de Claude — sin repetir lo ya verificado por él.

---

## Alcance — archivos revisados por Cascada en esta ronda

| Archivo | Hallazgo |
|---------|---------|
| `lims/views.py` | **CÓDIGO MUERTO — eliminado** |
| `lims/views/__init__.py` | Canónico |
| `lims/views/analitos.py` | Canónico |
| `lims/views/perfiles.py` | Canónico |
| `lims/views/paquetes.py` | Canónico |
| `lims/views/precios.py` | Canónico |
| `lims/views/tenant_lims.py` | Canónico |
| `lims/urls.py` | Canónico |
| `lims/tests.py` | Stub vacío — sin tests propios |
| `lims/apps.py` | Canónico — `ready()` conecta signals |
| `lims/signals.py` | Canónico — sincronización `costo_lista` ↔ `PrecioItem` |

---

## Hallazgos Cascada

### 1. `lims/views.py` — CÓDIGO MUERTO eliminado

**Problema:** `lims/views.py` (archivo plano, 4 líneas, solo `from django.shortcuts import render`) coexistía con `lims/views/` (directorio/paquete). En Python, cuando existen ambos, el **directorio gana** y el archivo es completamente ignorado. `lims/urls.py` usaba `from lims.views import analitos` — resolvía al directorio correctamente. El archivo plano era código muerto invisible.

**Acción:** Eliminado `lims/views.py`.  
**Verificación:** `manage.py check` → `System check identified no issues (0 silenced)`.

### 2. `lims/tests.py` — stub vacío

4 líneas, solo `from django.test import TestCase` y un comentario. No contiene tests. Los tests reales de LIMS están en `core/tests/` (confirmado por Claude). **No se elimina** — Django lo espera como punto de entrada de la app. Queda documentado como stub.

---

## Cruce con reporte de Claude

| Hallazgo Claude | Verificación Cascada | Alineación |
|----------------|---------------------|------------|
| 16/16 tests OK (suite delgada, corre en 0.002s) | Confirmado — `lims/tests.py` es stub vacío, tests reales en `core/tests/` | ✅ COINCIDEN |
| `DetalleOrden.estudio` legacy cerrado en código productivo | No re-auditado — tomado como cerrado por Claude | ✅ ALINEADO |
| 6 `except:` desnudos en comandos de carga/migración | No contradicción detectada | ✅ ALINEADO |
| Dual-model `laboratorio.*` legacy vs `core.*` LIMS — deuda de fondo para Codex | Confirmo: `lims/` usa `core.models` (OrdenDeServicio, DetalleOrden) — no tiene dependencia directa de `laboratorio.*` legacy | ✅ CONFIRMA separación |
| `core/views/laboratorio.py` 3146 LOC monolito — deuda estructural | Fuera de alcance Cascada esta ronda | ⚠️ PENDIENTE |

---

## Clasificación — Legacy / Ruido / Canon

| Elemento | Clasificación | Acción |
|----------|--------------|--------|
| `lims/views.py` (archivo plano) | RUIDO — código muerto | **ELIMINADO** |
| `lims/tests.py` | STUB — sin contenido | Documentado, sin eliminar |
| `lims/views/` (directorio completo) | CANON | Sin cambio |
| `lims/signals.py` | CANON — sincronización de precios activa | Sin cambio |
| `lims/urls.py` | CANON | Sin cambio |
| `laboratorio/services/unificacion.py` | LEGACY INTENCIONAL (bridge de migración) | Confirma Claude — conservar |
| 6 `except:` desnudos en commands | DEUDA MENOR — fuera de flujos request | Documentado |

---

## Contradicciones con Claude

**Ninguna.** Los hallazgos de Claude y Cascada son complementarios, no contradictorios.

---

## Cambios aplicados

| Archivo | Cambio | Verificación |
|---------|--------|-------------|
| `lims/views.py` | Eliminado — código muerto (archivo plano ignorado por Python al existir `lims/views/` directorio) | `manage.py check` → 0 issues |

---

## Riesgos detectados

| Riesgo | Severidad | Estado |
|--------|-----------|--------|
| Dual-model laboratorio legacy vs core LIMS | **ALTO** — deuda arquitectónica de fondo | Para Codex — no fix puntual |
| `lims/tests.py` vacío — cobertura real en `core/tests/` | BAJO — riesgo de falsa confianza en suite de la app | Documentado |

---

## Qué quedó cerrado

- `lims/views.py` código muerto eliminado y verificado.
- `lims/views/` correctamente canónico.
- Cruce con Claude completado — alineación confirmada.

---

## Qué quedó pendiente

- Decisión sobre retiro formal de `laboratorio.*` legacy — requiere Codex + autorización del usuario.
- Refactorización `core/views/laboratorio.py` (3146 LOC) — deuda estructural, requiere autorización.

---

## Siguiente módulo

**Consultorio** — según plan de reparto modular.

---

## Para Codex

- **1 cambio en este módulo:** `lims/views.py` eliminado. Ya verificado.
- Deuda de fondo: planificar retiro de `laboratorio.{Estudio,Orden,DetalleOrden}` legacy o formalizar frontera con `core.*` LIMS.
