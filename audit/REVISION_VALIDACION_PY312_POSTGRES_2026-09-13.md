# Revisión independiente — Validación Python 3.12.14 / PostgreSQL

**Fecha:** 2026-09-13
**Alcance:** revisar con ejecución real los puntos de
`audit/VALIDACION_PY312_POSTGRES_2026-09-13.md` y entregar evidencia de
comandos, tiempos, traceback y resultado final. No se usó la base productiva
ni se modificaron credenciales existentes.

**Conclusión ejecutiva:** la validación **no es "no concluyente por bloqueo"**.
El runner Django **sí completa** la creación del esquema de pruebas y ejecuta
las pruebas sobre PostgreSQL; el problema es **latencia por round-trip del túnel
SSH**, no un deadlock ni un defecto funcional. Con Python 3.12.14 real, la
batería dirigida pasa 8/8. La suite total es impracticable a través del túnel
(607 casos sólo en `core/tests`, ~10 transacciones/minuto), no por bloqueo.

---

## 1. Ejecución con Python 3.12.14

### Estado previo (reproduce el hallazgo del documento)

- `py -0p` registra `-V:3.12 -> C:\Users\jonil\AppData\Local\Programs\Python\Python312\python.exe`,
  pero el binario **no existe**:
  `py -3.12 --version` → `El sistema no puede encontrar el archivo especificado`.
- El venv existente `.venv_py312` está **roto**: `pyvenv.cfg` apunta a
  `C:\Users\jonil\AppData\Roaming\uv\python\cpython-3.12.14-windows-x86_64-none`
  (directorio eliminado).
- No hay `psql` ni `docker` locales.

### Reproducción corregida

```bash
py -m pip install uv                 # uv 0.12.13
py -m uv python install 3.12.14      # "Installed Python 3.12.14 in 8.30s"
py -m uv venv --python 3.12.14 .venv_py312_review
py -m uv pip install --python .venv_py312_review/Scripts/python.exe -r requirements.lock
```

Resultado (119 paquetes):

```text
python 3.12.14
django 5.2.17
psycopg 3.3.4
```

```text
$ manage.py check
System check identified no issues (0 silenced).
```

---

## 2. Creación de la base temporal Django sobre PostgreSQL

### Servidor (VPS, read-only en producción)

- SSH autentica como **`root@216.238.89.243`** (clave `~/.ssh/prislabprod`).
  Nota: el usuario por defecto de `scripts/deploy_local_to_vps.ps1` (`prislab`)
  está desactualizado; la autenticación real es `root`.
- Ubuntu 26.04, Python 3.14.4 (no 3.12), PostgreSQL 18.6.
- `listen_addresses=localhost`; `pg_hba`: `host all all 127.0.0.1/32 scram-sha-256`.

### Base temporal (aislada de `prislab_db`)

```sql
CREATE ROLE prislab_ci_review_20260913 LOGIN PASSWORD '<temp>' CREATEDB;
CREATE DATABASE prislab_ci_review_20260913 OWNER prislab_ci_review_20260913;
```

Túnel local → VPS:

```bash
ssh -N -L 55432:localhost:5432 root@216.238.89.243
```

Verificación de conectividad: `connected PostgreSQL 18.6`.

---

## 3. Diferencia: `migrate` directo, `--keepdb`, `PRISLAB_TEST_NO_MIGRATIONS=1`

| Modo | Qué hace | Evidencia (tiempo) |
|------|----------|--------------------|
| `manage.py migrate --noinput` | Aplica **todo** el historial de migraciones a una base real (no de pruebas). | **825 s (13m45s)**, todas `OK` (core 0001→0108, contabilidad 0014, etc.). |
| `manage.py test` (por defecto) | Crea una base de pruebas **separada** (`test_<name>`), re-aplica todo el historial de migraciones, ejecuta y **destruye**. | Batería de 8 casos: **767 s (12m47s)**, 8/8 OK. |
| `PRISLAB_TEST_NO_MIGRATIONS=1` | Desactiva migraciones (`MIGRATION_MODULES` → `_DisableMigrations` en `config/settings/database.py` líneas 47-57). El esquema se crea **directo desde los modelos** (`syncdb`), sin `RunPython`. | Batería de 8 casos: **111 s (1m51s)**, 8/8 OK. |
| `--keepdb` (con DB ya existente) | **Reutiliza** la base de pruebas en vez de crearla/destruirla. | **32 s**, 8/8 OK, `Using existing test database`. |

Punto clave de código (`config/settings/database.py`):

```python
if 'test' in sys.argv and os.environ.get('PRISLAB_TEST_NO_MIGRATIONS') == '1':
    class _DisableMigrations(dict):
        def __contains__(self, item):
            return True
        def __getitem__(self, item):
            return None
    MIGRATION_MODULES = _DisableMigrations()
```

Nota: `PRISLAB_TEST_NO_MIGRATIONS=1` es además el modo por defecto del script
propio del proyecto (`scripts/run_targeted_tests.ps1`), por lo que no es un
atajo ajeno al repositorio.

---

## 4. Transacciones `idle in transaction` y operaciones DDL lentas

