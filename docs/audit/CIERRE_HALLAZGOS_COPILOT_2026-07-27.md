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
`6ef947e1c25b6fe797cb6b7a52a0e46100442041` mediante
`scripts/deploy_local_to_vps.ps1 -User root`.

Evidencia remota:

- `/opt/prislab/app/DEPLOYED_REVISION` coincide con la revisión local.
- Migraciones `ia.0004` y `laboratorio.0017` aplicadas.
- `prislab-gunicorn`, `prislab-celery` y `prislab-celerybeat`: `active`.
- `/live/`, `/ready/`, `/health/` y `/login/`: HTTP 200.
- `/farmacia/` y `/laboratorio/`: HTTP 302 a `/login/` sin sesión, comportamiento esperado.
- Flujo humano PDV: Paracetamol buscado, producto seleccionable, lote FEFO elegido y carrito confirmado con `$15.00`; consola limpia después de la corrección del capturador de teclado.

El smoke autenticado y la prueba humana completa de los módulos siguen siendo
una fase funcional posterior; este despliegue no se presenta como sustituto de
esa auditoría.

## Correccion CCI/Westgard posterior

Se corrigio `laboratorio/services/cci_canal.py`: las excepciones de validacion,
integridad y operacion de base de datos ya estan importadas y el codigo dejo de
invocar `send_alert`, funcion inexistente que podia provocar un `NameError`
durante un rechazo Westgard si fallaba la notificacion. El canal queda en
`ALERTA_QC` aunque la notificacion no pueda persistirse, evitando liberar el
analito por un fallo secundario de alertamiento.

Se agrego `laboratorio/tests/test_cci_canal.py` y se incorporo al quality gate
general y PostgreSQL. Validacion local: 18 pruebas OK, 3 omitidas por backend
PostgreSQL; `manage.py check`, `makemigrations --check`, compilacion y
`git diff --check` sin errores.

Este cambio corrige robustez del camino de rechazo, pero no cierra la
verificacion operativa de CCI: produccion continua con cero mediciones de
control registradas al corte. Para cerrar Westgard se requieren lote, media,
desviacion estandar, equipo y mediciones reales del laboratorio, sin fabricar
datos clinicos.

## Clasificacion de pendientes y bateria adicional

Los datos de CCI/Westgard quedaron clasificados como captura operativa, no como
pendiente de codigo. La lista completa esta en
`docs/audit/CCI_DATOS_REQUERIDOS_PARA_CIERRE_2026-07-27.md`.

La bateria dirigida de Laboratorio, LIMS, Inventario, coherencia clinica,
seguridad y CCI ejecuto 49 pruebas: 49 OK, 0 fallos. Los mensajes de log
observados corresponden a escenarios intencionales: rechazo de una notificacion
secundaria, bloqueo de PDF con saldo pendiente, ausencia de consentimiento en
un caso de prueba y umbral de consultas para seguimiento de rendimiento. No se
clasifican como regresiones.

Pendientes funcionales verificables que permanecen abiertos:

- Flujo humano completo de Laboratorio/LIMS en produccion con datos operativos.
- Integracion HL7/analizador y dispositivos fisicos disponibles.
- Cierre de CCI/Westgard despues de cargar controles y mediciones reales.
- Ejecucion documentada de CAPA y EQA/PEEC con casos reales o controlados.
- Prueba de carga de canales en tiempo real cuando exista infraestructura para
  ejecutarla.

## Correccion Farmacia — material de curacion en venta con receta

Se corrigio la regla de dominio para que los productos con categoria
`CURACION` —jeringas, gasas, vendas, equipo de venoclisis y similares— no sean
enviados al flujo de antibióticos aunque arrastren banderas historicas de una
importacion. La misma regla se aplica en el endpoint de lotes, la busqueda PDV,
la validacion regulatoria y el registro COFEPRIS.

Evidencia:

- 6 pruebas del contrato regulatorio y busqueda PDV OK.
- Suite Farmacia/lotes/entrada previa: 60 pruebas OK.
- `manage.py check`, `makemigrations --check` y compilacion sin errores.

El folio interno PRISLAB permanece automatico e inmutable para conservar la
cadena de auditoria. El numero externo de la receta es editable. En surtido
parcial se conserva el folio y se registran cantidad prescrita, cantidad
surtida, saldo pendiente y motivo.

## Correccion Farmacia - devoluciones totales y parciales con autorizacion

Se corrigio el flujo de devoluciones de farmacia para que la interfaz y el
backend utilicen el mismo contrato. La pantalla permite seleccionar las
partidas y cantidades de una devolucion parcial, elegir reingreso a inventario
o merma/desecho, capturar el motivo y solicitar el PIN universal de cuatro
digitos antes de procesar.

El backend ahora:

- valida el PIN configurado por empresa antes de cualquier mutacion;
- acepta los roles operativos de farmacia autorizados, sin abrir el permiso a
  cajeros;
- mantiene compatibilidad temporal con los nombres de payload anteriores;
- delega el parcial al servicio trazable de devoluciones, incluyendo lotes y
  cantidades reales;
- bloquea parciales sin partidas, montos superiores al saldo disponible y
  devoluciones duplicadas.

El numero externo de receta queda opcional cuando el surtido es parcial. El
folio interno PRISLAB permanece automatico, unico e inmutable para auditoria;
no sustituye ni inventa el folio fisico del medico. Se conservan medico,
cedula, fecha, cantidad prescrita, cantidad surtida, saldo y motivo.

Validacion local posterior a la correccion:

- suite `core.tests.test_devoluciones_farmacia_api farmacia.tests`: **56 OK**;
- rechazo de parcial sin detalle: **400** con codigo
  `DEVOLUCION_PARCIAL_REQUIERE_DETALLE`;
- `git diff --check`: sin errores.

Correccion de rutas: el enlace visible `/farmacia/devoluciones/` estaba
resolviendo un template legacy desde `config/urls/farmacia.py`, aunque la
implementacion corregida vivia en la ruta ERP. Se unifico la ruta canonica con
`farmacia.views.devoluciones.buscar_venta_para_devolucion` y su procesador
correspondiente, conservando los aliases ERP para compatibilidad.

Despliegue y verificacion productiva:

- revision desplegada: `71809f595593e8f2fe31c3d9979582074a94bd95`;
- migraciones: sin pendientes; servicios de aplicacion activos;
- `/health/`, `/live/` y `/ready/`: HTTP 200;
- flujo humano en `/farmacia/devoluciones/`: venta cargada, dos partidas
  renderizadas, selección de una partida y cantidad parcial habilitada;
- el modal de procesamiento solicita PIN universal de exactamente cuatro
  digitos;
- se cancelo el dialogo antes de enviar, sin mutar caja, inventario ni ventas;
- consola del navegador: cero errores.

## Verificacion inicial Laboratorio/LIMS en produccion

Se reviso la interfaz productiva con la cuenta de auditoria sin crear una
orden ni modificar resultados clinicos:

- Recepcion de orden carga correctamente y permite buscar estudios por nombre,
  codigo o abreviatura.
- La seleccion de `GLU - GLUCOSA` se reflejo en la tabla y recalculo el resumen
  a `$85.00` sin error de interfaz.
- Toma de muestra, Monitor de Produccion, Registro de Resultados, Control de
  Calidad, Entrega de Resultados, Worklist y catalogo LIMS cargaron sin 502,
  traceback ni pantalla de error.
- La consola del navegador no reporto errores durante la prueba dirigida.
- Produccion al corte: `0` mediciones CCI del tenant 1 y `0` alertas Westgard
  pendientes. Esto impide declarar cerrado Westgard con evidencia clinica;
  requiere cargar controles, lotes, equipo y mediciones reales.

Validacion automatizada local del dominio: `laboratorio.tests lims.tests` =
**36 OK, 3 omitidas por backend PostgreSQL**. Las omisiones corresponden a
pruebas que requieren el backend PostgreSQL real y no se clasifican como fallo
de codigo local.

## Reportes de ventas de laboratorio con captura progresiva

Se implemento el reporte de ventas de laboratorio sin hacer obligatorios los
datos de enriquecimiento del inventario. La fuente minima de una venta es la
linea de la orden, su descripcion o analito y `precio_momento`; por lo tanto
una orden ya puede aparecer en caja y reportes aunque aun no tenga reactivo,
presentacion o costo de materiales capturados.

El reporte ahora muestra, por cada estudio/producto agrupado:

- cantidad e ingreso historico de la venta;
- reactivos vinculados a formulas de consumo, o `Pendiente de capturar`;
- costo material solo cuando existe un snapshot de `CosteoEjecucionAnaliticaLab`;
- estado de presentacion como pendiente hasta que el catalogo la complete.

No se usa cero para simular un costo conocido. La ausencia de costo se marca
como pendiente para evitar que utilidad o margen se interpreten como datos
reales antes de completar el inventario. Al capturar formulas y costeos, el
reporte los incorpora automaticamente en siguientes consultas, sin editar la
venta historica ni bloquear la operacion.

Validacion local:

- prueba de linea minima sin inventario: **OK**;
- prueba integrada de `/finanzas/lab/caja/` con estudio y precio unicamente:
  **OK**;
- suite Laboratorio/LIMS y reporte: **40 OK, 3 omitidas por PostgreSQL**;
- `manage.py check`, `makemigrations --check` y `git diff --check`: **OK**.
