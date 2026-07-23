# AI Coordination Status

Fecha: 2026-07-21

## Corte Farmacia: correcciones y verificacion productiva — 2026-07-23

Este corte se limita al modulo Farmacia y deja trazabilidad de lo que fue corregido y de lo que sigue pendiente para la certificacion humana integral.

### Correcciones desplegadas

- `9b59814`: el historial de ventas precarga detalles, pagos y CFDI; las consultas observadas bajaron de `63` a `20` y Sentinel dejo de reportar el umbral de consultas.
- `d68cdbe`: la validacion de antibioticos devuelve `400` si falta `producto_id`, `404` si el producto no pertenece a la empresa y `400` si faltan datos del prescriptor; ya no convierte esos casos en `500`.
- `f9d2b0b`: las rutas legacy `/farmacia/kardex/`, `/farmacia/reporte/valorizacion/`, `/farmacia/semaforo-caducidad/`, `/farmacia/stock-critico/` y `/farmacia/antibioticos/reporte-cofepris/` redirigen al namespace ERP vigente.

### Evidencia productiva

- El commit `f9d2b0b` esta desplegado en `/opt/prislab/app` sobre `release/v1.0-local`.
- `manage.py check`, estaticos y los servicios `prislab-gunicorn`, `prislab-celery` y `prislab-celerybeat` quedaron correctos.
- Las pantallas de Farmacia, APIs de busqueda, caja, Kardex, lotes, libro de control, devoluciones, reportes y regulatorio respondieron conforme a contrato bajo `auditoria_admin_10d`.
- La busqueda positiva de `AMOXICILINA` devolvio resultados en PDV y entrada; la busqueda inexistente devolvio lista vacia sin error.
- La validacion regulatoria productiva devolvio `400`, `404`, `400` y `200` en los cuatro escenarios de contrato probados.
- La cola Sentinel pendiente para URLs de Farmacia quedo en `0`. Las nueve incidencias historicas relacionadas fueron resueltas con nota de trazabilidad, no eliminadas.

### Estado de cierre

El backend y las pantallas de consulta de Farmacia quedan verificados en verde. La certificacion `100%` del modulo sigue **ABIERTA** hasta ejecutar con una sesion humana autenticada los flujos con efecto lateral: apertura de caja, ventas con varios productos y lotes, venta parcial, cancelacion, devolucion parcial/total, registro de gasto, precorte y corte. No se ejecutaron esos writes contra datos reales en este corte para no contaminar produccion ni usar credenciales no entregadas.

## Revision Sentinel Farmacia posterior — 2026-07-23

- Sentinel de produccion: `0` incidencias `PENDIENTE` cuya URL pertenece a Farmacia.
- La revision de logs detecto un `500` repetido en Entrada de mercancia por `UniqueViolation` de `core_producto_codigo_barras_key` cuando el formulario llegaba sin `producto_id` y el codigo ya existia.
- `8a624dc` corrige el caso: el servicio resuelve el codigo existente dentro de la empresa y, ante conflicto global, responde `409` controlado en lugar de `500`; se agrego regresion automatica.
- Produccion quedo desplegada en `8a624dc`; `manage.py check`, estaticos, servicios y rutas principales de Farmacia respondieron correctamente.
- La prueba productiva de codigo existente se ejecuto con rollback: devolvio `200`, resolvio el producto correcto y stock/precios quedaron identicos antes y despues.
- No se detectaron nuevos `500` de Farmacia despues del despliegue. Los `DisallowedHost` de dominios no canonicos y `401` de telemetria no autenticada quedan fuera del modulo.

## Entrada continua por multiples lotes — 2026-07-23

- `8e5581c` elimina la recarga automatica de Entrada de mercancia al guardar un producto existente.
- La interfaz conserva medicamento, marca, equivalencias, costo y precio; limpia solamente la operacion del lote y vuelve a cargar los lotes disponibles.
- El boton ahora indica `GUARDAR LOTE Y CONTINUAR` y permite registrar consecutivamente lotes distintos sin abandonar la ventana.
- El API devuelve `lote_id` y `lote` en cada ingreso exitoso.
- Produccion verificada con dos lotes reales dentro de rollback: ambos respondieron `200`, devolvieron sus identificadores correctos y no cambiaron stock ni precios.
- HTML productivo: `200`, funcion de continuidad presente y `location.reload()` ausente.

## Usuarios temporales de auditoria productiva — 2026-07-23

Se habilitaron tres cuentas temporales para pruebas humanas sobre Empresa `1` / sucursal `Matriz Principal`. No se guardan contrasenas en el repositorio.

| Usuario | Rol | Alcance verificado | Expira |
|---|---|---|---|
| `auditoria_admin_10d` | `ADMIN` + superusuario | Acceso total del sistema | 2026-08-02 17:25 UTC |
| `farmacia_admin_10d` | `FARMACIA` | PDV e inventario de Farmacia; Laboratorio bloqueado | 2026-08-02 17:25 UTC |
| `farmacia_empleado_10d` | `CAJERO` | PDV e inventario operativo; Laboratorio y admin bloqueados | 2026-08-02 17:25 UTC |

La expiracion esta respaldada por el timer `prislab-expire-auditoria-users.timer`, que desactiva las tres cuentas automaticamente.

## Correcciones productivas Farmacia — 2026-07-23

- Se corrigio la seleccion de resultados del PDV: el buscador renderiza botones con `data-producto-id` y el manejador ahora acepta ese elemento, no solamente tarjetas `.card`. La busqueda vuelve a permitir seleccionar y agregar el medicamento al carrito.
- Se corrigio la entrada de mercancia: la pantalla usa la URL canonica mediante `reverse`, muestra de forma visible `Producto existente` y `Producto nuevo`, permite buscar/seleccionar un producto existente y registra el incremento por Kardex sin duplicar el catalogo.
- La entrada existente conserva el producto seleccionado y actualiza existencias mediante `MovimientoInventario`; la prueba productiva se ejecuto dentro de una transaccion de rollback y confirmo que el stock quedo sin cambios.
- Se corrigio la llamada de trazabilidad de entradas para usar el contrato real de `registrar_trazabilidad`; el movimiento queda asociado a empresa, sucursal, usuario, producto y request.
- Se detecto y restauro la ausencia de las tres cuentas temporales documentadas. El login de `auditoria_admin_10d` fue verificado nuevamente despues de la restauracion.
- `manage.py check`, compilacion Python, despliegue, reinicio de servicios y busquedas productivas pasaron. La suite local dirigida sigue sin contabilizarse porque quedo bloqueada creando su base de pruebas.