Durante `migrate` y durante la creación de la base de pruebas se muestreó
`pg_stat_activity`. Estados observados repetidamente:

```text
state=idle in transaction  wait_event_type=Client  wait_event=ClientRead
```

con la última sentencia siendo DDL:

```text
CREATE INDEX "inventario__reactiv_e290da_idx" ON "inventario_lotereactivolab" ...
ALTER TABLE "core_hashraizdiario" ADD COLUMN "empresa_id" bigint NULL
DROP INDEX IF EXISTS "core_docume_empresa_16fe7f_idx"
```

**Interpretación corregida:** `idle in transaction` + `ClientRead` significa que
el servidor **terminó** la sentencia DDL y está **esperando a que el cliente
(Django) envíe la siguiente** a través del túnel. No es un deadlock ni una
migración colgada en ejecución. El cuello de botella es el **round-trip por
sentencia del túnel SSH** (cientos de DDL secuenciales), no el motor PostgreSQL:

- `load average` durante las corridas: `0.11` (CPU ocioso).
- Memoria VPS: `1637 MB total`, ~`74-81 MB free`, ~`279-293 MB available`
  (memoria ajustada, factor de riesgo, pero sin swap activo relevante).

---

## 5. Resultado de la batería dirigida

Batería `core.tests.test_prisci_unified_ai` (8 casos) contra PostgreSQL 18.6:

```text
Ran 8 tests in 15.672s   (modo migraciones)  -> OK  (exit 0)
Ran 8 tests in 17.399s   (NO_MIGRATIONS=1)   -> OK  (exit 0)
Ran 8 tests in 16.909s   (--keepdb reutiliza) -> OK  (exit 0)
```

Único traceback observado (esperado, no es fallo): el caso
`test_prisci_webhook_uses_same_assistant` dispara un `RuntimeError` de Gemini
("API key not valid") al ejercitar el fallback seguro; el test **pasa**.

---

## 6. Suite total

`PRISLAB_TEST_NO_MIGRATIONS=1 manage.py test --keepdb --verbosity 1`
(lanzada 19:07:56).

- Esquema creado: 273 tablas; la suite **avanza de forma continua** (no cuelga).
- Progreso medido en `pg_stat_database`:
  `xact_commit` 218 → 262 → 332 en ~12 min (~9-10 tx/min); sentencias activas
  eran `INSERT`/`SELECT` de fixtures de prueba.
- `core/tests` contiene **607** métodos `def test_` (sin contar el resto de apps).

**Resultado:** la suite total es **impracticable por latencia del túnel**
(horas de ejecución), no por bloqueo. Se detuvo de forma controlada a los ~12
minutos con la evidencia de progreso y throughput anteriores. No se declara
verde ni roja; se declara **no ejecutable en ventana operativa vía túnel SSH**.

---

## 7. Sin usar producción ni modificar credenciales

- Bases antes: `postgres, prislab_db, template0, template1`. Igual después.
- El rol temporal **nunca** se conectó a `prislab_db` (0 conexiones verificadas
  por `pg_stat_activity`).
- Sólo se crearon credenciales **temporales** nuevas (rol + DB `..._ci_review_...`),
  que se eliminaron al final. No se modificó ningún secreto existente.
- Limpieza verificada:

```text
DROP DATABASE test_prislab_ci_review_20260913 WITH (FORCE);  -- OK
DROP DATABASE prislab_ci_review_20260913 WITH (FORCE);       -- OK
DROP ROLE prislab_ci_review_20260913;                        -- OK
```

- Post-limpieza: `pg_isready` accepting; `postgresql` y `prislab-gunicorn`
  `active`.

---

## 8. Discrepancias con el documento base

1. **"No concluyente por bloqueo" queda refutado** para la batería dirigida:
   esperando ~13 min, la creación del esquema termina y las pruebas pasan 8/8.
2. **`idle in transaction` no es DDL lenta en servidor** ni deadlock: es el
   servidor en `ClientRead` esperando al cliente a través del túnel.
3. **Usuario SSH** es `root`, no `prislab`.
4. **`runtime.txt` fija `python-3.11.11`**, mientras la validación apunta a
   `3.12.14`: incoherencia entre el pin de runtime y el objetivo de validación.
5. Confirma "ruta inexistente" de Python 3.12 local y el venv `.venv_py312` roto
   (fue necesario reinstalar 3.12.14).
6. **`PRISLAB_TEST_NO_MIGRATIONS=1` reduce el esquema de ~13 min a ~2 min** y
   es el modo por defecto del runner propio del proyecto; conviene documentarlo
   como vía operativa para la suite PostgreSQL sin historia de migraciones.

## 9. Recomendación de cierre

Para cerrar la suite PostgreSQL completa de forma práctica: ejecutar el runner
**en el mismo host que PostgreSQL** (o con un túnel multiplexado de baja
latencia), con `PRISLAB_TEST_NO_MIGRATIONS=1 --keepdb` y memoria/CPU dedicados,
en un entorno que **no** comparta recursos con la Gunicorn productiva. Las
pruebas de migraciones deben ejecutarse aparte (sin `NO_MIGRATIONS`).
