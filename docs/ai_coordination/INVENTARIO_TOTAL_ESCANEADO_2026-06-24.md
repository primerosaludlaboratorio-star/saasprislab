# INVENTARIO TOTAL DEL PROYECTO — Escaneo real (no memoria)

**Generado por:** Claude · **Fecha:** 2026-06-24
**Base:** árbol `release/v1.0-local` (`f3e43e9` + trabajo interno) · **Método:** introspección Django + escaneo AST + resolver de URLs. **Todas las cifras provienen de escanear el árbol, no de recuerdos.**
**Alcance:** TODO el proyecto preexistente, no solo lo trabajado por las IAs.

> Nota de honestidad: este documento mapea **estructura completa** (módulos, modelos, endpoints, comandos, tests, runners, legado). La semántica función-por-función vive en el código; aquí queda el **índice exhaustivo de qué existe y dónde**, para que nada sea invisible. Debe reconciliarse con `INDICE_CANONICO_TOTAL.md` (Codex) cuando se persista.

---

## 1. Resumen global (cifras reales)

| Métrica | Valor |
|---|---|
| Archivos versionados | **1.890** |
| Python (`.py`) | 974 |
| Templates HTML | 407 |
| Docs Markdown | 269 |
| JS / MJS | 27 / 10 |
| Apps Django locales | **18** |
| **Modelos** | **240** |
| Funciones (def) | **3.567** |
| Clases | **1.228** |
| Métodos de test (`test_*`) | **342** (en apps) |
| Archivos de test en repo | **98** |
| **Comandos de gestión** | **164** |
| Templates | 390 (en apps) |
| **Endpoints URL** | **1.847** (1.067 admin auto + ~780 de apps) |
| Endpoints API (`/api/`) | **256** |

---

## 2. Inventario por app (escaneo AST + introspección)

| App | .py | funcs | clases | modelos | tests | cmds | templates |
|---|---:|---:|---:|---:|---:|---:|---:|
| academia | 17 | 34 | 18 | 4 | 5 | 1 | 2 |
| bienestar | 14 | 21 | 11 | 2 | 0 | 1 | 9 |
| consultorio | 24 | 159 | 67 | 17 | 36 | 0 | 35 |
| contabilidad | 25 | 62 | 26 | 4 | 14 | 1 | 6 |
| **core** | **476** | **2.392** | **659** | **109** | **215** | **123** | **199** |
| enfermeria | 9 | 9 | 5 | 0 | 0 | 0 | 6 |
| farmacia | 36 | 168 | 50 | 8 | 19 | 9 | 14 |
| inventario | 32 | 119 | 63 | 18 | 4 | 3 | 35 |
| iot | 11 | 15 | 11 | 3 | 0 | 0 | 1 |
| laboratorio | 61 | 192 | 112 | 28 | 17 | 13 | 6 |
| lims | 36 | 114 | 32 | 5 | 0 | 8 | 10 |
| logistica | 10 | 40 | 22 | 5 | 6 | 0 | 8 |
| mantenimiento | 18 | 74 | 64 | 19 | 0 | 2 | 22 |
| marketing | 19 | 45 | 26 | 6 | 6 | 0 | 10 |
| pacientes | 13 | 36 | 15 | 3 | 4 | 0 | 13 |
| recepcion | 8 | 10 | 5 | 0 | 0 | 0 | 7 |
| reglas_negocio | 11 | 27 | 15 | 2 | 11 | 0 | 0 |
| seguridad | 11 | 50 | 27 | 7 | 5 | 0 | 7 |
| **TOTAL** | **831** | **3.567** | **1.228** | **240** | **342** | **161** | **390** |

> `core` concentra el 57% del código y el 45% de los modelos: es el monolito real del sistema. Apps `enfermeria`, `recepcion`, `iot`, `bienestar` casi no tienen tests.

---

## 3. Superficie de URLs (lo que el programa expone)

**1.847 endpoints** totales. Sin contar el admin Django (1.067 auto-generados), la superficie de aplicación es ~780 rutas, **256 de ellas API**.

Top prefijos (módulo → nº endpoints): `laboratorio` 118 · `consultorio` 68 · `api` 61 · `farmacia` 54 · `silo-lab`(inventario) 50 · `lims` 42 · `mantenimiento` 32 · `director` 24 · `bienestar` 21 · `pacientes` 18 · `contabilidad` 17 · `marketing` 16 · `seguridad` 15 · `ia` 14 · `pris` 14 · `crm` 14 · `medico` 14 · `finanzas` 13 · `logistica` 11 · `capacitacion` 10 · `rh` 10 · `notificaciones` 9 · `nomina` 9 · `asistencia` 8.