**Estado Farmacia:** estas dos incidencias quedan corregidas y verificadas en produccion. La certificacion global del modulo Farmacia continua sujeta a la matriz completa de escenarios, no solo a estas dos correcciones.

## Auditoria Sentinel productiva — 2026-07-23

- Se revisaron los registros del dia. La alerta funcional reproducible de Farmacia era `PermissionDenied` repetido en `/farmacia/erp/kardex/crear-movimiento/`, provocado por el permiso Django obligatorio para el rol `FARMACIA`; se sustituyo por RBAC de Farmacia para `FARMACIA`, `ADMIN`, `GERENTE` y `DIRECTOR`.
- Se corrigio `TemplateDoesNotExist` en `/farmacia/libro-control/`: la vista apuntaba a `core/libro_control_antibioticos.html`, archivo inexistente; ahora usa la plantilla canonica existente `core/libro_control.html` con contexto compatible.
- Los reintentos de Sentinel habian provocado saturacion temporal de conexiones PostgreSQL (`remaining connection slots are reserved...`). Se reiniciaron Gunicorn, Celery y Celery Beat despues de corregir las causas; el estado posterior quedo estable.
- Verificacion posterior en produccion: Kardex y Libro de Antibioticos respondieron `HTTP 200` con `farmacia_admin_10d`; no aparecieron nuevas alertas de `PermissionDenied`, `TemplateDoesNotExist`, `503` ni `remaining connection slots` despues del reinicio.
- Queda una advertencia no bloqueante de latencia aislada en `/notificaciones/badge/` de aproximadamente `2.41 s`; no se clasifica como fallo funcional en este corte.
- Los `DisallowedHost` contra la IP publica son rechazo esperado del dominio no canonico, y los `401` de `/api/log-frontend-error/` son telemetria no autenticada, no errores de negocio.

**Estado Sentinel:** incidente funcional corregido y verificado en produccion; la advertencia de latencia queda pendiente de optimizacion separada.

## Punto cero Sentinel para nueva auditoria — 2026-07-23

- Se ejecuto `sentinel_amnistia_pre_produccion --dry-run` y despues la ejecucion real en produccion.
- Se marcaron `58` incidencias Sentinel historicas como `SOLUCIONADO`, conservando los registros y su trazabilidad; no se eliminaron filas.
- Buzon de quejas, discrepancias de inventario y notificaciones internas no tenian pendientes.
- La verificacion posterior dejo `0` incidencias Sentinel abiertas y `0` incidencias nuevas del dia.
- Las rutas `/farmacia/pdv/`, `/farmacia/erp/kardex/`, `/farmacia/erp/kardex/crear-movimiento/` y `/farmacia/libro-control/` respondieron `HTTP 200` autenticadas con `auditoria_admin_10d`.
- `IncidenciaOperativa` de negocio no fue modificada.

**Estado operativo:** Sentinel queda en punto cero para la siguiente auditoria. Cualquier nueva incidencia posterior a este corte debe tratarse como evento nuevo, no como arrastre historico.

## Correccion productiva de seleccion Producto/Lote — 2026-07-23

- La busqueda manual del PDV ya no deshabilita productos cuando `Producto.stock` esta en cero pero existen lotes con existencia; la API de lotes es la fuente de verdad, igual que en el escaneo.
- La entrada de mercancia resuelve el codigo de barras contra la misma API de catalogo usada por Farmacia; el lector puede confirmar con `Enter` y no se crea un producto duplicado.
- La entrada permite seleccionar un lote existente, suma la cantidad en ese lote y conserva la trazabilidad del Kardex. Los lotes sin existencia tambien aparecen en modo entrada para poder reabastecerlos.
- La venta muestra selector cuando hay varios lotes, conserva FEFO como valor predeterminado cuando solo hay uno y envia `lote_id` al cobro. El carrito muestra el lote y el backend registra `DetalleVentaLote`/Kardex.
- Se actualizo el cache-bust del JavaScript del PDV a `7.11-product-lot-selection`.
- Produccion verificada: busqueda PDV y entrada encontraron el mismo producto/codigo (`HTTP 200`); prueba de entrada con `lote_id` y prueba multi-lote pasaron dentro de rollback, sin dejar datos de auditoria; la pantalla autenticada carga el JavaScript nuevo y Sentinel permanece con `0` incidencias abiertas.

**Estado:** correccion desplegada y verificada en produccion. La certificacion integral de todos los escenarios de Farmacia sigue siendo independiente de este cierre puntual.

## Corte de auditoria productiva Laboratorio/LIMS — 2026-07-23

La verificacion se ejecuto autenticada con `auditoria_admin_10d` sobre `https://prislab.labcorecloud.com`. No se modificaron ordenes clinicas, pacientes, catalogos LIMS ni catalogo de farmacia durante este corte.

### Evidencia aprobada

- La suite automatica integral `PRISLAB_OMNI_SUITE` termino `ok=true`, `findingsCount=0`; sus cuatro bloques (`pdv_e2e`, `ui_omni`, `api_smoke`, `role_matrix`) terminaron correctamente.
- La verificacion de interfaz autenticada cargo recepcion de Laboratorio y acepto la busqueda de `glucosa`; las pantallas operativas de recepcion, lista de trabajo, consulta de ordenes, control de calidad, toma de muestra, entrega, maquila y dashboard respondieron `HTTP 200`.
- Las APIs de busqueda de estudios, parametros LIMS y ordenes recientes respondieron correctamente. El endpoint de preordenes rechazo sin `paciente_id` con `HTTP 400` contractual, no con error interno.
- La matriz de permisos confirmo que `auditoria_admin_10d` conserva acceso administrativo a Laboratorio, mientras que los usuarios de Farmacia reciben `403` en lista de trabajo y no heredan acceso por `is_staff`.

### Bloqueos que impiden cerrar Laboratorio

- **CCI/Westgard estricto no es verificable en produccion:** no existen equipos, materiales de control, lotes ni mediciones CCI persistidas. No se fabricaron fixtures en produccion para no contaminar evidencia ni datos operativos.
- **UREA/BUN sigue pendiente:** la consulta autoritativa de analitos no encontro los codigos exactos `UREA` ni `BUN`; no se debe declarar completo el flujo de resultados hasta resolver la dependencia de catalogo/LIMS.
- **UI LIMS legacy:** `/lims/estudios/` y `/lims/parametros/` redirigen al administrador (`/admin/lims/analito/`), aunque sus APIs responden. Esto queda como discrepancia funcional de interfaz, no como fallo de autenticacion.
- La auditoria UI transversal genero 15 avisos fuera del alcance especifico de Laboratorio (rutas 404/503 y una advertencia de autofactura). Se conservan separados y no se presentan como fallos del flujo LIMS.

