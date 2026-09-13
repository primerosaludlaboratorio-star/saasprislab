# Validacion Python 3.12 / PostgreSQL

**Fecha:** 2026-09-13
**Alcance:** comprobar disponibilidad del runtime y del motor requerido para
ejecutar la suite fuera de SQLite. No se ejecutaron migraciones, escrituras ni
pruebas contra la base productiva.

## Resultado

**No concluyente por bloqueo de entorno.** No se puede declarar la validacion
Python 3.12/PostgreSQL como aprobada.

## Evidencia

### Equipo local

- `py -0p` solo muestra Python 3.14.
- La entrada registrada para Python 3.12 apunta a una ruta inexistente.
- `docker`, `psql` y el servicio PostgreSQL local no estan disponibles.

### VPS

- Conexion SSH por clave verificada.
- Python disponible: `3.14.4`.
- Python 3.12 no esta instalado.
- PostgreSQL cliente: `18.6`.
- PostgreSQL local: activo y `pg_isready` responde `accepting connections`.
- Gunicorn activo.
- No se identifico un contenedor ni una base de pruebas separada para ejecutar
  Django sin riesgo de tocar datos productivos.

## Pruebas ejecutadas sin mutacion

- `python manage.py check`: correcto en el entorno local con Python 3.14.
- `python manage.py makemigrations --check --dry-run`: sin cambios.
- La bateria dirigida local quedo bloqueada en `Creating test database`.
- `check --deploy` con variables ficticias fallo cerrado al exigir
  `PRISLAB_ESCUDO_USUARIO_ID` y reportar tokens de servicio ausentes.

## Pendiente para cerrar

1. Instalar Python 3.12 en un runner aislado o usar la imagen CI oficial.
2. Provisionar una base PostgreSQL de pruebas separada, con credenciales
   temporales fuera del repositorio.
3. Ejecutar la suite con JUnit y guardar los resultados.
4. No usar la base productiva como base de pruebas.

Las pruebas E2E humanas quedan fuera de este documento y permanecen reservadas
para la fase final.

## Despliegue posterior

El 2026-09-13 se publico el commit `a7b0804dd852ed5c3eadfc97d8fec681de8caf5c`
mediante `scripts/deploy_local_to_vps.ps1` usando un worktree limpio. La
operacion fue exitosa:

- Migracion `contabilidad.0014_alter_clientefacturacion_empresa_and_more`: OK.
- `collectstatic`: 52 archivos copiados, 152 sin cambios y 869 procesados.
- `prislab-gunicorn`, `prislab-celery` y `prislab-celerybeat`: activos.
- `nginx -t`: correcto; solo queda un warning de deprecacion de la sintaxis
  `listen ... http2`.
- `/health/`: HTTP 200.
- `/media/does-not-exist.txt`: HTTP 404.
- `showmigrations contabilidad`: `0014` marcada con `[X]`.

Esto confirma despliegue y migracion, pero no sustituye la validacion Python
3.12/PostgreSQL ni las pruebas E2E humanas.

## Revalidacion aislada 2026-09-13

- Se instalo Python `3.12.14` en un entorno virtual ignorado por Git y se
  sincronizaron las dependencias desde `requirements.lock`.
- Se creo el rol y la base PostgreSQL temporales `prislab_ci_20260913`; el rol
  recibio `CREATEDB` exclusivamente para que Django pudiera crear su base de
  pruebas.
- `manage.py migrate --noinput` completo sobre la base temporal: correcto.
- La primera bateria no pudo iniciar porque el rol carecia de `CREATEDB`.
  Tras corregir ese permiso temporal, el esquema de prueba parcial se elimino.
- En una segunda ejecucion limpia, la base de pruebas comenzo a crearse pero
  quedo bloqueada durante las migraciones, en una transaccion `idle in
  transaction` al crear el indice `core_hashraizdiario_timestamp_envio`.
  Se detuvo de forma controlada despues de mas de cinco minutos sin avance.
- La base temporal `test_prislab_ci_20260913` fue eliminada con `DROP DATABASE
  ... WITH (FORCE)`. No se uso ni modifico la base productiva.
- Al finalizar, tambien se eliminaron la base y el rol temporales
  `prislab_ci_20260913` del VPS.

**Resultado:** Python 3.12 esta instalado y las migraciones sobre PostgreSQL
aislado pasan, pero la bateria Django sobre PostgreSQL permanece
**inconclusa por bloqueo reproducible del runner/migraciones**. No se declara
verde ni se atribuye el bloqueo a un defecto funcional sin aislar primero la
migracion o señal que deja la transaccion abierta.

### Reproduccion adicional

- Se repitio con una base PostgreSQL nueva y `PRISLAB_TEST_NO_MIGRATIONS=1`,
  para excluir la historia de migraciones.
- Django volvio a quedar detenido en `Creating test database` antes de
  ejecutar las pruebas. Se interrumpio despues de mas de cinco minutos.
- La base de pruebas, la base aislada y el rol temporal fueron eliminados
  nuevamente.

Esto acota el siguiente diagnostico a la creacion/sincronizacion del esquema
de pruebas PostgreSQL o a la inicializacion de la aplicacion; no hay evidencia
para declarar aprobada la suite PostgreSQL completa.
