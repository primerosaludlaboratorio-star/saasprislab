# MANTENIMIENTO (CMMS) — Cierre del Módulo Post-Split

**Estado: CERRADO**
**Fecha: 2026-06-27**

---

## Resumen

El módulo `mantenimiento/` fue auditado tras su split a paquetes (`models/`, `views/`). El paquete está **estable, sin deuda operacional en superficie (views/signals)**.

---

## Validaciones Ejecutadas

| Comando | Resultado |
|---------|-----------|
| `python manage.py check` | 0 issues |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test mantenimiento.tests --keepdb -v 1` | 4 tests OK |

---

## Estructura Verificada

- **`models/__init__.py`** — Re-exporta 17 modelos + 8 constantes desde 7 submodules (base, gemelo, biblioteca, ejecucion, tickets, tco, metrologia, iot, incca). `__all__` correcto.
- **`views/__init__.py`** — Re-exporta desde 6 submodules (helpers, director, operativo, tco, qr, api, metrologia).
- **`urls.py`** — 24 rutas en namespace `mantenimiento`, sin rutas huérfanas.
- **`admin.py`** — Registro completo con inlines (PasoProtocolo, NodoDiagnostico, RespuestaPaso, SalidaRefaccion, PasoReparacion).
- **`apps.py`** — Conecta `mantenimiento.signals` en `ready()`.
- **`signals.py`** — 2 receptores (SalidaRefaccion auditoría, LecturaSensorIoT alertas). Solo excepciones tipadas (`DatabaseError`, `ValidationError`).

---

## Deuda Corregida en Esta Sesión

### 1. `views/metrologia.py` line 281 — except Exception → tipado

```diff
- except Exception:
+ except (json.JSONDecodeError, ValueError):
```

En `api_iot_lectura()`, el `json.loads(request.body)` capturaba cualquier excepción. Ahora se limita a las 2 excepciones que `json.loads` realmente lanza.

### 2. `views/api.py` — import faltante de `_empresa`

Se agregó `from .helpers import _empresa, _req_empresa` que faltaba, lo que causaría `NameError` al invocar `api_checklist_bloqueado` o `api_stock_lote_para_refaccion`.

---

## Excepciones Amplias — Superficie Operativa (views + signals)

**Total `except Exception` en views/signals: 0**

Todos los handlers de excepción en la superficie operativa usan excepciones tipadas:
- `(DatabaseError, ValidationError)` en vistas CRUD (director, operativo, metrologia)
- `(DatabaseError, ValidationError)` en signals (IoT alertas)
- `SiloNoSoportadoError`, `LoteModel.DoesNotExist` en API views
- `(json.JSONDecodeError, ValueError)` en API IoT endpoint

---

## Deuda Residual No-Operativa (Management Command)

`management/commands/sync_incca_csv.py` conserva 2 `except Exception` (líneas 207, 224) en su loop de procesamiento batch de archivos CSV. Estos son **justificados**:
- Línea 207: Catch-all en loop por-archivo para que un archivo corrupto no aborte el batch completo. Cualquier error de I/O, encoding, o parsing queda aislado.
- Línea 224: Catch-all interior para no fallar al registrar el propio evento de error en BD.

Ambos son en un **command de ingesta offline**, no en superficie operativa.

---

## Conclusión

El módulo `mantenimiento` queda **CERRADO** sin deuda operacional en views/signals. La única deuda residual está en un management command de ingesta (no-operativo) y es justificada como boundary de batch processing.