**Estado de cierre:** `ABIERTO`. El modulo no puede marcarse 100% hasta provisionar un entorno/datos QA controlados para CCI, resolver UREA/BUN, decidir la ruta LIMS visible y ejecutar la matriz humana completa con efectos laterales.

## Corte operativo 2026-07-21: deploy pendiente por configuracion real

La documentacion del procedimiento VPS existe y se mantiene como canon. El estado actual es: `e8a4d21` esta publicado en `release/v1.0-local` y fue desplegado manualmente en la VPS. Las migraciones no tuvieron cambios, los estaticos fueron actualizados, los tres servicios quedaron activos y el dominio publico respondio `HTTP 200`.

El workflow `PRISLAB Deploy to VPS` run `29855825290` sigue fallando en `Validate deploy secrets` por ausencia de `DEPLOY_HOST`, `DEPLOY_USER` y `DEPLOY_SSH_KEY`; por eso queda pendiente solo la automatizacion GitHub, no el deploy manual confirmado. La auditoria funcional productiva debe continuar sobre `e8a4d21`.

## Auditoria humana UI en desarrollo — 2026-07-21

- Se ejecutó una interacción visible contra `http://127.0.0.1:8000` con la base QA aislada; no fue producción.
- Login, recepción, búsqueda/selección de paciente, búsqueda de estudios, selección de `GLU` + `URE` y cálculo de cobro exacto (`$145.00`) pasaron.
- La confirmación de orden quedó validada al aceptar explícitamente el modal: se crearon `LAB-20260721-001` y `LAB-20260721-002`.
- La orden `LAB-20260721-002` completó toma 6/6, captura `GLU=95`, validación humana, PDF y entrega; la base QA confirma `ENTREGADO` y `aprobado_por_humano=True`.
- La orden `LAB-20260721-003` se creó como CxC con total `$85.00`, abono `$40.00`, saldo `$45.00` y motivo trazable; el estado de pago pendiente se reflejó en la interfaz.
- La orden `LAB-20260721-004` se creó como cortesía autorizada: el subtotal de referencia es `$85.00`, pero total, abono y saldo son `$0.00`; se corrigió la vista para no mostrar un saldo cobrable ficticio.
- La misma orden de cortesía completó toma manual 6/6 y fue enviada a Maquila desde la interfaz; la base QA confirmó `EN_MAQUILA`.
- La pantalla de Control de Calidad cargó después de corregir el JSON escapado de `parametros_lista_json`; se registraron tres fixtures visibles y persistidos (`GLUCOSA`, lote `QA-GLU-2026`, valores 100/101/99, desviaciones 0/+1/-1). Levey-Jennings básico queda probado; Westgard CCI estricto sigue pendiente porque usa otro canal de medición.
- La orden `LAB-20260721-005` probó `GLUCOSA=500`: el diálogo visible sustituyó el `prompt()` no soportado, exigió justificación QFB y validó con PDF; la base confirmó `RESULTADOS_LISTOS`, `fuera_rango=True` y `aprobado_por_humano=True`.
- El servidor bloqueó por API una validación sin justificación (`400 JUSTIFICACION_QC_REQUERIDA`) antes de generar PDF; con justificación válida registró `Validación QFB` en observaciones.
- La orden `LAB-20260721-006` probó rechazo desde Worklist y cancelación desde Recepción: el detalle volvió a `PENDIENTE_TOMA`, después quedó `CANCELADO` con motivo trazable y `GastoCaja=-85.00`.
- La orden `LAB-20260721-003` completó por interfaz el complemento de `$45.00`; la base confirmó `PAGADO`, anticipo `$85.00` y saldo `$0.00`.
- El cierre del servidor QA reprodujo un residual operativo fuera del flujo clínico: `/favicon.ico` termina en `503` por `ValueError: unsupported format` dentro de Sentinel y genera una incidencia duplicable.
- Se hizo determinista SweetAlert2 local en `core/templates/base.html` y se corrigió `core/services/validador_ia.py` para usar la relación `analito` real.
- El avance de Monitor sin PDF está protegido para responder `400` controlado; la ejecución automática focalizada se lanzó con UTF-8, pero debe contabilizarse solo cuando finalice con salida verificable.
- `UREA` está configurada como calculada (`BUN*2.14`) y no es capturable manualmente sin dependencia; queda como pendiente de catálogo/LIMS.
- Evidencia detallada: [20260721_human_ui_dev_laboratorio.md](./inbox/20260721_human_ui_dev_laboratorio.md).
- Estado: `ABIERTO`. Ya están probados en QA críticos fuera de rango con justificación, rechazo/repetición, cancelación/reembolso, complemento de pago y Levey-Jennings básico; siguen abiertos Westgard CCI estricto, UREA/BUN y la segunda auditoría humana completa.

## Revalidacion productiva de Laboratorio/LIMS — 2026-07-21

- La interfaz autenticada en producción fue recorrida como usuario administrativo: recepción, toma de muestra, worklist, captura, entrega, consulta de órdenes, pacientes, historial válido, monitor, maquila, LIMS y control de calidad cargaron.
- Se corrigió y desplegó `core/templates/core/control_calidad.html`: `parametros_lista_json` se renderizaba como `&quot;` y provocaba `SyntaxError: Unexpected token '&'`.
- La verificación no cierra el módulo: la matriz humana con efectos laterales todavía no fue ejecutada completamente; el catálogo LIMS autoritativo observado contiene 101 perfiles y 810 analitos.
- La migración productiva pendiente `lims.0011_perfilanalito_alter_perfillims_analitos_and_more` fue aplicada y la API de parámetros del estudio pasó a `200 application/json`; antes de la migración producía `OperationalError: no such table: lims_perfilanalito`.
- Los tokens públicos inválidos de resultados continúan devolviendo `400`, pero ahora se registran como advertencia controlada sin traceback; el cambio fue desplegado y revalidado.
- La configuración efectiva del proceso Gunicorn tiene HSTS, redirección SSL y cookies seguras activas; los hosts alternos rechazados por `ALLOWED_HOSTS` son una guardia esperada del dominio canónico.
- Las pantallas operativas probadas respondieron, pero recepción y captura registraron latencias de aproximadamente 2.6 a 3.3 segundos; queda evaluación de rendimiento.
- Maquila fue corregida y desplegada: solo acepta órdenes `requiere_maquila=True`, exige POST y registra laboratorio externo, guía, notas y fecha en `EnvioMaquila`; el flujo QA fue verificado con rechazo por datos incompletos y envío exitoso.
- Sentinel fue corregido y desplegado para excluir `404` JSON contractuales de sus incidencias; la guardia se revalidó con una cancelación de orden inexistente.
- Se eliminó el N+1 de la API de parámetros LIMS: la medición productiva pasó de 32 a 11 consultas, con respuesta `200` y 29 parámetros.
- La IA de resumen de bienestar quedó como integración opcional silenciosa cuando no hay clave configurada; el PDF productivo continúa generándose sin advertencia.
- Auditoría segura productiva: `20 OK`, `0 FAIL`; los únicos avisos son el modo sin credenciales del comando de solo lectura y 2 detalles históricos legacy sin analito/perfil/paquete LIMS. No se alteraron esos registros clínicos.
- La suite Django remota quedó ejecutándose sin resultado durante más de un minuto y fue detenida; no se contabiliza como aprobada.
- Estado: `ABIERTO`. No declarar Laboratorio 100% cerrado hasta corregir los puntos anteriores y ejecutar la matriz humana con efectos laterales usando datos QA.