> Cada uno de estos prefijos es un flujo funcional verificable. La auditoría en vivo (human:ui) debe recorrerlos; hoy solo PDV está en cola.

---

## 4. Comandos de gestión (164) — superficie operativa "oculta"

`core` tiene **123** comandos. Una porción grande son comandos de **auditoría que ya existían en el repo** y que aparentemente no se usaban de forma sistemática, p.ej.:
`audit_system`, `audit_roles`, `audit_tenant_readiness`, `auditar_sistema`, `auditar_rutas`, `auditar_multitenant_async`, `auditoria_coherencia_total`, `auditoria_core_full`, `auditoria_farmacia_full`, `auditoria_lab_full`, `auditoria_medico_full`, `auditoria_qa`, `auditoria_secuencial`, `auditoria_botones_pantallas`, `bankguard_audit`, `audit_dump_code_markers`…
Otros: `arranque_frio`, `backup_database`/`backup_db_drive`/`backup_nocturno`, `anclar_hashes_diarios`, `backfill_*` (lotes, movimientos caja, ventas inventario).

Resto por app: laboratorio 13, farmacia 9, lims 8, inventario 3, mantenimiento 2, academia/bienestar/contabilidad 1 c/u.

> **Hallazgo de meta-auditoría:** el repo **ya traía herramientas de auditoría** (comandos + `tools/audit_url_inventory.py`, `tools/audit_coverage_gate.py`, `tools/audit_data_integrity.py`) que nunca se ejecutaron como parte de las "auditorías totales" pedidas. Eso explica que cosas (como los tests) quedaran invisibles.

---

## 5. Tests y runners (incluye los "tests ocultos")

- **98 archivos de test** en el repo · **342 métodos `test_*`** en apps.
- Suites/runners existentes (no documentados antes como canon):
  - `tools/run_omni_suite.mjs` (omni:local/cloud/both, Playwright).
  - `scripts_cascade_e2e/`: `_e2e_pdv_audit.mjs`, `octogono_ui_audit.mjs`, `playwright_auth.mjs` (+ carpeta `output/` con placeholder y capturas).
  - `scripts_cursor_e2e/`: **suite de fiabilidad de 12 tests** (`test_01_guardian_golden_lifecycle` … `test_09_sucursal_modo_inventario_ui`, `test_robot_chemist_flows`) + `run_cursor_reliability_suite.py`.
  - `tools/audit_*.py` (inventario URL, coverage gate, integridad de datos).
- Herramienta humana nueva (Codex, local, **sin push aún**): `tools/run_human_ui_audit.mjs` / `run_human_ui_audit.bat`.

> Estos `scripts_cursor_e2e/test_0X_*` son justo el tipo de "tests que existían y nadie veía" hasta que se buscaron explícitamente.

---

## 6. Legado / ruido detectado (para purga o canon)

- Carpetas legado: `scripts_legacy/`, `core/management/commands/_archive_legacy/`.
- **115 archivos `.py`** con marcadores `DEPRECATED/OBSOLET/LEGACY/no usar`.
- ~269 documentos `.md` en raíz (muchos reportes históricos de "auditoría/completado" cuya autenticidad ya se cuestionó en rondas previas).

> Decisión pendiente (carril Codex): por cada uno → **borrar / conservar como legado / promover a canon**.

---

## 7. Huecos / qué falta cubrir (verificación real, no estática)

| Frente | Estado |
|---|---|
| PDV / farmacia (login→venta→cancel→devolución→corte) | **PENDIENTE_VALIDAR** (espera salida real de human:ui) |
| ~780 endpoints de aplicación recorridos en vivo | mayoría **sin** verificación humana UI |
| Apps sin tests (enfermeria, recepcion, iot, bienestar) | sin cobertura |
| Cobertura global | baja (~25-34% medida en rondas previas) |
| Reportes `.md` históricos | autenticidad parcial / a reconciliar |

---

## 8. Método (reproducible)

Cifras obtenidas con:
- `git ls-files` (conteo y extensiones).
- Django `apps.get_models()` (modelos), `get_resolver()` (endpoints).
- `ast` sobre cada `.py` (funcs/clases/tests).
- `find`/`glob` para comandos, templates, runners y legado.

Cualquiera puede re-ejecutar el escaneo y obtener los mismos números. Este documento es el **mapa base**; el detalle vivo está en el código, los tests y los runners listados.
