# Módulo Core — Reporte Cascada — 2026-06-24

## Objetivo
Revisar el módulo Core contra el canon oficial, aplicar correcciones con evidencia, documentar desalineaciones y riesgos.

---

## Alcance — archivos revisados

- `core/middleware/__init__.py`
- `core/middleware/pris_context.py` ← **cambio aplicado**
- `core/middleware/admin_access_restrict.py`
- `core/middleware/performance.py`
- `core/agent/pris_agent.py`
- `config/settings.py` líneas 235-263 (bloque MIDDLEWARE)

---

## Evidencia encontrada

### 1. Riesgo crítico — import a nivel de módulo en middleware

`pris_context.py` importaba `get_pris_context` a nivel de módulo:
```python
from core.agent.pris_agent import get_pris_context  # línea 11
```
Cualquier error en `pris_agent.py` al arrancar Django rompía **cada request del sistema**, no solo la funcionalidad IA.

### 2. `admin_access_restrict.py` — alias de compatibilidad

Archivo de 173 bytes. Solo re-exporta `AdminAccessMiddleware` desde `admin_access.py`. No está en `settings.py`. Correcto — es un shim de compatibilidad para auditorías que referencian el nombre antiguo.

### 3. `core/middleware/__init__.py` — no exporta `pris_context`

`PrisContextMiddleware` no está en `__init__.py`. Settings lo referencia directamente como `core.middleware.pris_context.PrisContextMiddleware`. Consistente — no requiere cambio.

### 4. Settings usa notación mixta para middlewares

- Corta (`core.middleware.EmpresaIdentityMiddleware`) — válido porque `__init__.py` lo exporta.
- Larga (`core.middleware.pris_context.PrisContextMiddleware`) — válido porque no está en `__init__`.
- Sin inconsistencia real — Django resuelve ambas formas correctamente.

---

## Cambios aplicados

### `core/middleware/pris_context.py`

**Antes:** import a nivel de módulo — si `pris_agent` falla al importar, cae todo el sistema.

**Después:** import lazy en `__init__` con `try/except`. Si falla, `request.pris_context = {}` y el sistema sigue funcionando. El error queda en el log.

Verificación: `manage.py check` → `System check identified no issues (0 silenced)`.

---

## Riesgos detectados

| Riesgo | Severidad | Estado |
|--------|-----------|--------|
| Import a nivel de módulo en `pris_context.py` | CRÍTICO | **RESUELTO** |
| `admin_access_restrict.py` solo re-exporta — puede confundir futuras auditorías | BAJO | Documentado, sin cambio |

---

## Qué quedó cerrado

- Riesgo crítico de import en middleware de contexto PRIS. **Corregido y verificado.**

---

## Qué quedó pendiente

- `core/views/` tiene 81 archivos — no se revisaron en esta ronda. Próximo módulo (Farmacia) tiene overlap con `core/views/farmacia.py` e `core/views/inventario.py` — revisar en esa ronda.
- `core/services/` — servicios IA ya clasificados en PARTE 15 del inventario. Sin cambios de código pendientes en esta ronda.
- `core/management/commands/` — 169 comandos no revisados individualmente. Los de smoke/herramienta IA ya clasificados.

---

## Siguiente módulo sugerido

**Farmacia** — según el plan de reparto modular.

---

## Para Codex

Único cambio de código en este módulo:
- `core/middleware/pris_context.py` — import lazy con fallback. Ya verificado con `manage.py check`. Listo para commit.
