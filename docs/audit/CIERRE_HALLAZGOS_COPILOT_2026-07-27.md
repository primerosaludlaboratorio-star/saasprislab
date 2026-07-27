# Cierre de hallazgos Copilot - 2026-07-27

## Alcance

Implementacion local sobre release/v1.0-local. No se declara despliegue ni
cierre productivo hasta ejecutar migraciones, CI y smoke test autenticado.

## Correcciones

- Se elimino la contrasena por defecto del comando de usuarios de produccion.
- Rate limit: X-Forwarded-For solo se acepta desde proxies confiables
  configurados; el acceso directo usa REMOTE_ADDR.
- El bypass de tenant de emergencia provoca fallo de arranque en produccion.
- CotizacionOCR tiene FK obligatoria a empresa, backfill de migracion y admin
  filtrado por tenant.
- Sentinel limita telemetria a 120 eventos por minuto por IP y rechaza
  payloads no objeto o mayores de 16 KiB.
- Westgard queda activo por defecto; no puede apagarse desde el panel en
  produccion sin una excepcion operativa explicita.
- CI incorpora gate PostgreSQL 16 y publica coverage.xml como artefacto.
- Laboratorio incorpora CAPA/no conformidades y EQA/PEEC con estados
  controlados, causa raiz, accion correctiva, evidencia de cierre, z-score y
  bitacora CAPA append-only.

## Evidencia

Pasaron:

- manage.py check
- manage.py makemigrations --check --noinput
- compilacion Python de core, laboratorio, ia y contabilidad
- pruebas unitarias de rate limit, governance Westgard y Sentinel

La suite Django que crea la base completa queda pendiente de un entorno de
pruebas funcional: el arnes SQLite local se bloquea durante la creacion de la
base y no entrega un resultado final. No se contabiliza como verde.

## Pendientes antes de produccion

1. Ejecutar migraciones en staging controlado y comprobar backfill OCR.
2. Ejecutar el job PostgreSQL y revisar el artefacto de cobertura.
3. Hacer smoke test autenticado de CAPA, EQA, Sentinel y autofactura.
4. Desplegar solo despues de esos resultados y registrar el commit.

## Segunda tanda de hardening

- Se retiro completamente el bypass OMNI del middleware de rate limit; los
  escenarios de auditoria ya no pueden saltarse limites mediante header.
- Se agrego rate limit a reset y diagnostico Sentinel.
- Se retiro la IP publica del server_name de Nginx.
- Strict tenant queda activo por defecto en staging y produccion, pero no
  altera la ejecucion de suites de test.
- Las APIs autenticadas de voz y OCR de PRIS ya no usan csrf_exempt; ahora
  exigen POST con CSRF, validan JSON y limitan el tamano de entrada.

Evidencia adicional: 8 pruebas unitarias de seguridad pasan, incluyendo la
proteccion CSRF de voz/OCR.

El transporte REST de Gemini tambien quedo centralizado en
core/utils/gemini_transport.py. Los adaptadores legacy de PRIS delegan en ese
unico transporte y conservan sus imports compatibles. La prueba de
centralizacion pasa sin llamadas externas.

El endpoint autenticado de verificacion WebAuthn tambien dejo de usar
csrf_exempt. Los restantes endpoints sin CSRF se mantienen solo cuando usan
un token de servicio independiente (kiosco, IoT, cron, webhook o Sentinel) y
cuentan con rate limit o validacion equivalente.

Durante el quality gate se corrigio una regresion de CAPA: las transiciones
fallidas ahora restauran el estado en memoria y no contaminan la siguiente
operacion. Tambien se restauraron los aliases URL historicos ocr_receta y
transcripcion_voz para compatibilidad.

Quality gate local con PRISLAB_TEST_NO_MIGRATIONS: 118 pruebas OK, 4
omitidas; el bloque adicional de autofactura, IA, CAPA y usuarios: 13
pruebas OK. La ejecución histórica con migraciones completas sigue
requiriendo PostgreSQL/CI.

## Correccion adicional verificada

El diagnóstico Sentinel dejó de depender de `psycopg2` y de la consulta
exclusiva `pg_tables`. Ahora utiliza la introspección y el escape de
identificadores de Django, por lo que funciona con PostgreSQL en producción y
SQLite en las verificaciones locales. Se añadió una prueba de regresión que
ejecuta el diagnóstico con el backend activo.

La batería dirigida final ejecutada en local terminó con 24 pruebas OK,
incluyendo seguridad, rate limit, transporte Gemini, autofactura, IA, CAPA,
EQA, usuarios de producción y diagnóstico Sentinel.

El workflow de CI ahora ejecuta ese conjunto adicional tanto en el gate
general como en el gate PostgreSQL 16. La migración OCR conserva backfill
obligatorio y falla si existen registros huérfanos; la migración CAPA/EQA se
validó con `sqlmigrate` en ambos sentidos.

Pendiente operativo residual: ejecutar el workflow en GitHub y efectuar el
despliegue/smoke autenticado en el servidor real. El repositorio no contiene
los secretos SSH ni permite verificar el estado de servicios remotos desde
esta sesión.

## Despliegue local confirmado

El 2026-07-27 se desplegó desde este checkout local, sin GitHub, la revisión
`8a0e3e80a73a1e478ce015e6d4c050b6cb84af73` mediante
`scripts/deploy_local_to_vps.ps1 -User root`.

Evidencia remota:

- `/opt/prislab/app/DEPLOYED_REVISION` coincide con la revisión local.
- Migraciones `ia.0004` y `laboratorio.0017` aplicadas.
- `prislab-gunicorn`, `prislab-celery` y `prislab-celerybeat`: `active`.
- `/live/`, `/ready/`, `/health/` y `/login/`: HTTP 200.
- `/farmacia/` y `/laboratorio/`: HTTP 302 a `/login/` sin sesión, comportamiento esperado.

El smoke autenticado y la prueba humana completa de los módulos siguen siendo
una fase funcional posterior; este despliegue no se presenta como sustituto de
esa auditoría.
