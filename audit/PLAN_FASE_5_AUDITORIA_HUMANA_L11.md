# Plan Fase 5 - Auditoria humana integral L11

## Objetivo y reglas

Validar PRISLAB como lo usarian personas reales, desde el acceso hasta el
cierre de cada operacion. Se comprobara funcionalidad, integracion entre
modulos, permisos, aislamiento por empresa, usabilidad, ortografia,
consistencia visual, documentos y recuperacion ante errores.

Este plan es independiente de reportes historicos. Todo resultado debe indicar
commit, entorno, fecha, URL, rol, empresa, datos y evidencia. Una prueba
aislada de una vista o boton no cierra un flujo.

No se permite usar o exponer contrasenas en reportes, modificar datos reales,
declarar PASS sin evidencia, corregir codigo durante una corrida ni mezclar
resultados de commits, entornos o tenants. En produccion solo se permiten
consultas y datos sinteticos reversibles. Las escrituras deben hacerse en
staging o con datos marcados AUDIT-YYYYMMDD.

La auditoria de observacion es read-only. La prueba funcional con escritura es
una fase separada, ejecutada solo en staging o en un tenant de pruebas
autorizado. Nunca se debe confundir una escritura reversible de prueba con una
modificacion permitida en produccion.

## Perfiles

1. Paciente: portal, citas, consentimiento, resultados y descarga.
2. Recepcion: paciente, agenda, orden, consentimiento y cobro.
3. Vendedor de farmacia: catalogo, receta, lotes, venta, caja y devolucion.
4. Quimico/Laboratorio: recepcion, toma, captura, validacion y correccion.
5. Medico: expediente, orden, resultados, receta y autorizaciones.
6. Auditor de calidad: trazabilidad, resultados, bitacora y reportes.
7. Administrativo/RH: usuarios, asistencia, nomina y permisos de su area.
8. Gerente: cortes, reportes, inventario y metricas de su empresa.
9. Director/Administrador: configuracion y autorizaciones permitidas.
10. Auditor tecnico: tenant, RBAC, CSRF, errores, red y documentos.

Cada perfil debe probar tambien URLs directas no autorizadas, enlaces de otro
modulo y registros de otra empresa.

## Division entre tres auditores

Auditor A cubre farmacia, inventario, caja, devoluciones y experiencia de
usuario. Auditor B cubre laboratorio/LIMS, expediente, medico, paciente, PDF y
calidad. Auditor C cubre integracion tecnica, RBAC, multi-tenant, errores,
accesibilidad, ortografia, rendimiento observable y consistencia transversal.

Cada auditor repite una muestra cruzada del 20 por ciento de los flujos de los
otros. Los escenarios usan IDs unicos F5-A-001, F5-B-001 y F5-C-001.

## Modulos y flujos

### Acceso y plataforma

- Login, logout, expiracion, sesiones concurrentes, recuperacion y 2FA.
- Rate limit, mensajes de error, seleccion de empresa y sucursal.
- Menu por rol, navegacion, breadcrumbs, enlaces profundos y volver.
- Desktop, tablet, movil, zoom, teclado, foco y estados de carga.
- Errores 400, 403, 404, 409, 429, 500 y desconexion.

### Pacientes y recepcion

- Alta, busqueda, homonimos, duplicado, edicion y campos obligatorios.
- Cita, llegada, orden, consentimiento, cancelacion y reprogramacion.
- Paciente ajeno: no debe aparecer ni abrirse.
- Historial, saldo, privacidad y entrega de resultados.

### Farmacia e inventario

- Producto con y sin codigo de barras, edicion y codigo equivocado.
- Lote, caducidad, precio, existencia, compra y entrada express.
- Recepcion parcial, ajuste autorizado y bloqueo de caducados.
- Antibiotico con receta, antibiotico con jeringa y jeringa sola.
- Pieza/fraccion, precio especial, cupon, descuento y redondeo.
- Efectivo, tarjeta, transferencia, pago parcial, total y saldo.
- Cancelacion antes/despues del pago y reversa de inventario.
- Devolucion parcial/total, autorizacion y consulta del historial.
- Cortes, historial de cortes, diferencias y exportacion Excel.
- Filtros, paginacion, descarga, alta y enlaces a la pantalla correcta.

### Laboratorio y LIMS

- Catalogo de analitos humanos y exclusion de veterinarios.
- Cotizacion, orden, prioridad, convenio y precio.
- Recepcion, identificacion, etiquetas, toma y rechazo de muestra.
- Lista de trabajo, asignacion, captura, unidades y rangos.
- Resultado normal, critico, texto, decimal, cualitativo y sin dato.
- Validacion por rol, doble validacion y sello de tiempo.
- Intento de editar validado, correccion controlada y motivo.
- Version anterior, nueva version, excepcion, repeticion y muestra insuficiente.
- Autorizacion, liberacion, entrega, reimpresion y descarga de PDF.
- HL7, notificaciones, panic button y cierre de orden.
- Doble envio y edicion concurrente por dos quimicos.