## Estado actual

- La herramienta canónica de verificación humana de UI ya existe:
  - [tools/run_human_ui_audit.mjs](../../tools/run_human_ui_audit.mjs)
  - [run_human_ui_audit.bat](../../run_human_ui_audit.bat)
- La documentación de uso está en:
  - [PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md](./PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md)
- La regla de cierre técnico está en:
  - [ESTANDAR_TESTEABILIDAD_AUDITABILIDAD.md](./ESTANDAR_TESTEABILIDAD_AUDITABILIDAD.md)
- El flujo canónico de tareas está en:
  - [NEXT_ACTIONS.md](./NEXT_ACTIONS.md)
- El indice maestro completo está en:
  - [INDICE_CANONICO_TOTAL.md](./INDICE_CANONICO_TOTAL.md)
- Los pendientes canónicos están en:
  - [PENDIENTES_CANONICOS.md](./PENDIENTES_CANONICOS.md)
- El inventario físico del repo está en:
  - [INVENTARIO_CANONICO_REPO.md](./INVENTARIO_CANONICO_REPO.md) (historico / estructural)
  - [INVENTARIO_REAL_REPO.md](./INVENTARIO_REAL_REPO.md)
  - [INVENTARIO_UNIFICADO_RECONCILIADO_2026-06-24.md](./INVENTARIO_UNIFICADO_RECONCILIADO_2026-06-24.md)
  - [ESTADO_TESTS_LLM_Y_CAP5_2026-06-24.md](./ESTADO_TESTS_LLM_Y_CAP5_2026-06-24.md)

## Primer resultado validado

Se ejecutó la herramienta por primera vez contra producción con salida correcta:

- Target: `cloud`
- Base URL: `https://prislab.labcorecloud.com`
- Resultado: `ok: true`
- Hallazgos: `0`
- Artefactos:
  - `auditoria_ui_20260623_194820/report.json`
  - `auditoria_ui_20260623_194820/report.md`
  - `auditoria_ui_20260623_194820/screenshots/`

## Segundo resultado validado

Se ejecutó la herramienta con credenciales reales de prueba (`admin`) contra producción y quedó limpia:

- Target: `cloud`
- Base URL: `https://prislab.labcorecloud.com`
- Usuario: `admin`
- Resultado: `ok: true`
- Hallazgos: `0`
- Artefactos:
  - `auditoria_ui_20260623_212952/report.json`
  - `auditoria_ui_20260623_212952/report.md`
  - `auditoria_ui_20260623_212952/screenshots/`

## Cierres tecnicos integrados por Codex

### Consultorio - tenant efectivo en PDFs

- estado: `CERRADO`
- commit local Codex: `b9217b9`
- archivos:
  - `consultorio/pdf_views.py`
  - `consultorio/pdf_views_prislab.py`
  - `consultorio/tests.py`
  - `consultorio/test_pdf_tenant.py`
- resultado:
  - las rutas PDF vivas de Consultorio ya usan `empresa_efectiva_request(request)`
  - se corrigio la estructura rota de tests del modulo
  - una regresion nueva detecto y permitio corregir un bug real en `imprimir_expediente_forense`
- evidencia:
  - `py_compile OK`
  - `manage.py check OK`
  - `manage.py test consultorio --keepdb -v 1` -> `41 OK`

### Director + IA/PRIS - zona horaria local

- estado: `CERRADO`
- commit local Codex: `d26a09d`
- archivos:
  - `core/views/war_room.py`
  - `core/views/ia_dashboard.py`
  - `core/views/pris_ia.py`
  - `core/views/pris_jarvis.py`
  - `core/agent/pris_tools_operativos.py`
  - `core/ai_brain.py`
  - `core/views/ranking.py`
  - `core/views/incidencias.py`
  - `core/tests/test_director_dashboard_tz.py`
  - `core/tests/test_ia_pris_tz.py`
- resultado:
  - se reemplazo el patron UTC `timezone.now().date()` por `localdate()` en el alcance Director/IA/PRIS que seguia vivo en esta rama
  - se agregaron regresiones reales para dashboard Director y KPI IA/PRIS
- evidencia:
  - `py_compile OK`
  - `manage.py check OK`
  - `manage.py test core.tests.test_director_dashboard_tz core.tests.test_ia_pris_tz core.tests.test_finanzas_caja_tz -v 1` -> `3/3 OK`

### Pacientes - formulario y template de alta

- estado: `CERRADO`
- archivos:
  - `pacientes/views.py`
  - `pacientes/templates/pacientes/crear_paciente.html`
  - `pacientes/tests.py`
- resultado:
  - se corrigio `PacienteForm` para usar solo campos reales del modelo
  - se agrego el template faltante `crear_paciente.html`
  - el flujo de alta de pacientes dejo de caer por `FieldError` / `TemplateDoesNotExist`
- evidencia:
  - `manage.py check OK`
  - `manage.py test pacientes.tests --verbosity=2 --no-input` -> `7 OK (1 skipped)`

### Farmacia - endurecimiento post-refactor

- estado: `CERRADO`
- archivos:
  - `farmacia/urls.py`
  - `farmacia/views/soporte.py`
  - `farmacia/views/__init__.py`
  - `farmacia/views/pdv.py`
  - `farmacia/tests.py`
