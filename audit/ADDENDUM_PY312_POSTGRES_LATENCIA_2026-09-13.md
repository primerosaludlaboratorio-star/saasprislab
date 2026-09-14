# Addendum: Python 3.12/PostgreSQL

Fecha: 2026-09-13

## Verificacion posterior al despliegue

- Revision activa en VPS: `9ee46ac5fd3bfebba02264a263de806a060708ee`.
- Gunicorn, Celery y Celery Beat: activos.
- PostgreSQL: listo.
- La base productiva no fue utilizada.

Se ejecuto en el mismo VPS, con Python `3.12.14`, PostgreSQL local y una base
temporal aislada:

```text
PRISLAB_TEST_NO_MIGRATIONS=1
inventario.tests.test_consumo_analitico --keepdb
Ran 4 tests in 2.299s
OK
```

El resultado confirma contra PostgreSQL el fix de `inventario/signals.py` con
`select_for_update(of=('self',))`, que evita el error de PostgreSQL sobre el
lado nullable del `OUTER JOIN`. El rol y la base temporales se eliminaron.

## Solucion de la latencia

La latencia observada era del round-trip del tunel SSH, no un deadlock de
PostgreSQL. El procedimiento correcto es:

1. Ejecutar la suite en el mismo host de PostgreSQL.
2. Usar una base y un rol temporales, separados de `prislab_db`.
3. Usar `PRISLAB_TEST_NO_MIGRATIONS=1 --keepdb` para regresiones repetitivas.
4. Ejecutar una corrida separada con migraciones reales.
5. Eliminar base y rol temporales automaticamente al finalizar.

El tunel queda reservado para comandos puntuales, no para la suite completa.

## Remediacion posterior verificada

Revision desplegada: `341b4569f29e336d3a4e772d0b52a04fab6cf614`.

- Sentinel ya no cierra conexiones sanas compartidas por el request.
- Las tareas de Marketing ejecutadas en modo Celery eager no cierran la
  conexion del llamador; los workers reales mantienen su limpieza normal.
- El inventario de Farmacia incluye productos compartidos del tenant
  (`sucursal=NULL`) y conserva el aislamiento por tenant y sucursal.
- La prueba de backup declara SQLite explicitamente, evitando depender del
  motor PostgreSQL activo en el entorno de pruebas.

Verificacion local y remota con Python `3.12.14` y PostgreSQL 18.6:

```text
15 tests, OK
manage.py check: 0 issues
No migrations pending
Health check de produccion: 200 OK
```

La base y el rol temporales se eliminaron al finalizar. La base productiva,
credenciales y datos operativos no fueron modificados.