### Medico, expediente y paciente

- Consulta, nota, diagnostico, receta, certificado y firma.
- Expediente por paciente y empresa, consentimiento, audio y privacidad.
- Resultados pendientes, validados, entregados y saldo bloqueado.
- PDF legible, completo, descargable y sin URL publica insegura.
- Historial de cambios, sellado, acceso forense y bloqueo de edicion.

### Administracion, RH y finanzas

- Crear, editar, desactivar y reactivar usuarios.
- Jerarquia de roles y prohibicion de autoelevacion.
- Sucursal, permisos, modulos y expiracion.
- Asistencia, incidencia, autorizacion y documentos privados.
- Nomina, contabilidad, poliza, autorizacion y segregacion.
- Cuentas por cobrar, pagos, cortes y reportes.
- Dashboard limitado al rol y tenant correcto.

### Integraciones y operaciones

- Celery, Redis, correo, WhatsApp, webhook, IA y almacenamiento.
- Reintento, timeout, respuesta vacia y proveedor caido.
- PDF, Excel y CSV realmente descargables y legibles.
- Backup, restauracion, fallo controlado y reporte de recuperacion.
- Sentinel, monitoreo, health check e impresion sin SSRF.

## Variantes obligatorias

Cada flujo normal debe repetirse con doble clic, recarga durante POST,
navegador atras, doble sesion, edicion concurrente, perdida de red antes y
despues de guardar, timeout, campos vacios, exceso de longitud, HTML, SQL,
Unicode, fechas de zona horaria, importes cero/negativos/maximos/centavos,
archivo invalido/grande/corrupto, token expirado, CSRF ausente, rol inferior,
ID de otra empresa y datos veterinarios donde no correspondan.

## Usabilidad, lenguaje y consistencia

En cada pantalla se registra si el objetivo se entiende en 10 segundos, si el
boton principal y el siguiente paso son evidentes, si las etiquetas son
humanas, si los mensajes indican como resolver el problema y si existe
confirmacion antes de acciones destructivas.

Tambien se revisan estados de carga, vacio y error; tablas, filtros y
descargas; contraste, foco, teclado, texto alternativo y responsive.

Se levanta un inventario de textos con pantalla, texto actual, correccion,
severidad y captura. Se corrigen tildes, mayusculas, signos, concordancia,
fechas, moneda, unidades y nombres de estados de forma consistente en todo
el sistema, no solo en una pantalla.

## Procedimiento por escenario

1. Preparar datos sinteticos y registrar IDs iniciales.
2. Confirmar rol, empresa y sucursal visibles.
3. Ejecutar el flujo completo normal.
4. Verificar la siguiente pantalla y el modulo receptor.
5. Confirmar estado, folio, saldo, inventario, auditoria y notificacion.
6. Recargar, volver, abrir otra sesion y repetir el ultimo paso.
7. Ejecutar cancelacion, edicion, duplicado, timeout y reintento.
8. Probar la misma accion con rol inferior y tenant ajeno.
9. Verificar efectos secundarios y limpiar solo datos propios de la prueba.

## Evidencia y hallazgos

Cada prueba contiene ID, fecha UTC, commit, entorno, URL base, auditor,
perfil, empresa, sucursal, precondiciones, pasos, esperado, real, capturas,
IDs, estados, efectos relacionados, resultado y limpieza.

Los resultados permitidos son PASS, FAIL, BLOCKED y NO_PROBADO. BLOCKED exige
causa externa comprobable. Un hallazgo incluye severidad, reproducibilidad,
impacto, pasos, URL, rol, tenant, esperado, real y evidencia. Nunca incluye
contrasenas, tokens, API keys, PII innecesaria o datos productivos.

Cada hallazgo usa un identificador unico con el formato HUM-MODULO-###. Debe
separar explicitamente HECHO, OBSERVACION, INFERENCIA, HIPOTESIS y
RECOMENDACION. La confianza Alta solo se permite cuando se trazaron request,
vista, template, persistencia, auditoria y respuesta observada. La confianza
Media requiere una verificacion pendiente. La confianza Baja es una sospecha
que no puede presentarse como defecto confirmado.

Un hallazgo tecnico debe incluir archivo y linea. Uno de interfaz debe incluir
template/componente, selector o texto visible, URL, captura y el flujo que lo
renderiza. Ningun numero de cobertura puede ser estimado: debe derivarse de
un inventario contable.

Critica significa acceso cross-tenant, perdida de datos, cobro incorrecto,
publicacion clinica insegura o accion destructiva sin control. Alta significa
bypass de rol, alteracion clinica/financiera, integridad rota o bloqueo del
flujo principal. Media y baja cubren impacto limitado y problemas de interfaz.