- resultado:
  - se resolvio la colision de `api/lotes-producto`
  - apertura y verificacion de caja ya filtran por `empresa`
  - `KardexListView` devuelve `none()` si no hay empresa
  - `pdv_farmacia` ya usa el resolvedor canonico de empresa
- evidencia:
  - `manage.py check OK`
  - `manage.py test farmacia.tests --verbosity=2` -> `31 OK`
  - reporte adicional de cierre: `21/21` tests nuevos verdes sobre AperturaCaja, CorteCaja, EntradaExpress, COFEPRIS y CargaMasiva
- residual:
  - se conservan 3 fallos preexistentes documentados fuera del cierre de esta ronda

### Enfermeria - cierre con pruebas reales

- estado: `CERRADO`
- archivos:
  - `enfermeria/tests.py`
  - `docs/ai_coordination/reporte_auditoria_enfermeria.md`
- resultado:
  - el modulo tiene cobertura funcional y de tenant en pruebas automatizadas
  - se valido dashboard, triage, captura de signos, historial, graficas, alertas y formularios
- evidencia:
  - `manage.py check OK`
  - `manage.py test enfermeria.tests` -> `17/17 OK`

### Inventario - cierre funcional con regresiones

- estado: `CERRADO`
- archivos:
  - `inventario/views.py`
  - `inventario/views_consultorio.py`
  - `inventario/views_generales.py`
  - `inventario/views_compras.py`
  - `inventario/models.py`
  - `inventario/templates/inventario/lista_lotes.html`
  - `inventario/tests/test_inventario.py`
- resultado:
  - se corrigio el `FieldError` por mezcla `DecimalField/FloatField` en agregaciones con `Coalesce(Sum(...), Value(...))`
  - se corrigio el `TemplateSyntaxError` por `_semaforo` en template
  - se agrego propiedad publica `semaforo` al modelo para soporte correcto en vistas/templates
  - se limpiaron asignaciones redundantes y imports asociados al flujo de inventario
- evidencia:
  - `manage.py check OK`
  - `manage.py test inventario.tests.test_inventario` -> `31/31 OK`

### Bloque operativo - recepcion / logistica / mantenimiento / academia / marketing

- estado general:
  - `Recepcion` -> `CERRADO` con suite completa verde
  - `Logistica` -> `CERRADO`
  - `Mantenimiento` -> `CERRADO`
  - `Academia` -> `CERRADO`
  - `Marketing` -> `CERRADO`
- resultado reportado:
  - logistica: `7/7 OK`
  - mantenimiento: `4/4 OK`
  - academia: `8/8 OK`
  - marketing: `9/9 OK`
- precision canonica:
  - recepcion ya tiene fix local integrado para el bug TZ y una suite canonica nueva, pero sigue con discrepancia abierta: el checklist oficial la marca cerrada con redireccion unificada, mientras la validacion limpia local aun no confirma ese cierre definitivo
  - logistica, mantenimiento, academia y marketing quedan promovidos a `CERRADO` por checklist oficial + reporte maestro del 2026-06-25

### RH/Nómina - endurecimiento de seguridad y cobertura

- estado: `CERRADO` (revalidado 2026-06-27)
- archivos:
  - `core/tests/test_rh_nomina_security.py`
  - `core/views/nomina.py`
  - `core/views/rh.py`
  - `core/admin.py`
  - `core/models/rrhh.py`
- resultado:
  - `CompetenciaAdmin` restringido a superuser con pruebas explícitas de change/delete para ADMIN no-superuser
  - wrappers legacy de nómina protegidos con `@role_required` (como wrappers internos, no endpoints públicos)
  - `mis_resultados` aislado por tenant en `core/views/rh.py:498`
  - `_empresa()` falla con `PermissionDenied` en `core/views/nomina.py:24`
  - `Competencia` documentada como catálogo global en `core/models/rrhh.py:141`
- evidencia:
  - `manage.py check OK`
  - `manage.py test core.tests.test_rh_nomina_security --keepdb -v 0` -> **25/25 OK** (76s, sin timeout)
  - suite `test_rh_nomina_security` reforzada con tests de CompetenciaAdmin (P2 corregido)
- nota: el residual de timeout documentado anteriormente no se reproduce en el arbol actual



### IoT - kioscos multi-tenant e IP allowlist

- estado: `CERRADO`
- archivos:
  - `iot/models.py`
  - `iot/views.py`
  - `iot/migrations/0005_kiosco_empresa.py`
  - `iot/tests.py`
- resultado observado en codigo:
  - `Kiosco` ahora tiene FK `empresa`
  - las vistas administrativas ya filtran por `empresa`
  - `api_kiosco_heartbeat`, `api_kiosco_confirmar` y `api_kiosco_rechazar` validan IP con `_get_ip(request)`
  - existe suite nueva `IoTKioscoSecurityTests`
- precision canonica:
  - la documentacion oficial ya lo promueve a `CERRADO` con migracion `0005`, suite `iot.tests` y nota explicita de ejecucion con `--keepdb`
- mantener fuera del cierre solo el paso operativo de deploy y validacion fisica de kioscos en red local

### Recepcion - cierre reproducible en arbol canonico

- estado: `CERRADO`
- archivos:
  - `recepcion/views.py`
  - `recepcion/tests.py`
  - `core/views/general.py`
- resultado:
  - la redireccion de `RECEPCION` ya quedo unificada en `core/views/general.py` hacia `recepcion:dashboard_recepcion` tanto por grupo como por `rol`
  - `recepcion/views.py` ya usa `timezone.localdate()` en `dashboard_recepcion` y `lista_espera`
  - se cerro el bypass operativo por tenant implicito: `Recepcion` ya no acepta usuarios sin FK `empresa` aunque el middleware resuelva una empresa por defecto
  - la suite canonica valida redirect sin empresa, bloqueos cross-tenant y regresiones TZ
- evidencia:
  - `manage.py test recepcion.tests --keepdb -v 0` -> `5 OK`
  - la suite completa quedó verde y el estado documentado se considera `CERRADO`

### Seguridad - revalidacion local final

- estado: `CERRADO`
- archivos:
  - `seguridad/views.py`
  - `seguridad/tests.py`
  - `core/decorators.py`
- resultado:
  - la suite del modulo ya corre limpia sobre este arbol canonico
  - 2FA, boton de panico y rastro paciente quedaron revalidados con evidencia reproducible
  - el warning de Sentinel sobre 403 sin empresa corresponde al comportamiento esperado del bloqueo, no a una fuga tenant
- evidencia:
  - `manage.py test seguridad.tests --keepdb -v 1` -> `9 OK`

