# Acceso total a `docs/audit/` y `docs/manual/`

**Propósito:** Estas carpetas son la **bitácora de auditoría** y los **manuales operativos** del proyecto. Deben ser legibles y editables por el Programador, por usuarios con permiso de repo, y por **asistentes de IA** (Cursor, etc.) sin bloqueos artificiales.

## Reglas en el repo

| Archivo | Qué garantiza |
| :--- | :--- |
| **`.cursorignore`** | `docs/**` ignorado **excepto** `docs/audit/` y **`docs/manual/`**, con refuerzo para `*.md` y, en manual, `*.txt`; en auditoría también `*.py` y `*.json`. |
| **`docs/audit/_cursorignore_snapshot.txt`** | Copia de **`.cursorignore`** para comprobar política de indexación sin abrir la raíz del repo. **Actualizar** con `Copy-Item .cursorignore docs/audit/_cursorignore_snapshot.txt` (PowerShell) cuando cambie el ignore. |
| **`.gitignore`** | No existe regla que ignore `docs/` completo; auditoría y manuales **se versionan** con `git add docs/audit/` y `git add docs/manual/` según corresponda. |

## Contenido típico (`docs/audit/`)

- `DOCS_AUDIT_MAESTRO.md` — bitácora maestra (actualizar tras cada cierre de tarea según §1.1 del propio documento).
- `TODO_CODE_SCAN.txt` — volcado de `TODO`/`FIXME`/`HACK`/`XXX` (regenerar con `python manage.py audit_dump_code_markers`).
- `INVENTARIO_URLS.txt` / `.meta.txt` — inventario de rutas Django.
- `FUNCIONES_EXHAUSTIVO_POR_RUTA.md`, `COMANDOS_MANAGE_PY.md`, `INFRA_ASYNC_Y_REALTIME.md` — anexos exhaustivos.
- `_regen_*.py` — scripts de regeneración de anexos.
- `INSTRUCCION_FINAL_PROGRAMADOR.md` — cierre operativo producción (HL7 y checklist).

## Contenido típico (`docs/manual/`)

- Manuales de módulo (p. ej. inventario federado) y apéndices (p. ej. fórmulas LIMS v7.5).

## Si una herramienta “no ve” un archivo aquí

1. Comprobar que el archivo esté bajo `docs/audit/` o `docs/manual/` (no `docs/otro/`).
2. Ejecutar `git check-ignore -v ruta/al/archivo`.
3. Comparar con `docs/audit/_cursorignore_snapshot.txt` y corregir `.cursorignore` si falta una línea `!docs/...`.
4. Recargar el proyecto en el IDE para que vuelva a indexar.
