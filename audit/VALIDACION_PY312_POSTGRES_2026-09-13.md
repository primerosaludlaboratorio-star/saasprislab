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