### Bienestar - cierre de auditoría y hardening

- estado: `CERRADO`
- archivos:
  - `config/urls.py` (resolución de colisión de rutas)
  - `bienestar/views.py` (timezone localdate)
  - `core/views/bienestar.py` (timezone localdate + redirect NOM-035 corregido)
  - `core/tests/test_bienestar_nom035.py` (regresión endurecida)
  - `core/templates/includes/sidebar.html` (rutas actualizadas)
- resultado:
  - **B1 (CORREGIDO)**: colisión de URL en `/bienestar/` — NOM-035 sombreaba Espacio Seguro. Rutas NOM-035 movidas a `/bienestar-staff/`.
  - **B6 (CORREGIDO)**: `timezone.now().date()` → `timezone.localdate()` en 8 ubicaciones de `bienestar/views.py` y `core/views/bienestar.py`.
  - **B7 (CORREGIDO)**: `evaluacion_nom035` redirigía a `dashboard_bienestar`, nombre inexistente tras el cambio de rutas. Sentinel lo estaba enmascarando como auto-repair. Se corrigió a `bienestar_dashboard` y la prueba ahora valida el destino exacto.
  - **B2-B5 (DESCARTADOS)**: `DiarioEmocional`, `RecursoCrecimiento`, `EvaluacionNOM035`, `DiarioEmocionalStaff` sin FK `empresa`. El aislamiento por `usuario` es suficiente (Usuario es único global). `RecursoCrecimiento` es catálogo global intencional.
  - Superficie dual verificada como intencional: `bienestar/views.py` (Espacio Seguro), `core/views/bienestar.py` (NOM-035 Staff), `core/views/bienestar_mejorado.py` (Alertas PRIS).
  - Tenant isolation confirmada en todos los modelos con FK `empresa`: `ConversacionBienestar`, `AlertaBienestar`, `SesionCoachingStaff`, `AlertaBurnout`, `ProgramaCapacitacion`.
- evidencia:
  - `manage.py check` -> `System check identified no issues (0 silenced)`
  - `manage.py test bienestar.tests core.tests.test_bienestar_nom035 core.tests.test_bienestar_mejorado --keepdb -v 0` -> `19 OK`
  - validación directa HTTPS de `evaluacion_nom035` -> `302 /bienestar-staff/` + `AlertaBurnout` creada

### Contabilidad / Finanzas - AUDITORIA PROFUNDA CERRADA

- estado: `CERRADO` (auditoria profunda 2026-06-26)
- fuente:
  - `docs/ai_coordination/ESTADO_CONTABILIDAD_FINANZAS_CIERRE_TOTAL_V2.md`
  - auditoria profunda Cascade 2026-06-26: verificacion contra arbol real, endurecimiento except Exception, suite completa
- archivos reportados:
  - `contabilidad/models.py`
  - `contabilidad/migrations/0012_catalogo_cuentas_polizas.py`
  - `core/views/contabilidad.py`
  - `core/views/reportes_financieros.py`
  - `core/views/cuentas_por_cobrar.py`
  - `core/views/motor_financiero.py`
  - `config/urls.py`
  - `core/tests/test_contabilidad_general.py`
  - `core/tests/test_finanzas_roles_regression.py`
- resultado documentado:
  - `FacturaCFDI.empresa` queda como FK canónica multi-tenant y `NOT NULL`
  - existen modelos reales `CuentaContable`, `Poliza`, `AsientoContable`
  - dashboard, catálogo, pólizas, autorización, reportes y balance general quedan operativos
  - CxC / convenios siguen activos en `/finanzas/...`
  - se corrige la cifra inflada histórica de `test_cfdi_borrador_auto`: son `2 tests`, no `22`
  - `dashboard_contabilidad` ya filtra ingresos por `estado='COMPLETADA'`, evitando inflar ingresos con ventas canceladas
  - `core/views/cuentas_por_cobrar.py` ya usa `timezone.localdate()` en CxC / convenios
- evidencia recibida:
  - `manage.py check`
  - `manage.py makemigrations --check`
  - `manage.py test core.tests.test_contabilidad_general --verbosity=2`
  - `manage.py test contabilidad.tests.test_finanzas_seguridad.DashboardFinancieroTests --verbosity=2 --keepdb`
- auditoria profunda 2026-06-26:
  - `FacturaCFDI.empresa` NOT NULL canónico confirmado en modelo + migraciones 0008→0011
  - `CxC / convenios` usan `timezone.localdate()` — confirmado
  - Dashboard contable NO reintroduce conteo falso — confirmado
  - `except Exception` en `contabilidad/facturama_api.py:113` endurecido a `(ValueError, KeyError, TypeError, OSError)` con justificación explícita
  - Superposición de rutas `/contabilidad/` documentada como deuda arquitectónica sin impacto funcional (include sin path vacío)
  - 48 tests ejecutados en esta pasada: exit 0, OK
- evidencia directa:
  - `manage.py check` → 0 issues
  - `manage.py makemigrations --check` → No changes
  - `manage.py test core.tests.test_contabilidad_general contabilidad.tests.test_finanzas_seguridad core.tests.test_finanzas_roles_regression --keepdb -v 1` → **48 tests OK** (exit 0)
- deuda arquitectonica residual (confirmada intencional 2026-06-27):
  - polizas manuales sin generacion automatica de asientos desde ventas — diseno intencional: entrada manual de contadores
  - balance con fallback proxy si no hay asientos — correcto: retorna cero, no falla
  - timbrado con mocks via set_facturama_factory_for_tests() — patron correcto para CI; FacturamaAPI real se usa en produccion
  - superposicion path /contabilidad/ (include + dashboard directo) — sin impacto funcional

### Buzon / Comunicacion / Notificaciones - cierre operativo documentado

- estado: `REPORTE_INTEGRADO`
- fuente:
  - reporte recibido `2026-06-25`
  - cierre profundo adicional entregado por `Claude` sobre `core/views/buzon.py`
- resultado documentado:
  - se reportan 7 bugs confirmados y corregidos sobre permisos, `@require_POST`, campo de fecha, manejo `Http404`, bug lógico de reapertura y respuesta sin empresa
  - se agrega suite nueva `test_buzon_notificaciones.py` con cobertura funcional y de tenant/roles
  - Claude añade 3 hallazgos profundos corregidos: colisión funcional de `buzon_kanban`, 500 en vez de 404 en `api_cambiar_estado_queja`, y tenant arbitrario en `tu_opinion`
- evidencia recibida:
  - `manage.py test core.tests.test_multi_tenant_isolation core.tests.test_buzon_notificaciones`
  - `manage.py check`