## Criterios de cierre

Fase 5 no se cierra hasta que cada modulo y perfil tenga matriz ejecutada,
todos los flujos principales tengan PASS de inicio a fin, no existan FAIL
criticos o altos abiertos, cada correccion tenga regresion verde, los PDFs y
exportaciones hayan sido abiertos, y ortografia y consistencia tengan
inventario corregido o aceptado.

Tambien se requiere muestra cruzada independiente, reporte consolidado con
omisiones y limites, y reconciliacion de commit, entorno y artefactos. Tener
pantallas construidas o tests verdes no equivale a cierre humano.

## Auditoria independiente y conciliacion

Los tres auditores reciben exactamente el mismo commit, entorno, glosario,
cuentas de prueba y este plan. Durante la primera entrega no pueden leer los
reportes de los otros ni adaptar sus conclusiones al consenso. Cada reporte
indica el IDE, modelo, version, fecha UTC, commit, URL base y modo de acceso.

La conciliacion se realiza despues de recibir los tres reportes y compara
evidencia, no solo titulos o severidades:

1. Unificar hallazgos con evidencia equivalente, conservando todos los pasos.
2. Marcar coincidencias, exclusivos y discrepancias de severidad.
3. Reproducir manualmente cada exclusivo antes de aceptarlo o descartarlo.
4. Unir las pruebas propuestas por los tres; nunca quedarse solo con la
   interseccion.
5. Resolver cada hallazgo en confirmado, refutado, pendiente o bloqueado.
6. Crear un backlog de remediacion separado, sin editar durante la auditoria.

El reporte consolidado debe incluir una matriz Modulo x Rol x Tipo de prueba
con estados cubierto, parcial, no cubierto o bloqueado. Tambien debe contar
modulos, pantallas, endpoints, formularios, roles, entidades y escenarios.

## Entregables obligatorios por auditor

Cada auditor entrega:

- AUDITORIA_INTEGRAL_<IDE>_<FECHA>.md con mapa, roles, flujos, hallazgos,
  cobertura, omisiones y autoevaluacion.
- escenarios.csv con ID, modulo, rol, precondicion, pasos, esperado, real,
  resultado y evidencia.
- hallazgos.csv con ID, categoria, severidad, confianza, ubicacion y estado.
- capturas o referencias de evidencia sin PII innecesaria.
- lista de comandos, URLs, commit y entorno usados.

El auditor declara al final: modo solo lectura respetado, si hubo datos creados,
si fueron limpiados, que no pudo probar y por que. Un archivo o modulo no
revisado se etiqueta NO AUDITADO, nunca limpio.

## Reglas especiales de interfaz

La revision de UI no se limita a que una pagina cargue. Para cada pantalla
critica se verifica objetivo, jerarquia, accion primaria, estados vacio/carga/
error/exito, recuperacion, confirmaciones, mensajes accionables, consistencia
de nombres y navegacion de entrada y salida.

Se debe revisar texto visible, labels, placeholders, tooltips, validaciones,
alertas, tablas, PDF, Excel, correo y mensajes de API presentados al usuario.
Se registra texto exacto, correccion propuesta, regla gramatical aplicable,
impacto y todas las pantallas donde se repite. La correccion no se aplica en
esta fase.

## Revision de omisiones

Antes de cerrar el reporte, cada auditor responde con evidencia:

- Que aplicaciones, URLs, vistas, templates, APIs y modelos existen.
- Que roles, empresas y sucursales se probaron.
- Que flujos normales, alternos, cancelaciones, errores y recuperaciones se
  ejecutaron.
- Que funciones visibles, ocultas, duplicadas o muertas se encontraron.
- Que integraciones, PDFs, exportaciones, auditoria y notificaciones se
  comprobaron.
- Que escenarios de concurrencia, doble envio y perdida de red se probaron.
- Que accesibilidad, responsive, lenguaje y consistencia se revisaron.
- Que quedo fuera por falta de acceso, datos, infraestructura o tiempo.

La ausencia de evidencia en cualquier respuesta se clasifica como
NO_PROBADO o BLOCKED, no como PASS.

## Instruccion para cada auditor IA

Trabaja solo sobre PRISLAB y el commit/entorno indicado. No edites codigo ni
ejecutes cambios destructivos. Comportate como el perfil asignado, completa
los flujos de inicio a fin y verifica sus efectos en los modulos siguientes.
Registra cada paso y evidencia. No conviertas inferencias en hallazgos
confirmados ni una pantalla cargada en funcionalidad aprobada. Entrega JSON y
Markdown con escenarios, capturas, URLs, esperado/real, fallos, bloqueos,
datos creados y limpieza. No cambies el repositorio.
