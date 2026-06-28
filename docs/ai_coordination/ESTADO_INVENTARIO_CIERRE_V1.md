# INVENTARIO — Cierre del Módulo Post-Split

**Estado: CASI_CERRADO → CERRADO (revalidado 2026-06-27)**
**Fecha: 2026-06-27**

---

## Resumen

El módulo `inventario/` fue auditado tras su split en silos federados (Lab, Consultorio, Generales, Compras, Traspasos). El paquete está **estable, sin deuda operacional**.

---

## Validaciones Ejecutadas

| Comando | Resultado |
|---------|-----------|
| `python manage.py check` | 0 issues |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test inventario.tests.test_inventario --keepdb -v 1` | 31 tests OK |

---

## Estructura Verificada

- **`models/__init__.py`** — Re-exporta 18 modelos desde 6 submodules (base, lab, consultorio, generales, compras, logistica). `__all__` correcto.
- **`views/__init__.py`** — Re-exporta 36 views desde 6 submodules. `__all__` correcto.
- **`urls.py`** — 38 rutas en namespace `inventario`, sin rutas huérfanas ni stale.
- **`admin.py`** — Registro completo de todos los modelos de silo.
- **`apps.py`** — Conecta `inventario.signals` en `ready()`.
- **`signals.py`** — 4 receptores (Lab FEFO, Consultorio, Generales, CMMS). Solo excepciones tipadas (`DatabaseError`, `ValidationError`, `ObjectDoesNotExist`).
- **`concurrency.py`** — Retry helper con `OperationalError`/`IntegrityError` tipados.
- **`services/critical_stock.py`** — Agregación de stock sin excepciones amplias.
- **`management/commands/`** — 3 comandos sin `except Exception`.

---

## Deuda Corregida en Esta Sesión

### 1. `auditar_bom_consumo_reactivo.py` — except Exception → tipado

```diff
- except Exception:
+ except (OperationalError, ProgrammingError):
+     # Tabla no existe aún (pre-migración) — DB introspection falla.
```

**Justificación previa:** La introspección de BD puede fallar con diferentes excepciones según backend. Ahora se limita a las 2 excepciones documentadas.

### 2. `views/compras.py` — 2 imports rotos corregidos

```diff
- from .models import NotificacionDiscrepancia
+ from ..models import NotificacionDiscrepancia

- from .views import _get_empresa
+ from .helpers import _get_empresa
```

Estos imports fallaban en runtime al invocar `_recibir_mercancia` y `api_articulos_criticos`.

### 3. `views/traspasos.py` line 418 — import obsoleto eliminado

```diff
- from .views import _get_empresa
```

`_get_empresa` ya se importa en el nivel del módulo (línea 27) desde `.helpers`. El import inline apuntaba a `.views` (= `inventario.views.views`), que no existe.

---

## Excepciones Amplias — Inventario Completo (fuera migrations)

**Total `except Exception`: 0**

Todos los handlers de excepción en el módulo usan excepciones tipadas:
- `(DatabaseError, ValidationError)` en vistas CRUD
- `(DatabaseError, ValidationError, ObjectDoesNotExist)` en signals
- `(OperationalError, IntegrityError)` en concurrency retry
- `(OperationalError, ProgrammingError)` en introspección de BD

---

## Conclusión

El módulo `inventario` queda **CERRADO** — revalidado con tests frescos 2026-06-27.