- residual declarado por el propio reporte:
  - rate limiting en `tu_opinion` como mejora opcional
  - ampliar `ejecutar_verificaciones` si se quiere cubrir más que órdenes de laboratorio
- precision canonica:
  - `core/templates/core/tu_opinion.html` ya contiene `{% csrf_token %}`; ese residual anterior queda descartado
  - este bloque queda integrado como cierre operativo fuerte, con fixes profundos ya presentes en el árbol local
  - Imperium entra después como auditor profundo de alto nivel, no como confirmador del reporte

### Operaciones - tenant canonico y cobertura propia

- estado: `CERRADO`
- archivos:
  - `core/views/operaciones.py`
  - `core/tests/test_operaciones_module.py`
- resultado:
  - `rutas_recoleccion` ya usa `empresa_efectiva_request(request)` en vez de `getattr(request.user, 'empresa', None)`
  - el modulo ya rechaza usuarios sin FK `empresa` aunque exista fallback de empresa por defecto en middleware
  - `monitor_rutas` queda cubierto como alias estable del mismo flujo
- evidencia:
  - `manage.py test core.tests.test_operaciones_module --keepdb -v 1` -> `4 OK`

## Modulos cerrados al corte actual

- Consultorio PDF / tenant efectivo
- Director
- IA/PRIS (fix TZ dentro del alcance Director/IA/PRIS)
- Pacientes
- Laboratorio como flujo funcional principal
- Enfermeria
- Inventario
- Farmacia
- Logistica
- Mantenimiento
- Academia
- Marketing
- IoT
- RH / Nomina (código endurecido; deuda: suite con timeout)
- Seguridad
- Operaciones
- Bienestar
- Contabilidad / Finanzas (auditoria profunda cerrada 2026-06-26)

## Modulos casi cerrados al corte actual


## Modulos abiertos al corte actual

- Ninguno

## Modulos en proceso no consolidados en este corte

- Ninguno

## Reportes finales integrados

- Ninguno. Los cierres de Contabilidad / Finanzas y Buzon / Comunicacion / Notificaciones ya quedaron integrados como baseline historico.

## Pendientes prioritarios vivos

- Ninguno funcional en el codigo local.
- `branch protection` / `rulesets` en GitHub: verificados por evidencia funcional; `H-001` corregido en `release/v1.0-local`.

## Deploy confirmado en VPS

- fecha: `2026-07-16`
- commit desplegado: `1b2d42e`
- servidor: `216.238.89.243`
- ruta productiva: `/opt/prislab/app`
- validaciones ejecutadas:
  - `git -C /opt/prislab/app rev-parse --short HEAD` -> `1b2d42e`
  - `systemctl is-active prislab-gunicorn` -> `active`
  - `systemctl is-active prislab-celery` -> `active`
  - `systemctl is-active prislab-celerybeat` -> `active`
  - `curl -I https://prislab.labcorecloud.com` -> `HTTP/2 200`
- alcance real del deploy:
  - produccion ya contiene el cierre verificado de `Seguridad` y `Operaciones`
  - Recepcion queda como cierre funcionalmente verificado y cerrado en la rama local
  - el despliegue de hoy sincronizo el arbol real hasta `1b2d42e` y resolvio el bloqueo de `collectstatic` causado por el mapa faltante de Chart.js

## Ultima verificacion recibida de Claude

Se recibio un cierre de evidencia adicional sobre la tanda de seguridad / tests:

- `SEC-2FA` quedo verificado con la regla actual: `127.0.0.1` y `192.168.*` ya no exentan por defecto.
- La suite global reportada por Claude quedo mayormente verde:
  - `315` tests
  - `297` OK
  - `14` skipped
  - `2` errores de entorno/herramienta
- Consultorio quedo validado inicialmente con `36/36` tests OK.
- Farmacia quedo validada con `18/18` tests OK.
- La superficie IA quedo con `3` tests OK y placeholders claramente marcados.
- Pendiente real detectado por esa misma tanda:
  - contradiccion de aislamiento LIMS en `test_lims_config_tenant_security.py`
  - `api_rangos_parametro` expone datos cross-tenant en un caso de prueba
  - la configuracion LIMS necesita root-cause antes de darlo por cerrado
- Artefacto persistido:
  - [docs/ai_coordination/inbox/20260624_claude_SEC_2FA_TESTS_LIMS.md](./inbox/20260624_claude_SEC_2FA_TESTS_LIMS.md)

Nota de reconciliacion:

- el reporte de Claude sobre Director/IA/PRIS apuntaba a una PR separada; Codex confirmo que ese fix no estaba integrado en `release/v1.0-local` y lo reaplico/valido localmente en el arbol canonico actual
- el reporte viejo que decia que `INDICE_CANONICO_TOTAL.md` o `INVENTARIO_MAESTRO_TOTAL.md` no existian ya no aplica al estado actual del repo

## Verificacion de contrapeso sobre Core

Se reviso el reporte de Cascada sobre `core/middleware/pris_context.py` y el fix queda aprobado:

- el archivo real ya usa import lazy con fallback seguro
- `manage.py check` pasa sin issues
- la correccion valida es la resiliencia por-request ante fallos de `get_pris_context`
- la explicacion del riesgo en el reporte original se ajusto para no confundir fallo de arranque con fallo runtime
- artefacto persistido:
  - [docs/ai_coordination/inbox/20260624_cascada_CORE_PRIS_CONTEXT.md](./inbox/20260624_cascada_CORE_PRIS_CONTEXT.md)

## Revalidacion humana UI mas reciente

Se ejecuto nuevamente el runner humano en produccion y esta corrida reporto una falla de login:

- `ok: false`
- `findingsCount: 1`
- hallazgo: `Login did not redirect to a protected area`
- artefacto persistido:
  - [docs/ai_coordination/inbox/20260624_ui_rerun_login_fail.md](./inbox/20260624_ui_rerun_login_fail.md)

Nota:

- La corrida sigue confirmando que la raiz y el dashboard abren sin 500.
- La falla nueva queda como pendiente de revalidacion porque puede ser credencial/sesion/anti-automation o una regresion de login.

## Diagnostico adicional de login

Se valido que la causa no es 2FA:

- `admin` existe y esta activo
- `TOTP_ACTIVE = False`
- `2FA_FLAG = False`
- `authenticate(username='admin', password='[redacted]')` devolvio `False`

Conclusion:

- la credencial usada para la revalidacion no coincide con la base actual
- `/home/` sigue respondiendo `302` hacia `/login/`
- el problema reproducido es de autenticacion/credencial, no de 500 directo en `/home/`
- artefacto persistido:
  - [docs/ai_coordination/inbox/20260624_login_admin_invalid.md](./inbox/20260624_login_admin_invalid.md)

## Canonical host - normalizacion de dominio

Se alineo el middleware de host canonico para que deje de depender de valores hardcodeados y use entorno real:

- `PRISLAB_CANONICAL_HOST` ahora puede definir el host publico canónico
- `PRISLAB_LEGACY_HOSTS` permite listar hosts antiguos a redirigir
- `CSRF_TRUSTED_ORIGINS` recibe automaticamente el origen canonico cuando falta en produccion

Esto corrige el caso en el que el navegador normal y el modo incognito se comportaban distinto por host/cookie/cache de dominio.

Artefacto persistido:

- [core/middleware/canonical_host.py](../../core/middleware/canonical_host.py)
- [config/settings.py](../../config/settings.py)

## Verificacion humana UI - resultado validado

Se ejecuto una corrida humana automatizada contra produccion con resultado general `OK`:

- login autenticado y redirigido correctamente
- `/` y `/home/` abrieron sin `500`
- Laboratorio acepto texto en el buscador
- Farmacia acepto texto en el buscador
- solo quedaron dos `WARN` de deteccion visual:
  - Consultorio: no se detecto boton de accion de cita en la pantalla inicial
  - Director: la pagina abrio, pero el runner no encontro una accion clave

Artefacto persistido:

- [docs/ai_coordination/inbox/20260624_human_ui_audit_ok.md](./inbox/20260624_human_ui_audit_ok.md)

## LIMS tenant - ajuste de causa raiz

El reporte nuevo de Claude apunta a que el supuesto cross-tenant no era fuga real de datos:

- el filtro por empresa funcionaba
- `lims.views.tenant_lims.empresa_lims()` ahora solo usa la FK explícita del usuario
- `Usuario.save()` ya no auto-asigna empresa por defecto
- `core.tests.test_lims_config_tenant_security` quedó verde (`5/5`)
- Sentinel conserva la degradación para otros errores, pero `Http404` vuelve a responder como `404`

- la contradicción canónica de "usuario sin empresa" quedó cerrada para LIMS

Artefacto persistido:

- [docs/ai_coordination/inbox/20260624_lims_tenant_404_masking.md](./inbox/20260624_lims_tenant_404_masking.md)

## Ruido benigno conocido

- La consola puede mostrar errores de WebSocket contra `localhost` o `localhost.qz.io` por el servicio de impresión/QZ.
- Ese ruido ya se filtró en la herramienta canónica y no debe contarse como hallazgo funcional de negocio.

## Regla de uso

- Todo módulo, flujo y función del canon debe poder probarse y auditarse con evidencia reproducible.
- Si no existe prueba automática, runner humano o evidencia técnica verificable, el tema queda pendiente.
- La verificación humana se ejecuta primero con la herramienta canónica.
- Las IAs leen el `report.md` o `report.json` y luego comparan evidencia.
- No se debe depender de extensiones de navegador para cerrar un flujo.
- No se debe reauditar sin nueva evidencia.
- Si algo no está reflejado en `INDICE_CANONICO_TOTAL.md`, no es fuente de verdad para coordinación.
- Si algo no está reflejado en `INVENTARIO_REAL_REPO.md`, no fue parte del corte ejecutable actual.
- Si algo quedó solo en una lectura estructural externa, debe persistirse antes de usarlo como canon.

## Limpieza de ruido documental

- Los reportes, scripts y notas históricas fuera del canon actual están siendo retirados del árbol de trabajo.
- Lo que queda como `D` en `git status` corresponde a ruido viejo ya separado del canon operativo.
- No debe volver a mezclarse con el flujo nuevo salvo que una instrucción explícita lo reabra.

## Orden operativo

1. Humano ejecuta `npm run human:ui -- --target cloud --user <usuario> --pass <clave>`.
2. Se revisa el `report.md` generado.
3. Codex corrige si hay fallos de código.
4. Claude y Cascada clasifican y contrastan reportes nuevos.
5. Se actualiza el estado canónico solo con evidencia nueva.

## Marca y equivalencias comerciales en Farmacia - 2026-07-23

Se incorporó la trazabilidad de marca/laboratorio y nombres comerciales equivalentes en el flujo de medicamentos:

- La entrada de mercancía permite capturar o seleccionar marca/laboratorio mediante una lista sugerida, conservando texto libre para nuevos laboratorios.
- La entrada permite registrar equivalencias comerciales o nombres de patente separados por coma, sin hardcodear composiciones farmacológicas.
- Las búsquedas de PDV y entrada consultan también las equivalencias comerciales y priorizan la coincidencia exacta del término.
- Kardex muestra marca/laboratorio y equivalencias en cada movimiento; el Libro de Control las muestra junto al producto cuando existen registros.
- El dato de marca y equivalencias se conserva al actualizar un producto existente y queda incluido en la evidencia de auditoría del movimiento.
- Migración aplicada: `core.0085_producto_equivalencias_comerciales`.

La composición de una patente debe validarse con la ficha técnica o fuente regulatoria antes de capturarla como equivalencia; el sistema no inventa ni deduce sustancias activas.

Evidencia de producción tras los despliegues de los commits `8d95298`, `8cf1af5`, `3cda2b5` y `1c72469`:

- búsqueda por marca y equivalencia: `200`, producto encontrado
- formulario de entrada: campos de marca/laboratorio y equivalencias visibles
- Kardex usa la plantilla efectiva `core/templates/farmacia/kardex_list.html` y expone la marca como columna dedicada
- migración aplicada correctamente y servicios activos
- pruebas realizadas con transacción reversible; no se modificó permanentemente el catálogo de producción

## Memoria de precios en entrada de medicamentos - 2026-07-23

Al seleccionar un producto existente en Entrada de Mercancía:

- se precarga el costo de compra vigente (`precio_compra`);
- se precarga el precio al público vigente (`precio_publico`);
- ambos valores se muestran también en el resultado de búsqueda para evitar consultas manuales repetidas;
- el costo puede ajustarse en el momento de la nueva compra si cambió el proveedor;
- el precio de venta vigente se conserva si el usuario no lo modifica explícitamente.

La API de búsqueda de compras expone ambos valores y la interfaz muestra la referencia de memoria junto a cada campo. Evidencia productiva: commit `fa8e999`, respuesta `200` con ambos precios y prueba reversible sin cambios persistentes en catálogo.
