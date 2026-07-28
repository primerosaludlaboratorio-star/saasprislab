# Matriz E2E de Laboratorio y LIMS — 2026-07-28

## Alcance

Esta matriz separa evidencia automática, navegación humana en producción y
pruebas que requieren datos operativos controlados o equipos físicos. No se
declara cierre por una sola página HTTP ni por comandos legacy.

## Resultado actual

| Flujo / escenario | Evidencia | Estado |
|---|---|---|
| Recepción de orden, lista de trabajo y consulta | Suite de pruebas y navegación humana en producción | PASA en smoke; falta transacción productiva controlada |
| Toma de muestra | `core.tests.test_monitor_produccion_workflow` y UI accesible | PASA en lógica; falta ejecución física |
| Captura manual por analito LIMS | `ResultadosLimsService` y pruebas de monitor | PASA en lógica; validar con orden de prueba controlada |
| Rangos, valores críticos, delta check y fórmulas | 48 pruebas focalizadas anteriores + suite clínica | PASA en automatizado |
| Validación humana, justificación y generación/entrega | Suite clínica y navegación de producción | PASA en automatizado/smoke; falta operación con datos controlados |
| Cambio de equipo por analito | Equipo persistido en `ResultadoParametro`, filtro por tenant y metrología | PASA en pruebas locales; falta dos analizadores físicos |
| Equipo inactivo, calibración vencida o canal bloqueado por CCI | `metrologia_lab`, `cci_canal`, `ResultadosLimsService` | PASA en pruebas de reglas; falta prueba operativa con estado real |
| Recepción HL7/ASTM e identificación por IP | 13 pruebas de handshake/equipo | PASA en automatizado; pendiente conexión física |
| Maquila por contingencia | Envío existente más recepción formal implementada; 3 pruebas nuevas | PASA en automatizado; pendiente archivo y resultado real |
| Resultado de maquila, captura y validación posterior | Recepción devuelve orden a `EN_PROCESO`; captura queda habilitada | PASA en automatizado; pendiente prueba humana controlada |
| Maquila duplicada o de otro tenant | Idempotencia y aislamiento cubiertos | PASA |
| CCI Westgard: warning/rechazo | 8 reglas y pruebas de canal | PASA en automatizado |
| CCI rechazado y continuidad | El canal bloqueado no puede validarse sin actuación autorizada; no existe “desactivar y seguir” silencioso | PASA como control de seguridad; requiere definir procedimiento autorizado |
| Falta de energía y envío a maquila | Flujo de maquila disponible si la orden está marcada `requiere_maquila` | PARCIAL: falta operación explícita de contingencia que marque una orden no prevista |
| Impresión, WhatsApp y entrega | URLs accesibles en producción; reglas de triple llave cubiertas | PASA en smoke; falta envío externo con datos controlados |

## Correcciones realizadas en esta revisión

1. Se agregó estado formal de recepción de maquila, usuario, fecha, notas y
   archivo de evidencia.
2. La recepción es idempotente, acotada al tenant y devuelve las órdenes a
   `EN_PROCESO` para captura y validación humana.
3. El selector de equipos de captura ya no expone equipos de otra empresa.
   Un equipo legacy sin empresa solo aparece si tiene una interfaz activa,
   validada o en prueba explícitamente vinculada al tenant.
4. El equipo seleccionado se persiste en cada `ResultadoParametro` para la
   trazabilidad analito-equipo-consumo.
5. La ruta se registró en `config/urls/laboratorio.py`, que es el enrutador
   activo del `ROOT_URLCONF`; el archivo monolítico `config/urls.py` no es la
   ruta canónica actual.

## Evidencia ejecutada

- `manage.py check`: sin problemas.
- `makemigrations --check --dry-run`: sin cambios pendientes.
- Migración limpia hasta `core.0096` y `laboratorio.0019`: completada en SQLite
  de staging local.
- Pruebas focalizadas post-cambio: 16/16 OK.
- Pruebas focalizadas previas de Laboratorio/LIMS: 48/48 OK.
- La navegación humana de producción verificó HTTP 200 y ausencia de errores
  de servidor en recepción, lista de trabajo, consulta, monitor, entrega,
  maquila, control de calidad, captura y catálogo LIMS. No realizó mutaciones.
- Revisión humana productiva del 2026-07-28: 12 rutas autenticadas, todas con
  HTTP 200, 0 errores de consola y 0 solicitudes fallidas. Se incluyeron
  recepción, lista, consulta, toma, monitor, entrega, maquila, control de
  calidad, analitos, perfiles, paquetes y precios.
- Las rutas `/laboratorio/captura/9/` y `/lims/estudios/` redirigieron a sus
  entradas canónicas (`lista-trabajo` y `lims/analitos`) con HTTP 200 y sin
  error de servidor.
- Prueba humana con la orden QA `LAB-20260720-001`: guardar captura manual
  `GLUCOSA=95` respondió HTTP 200 y persistió el valor. La validación posterior
  respondió HTTP 200, generó y persistió el PDF tenant, y dejó la orden en
  `RESULTADOS_LISTOS` con `validado=True` y `aprobado_por_humano=True`.
- Correcciones desplegadas y verificadas: savepoint para errores de rango,
  rutas de PDF acotadas después del prefijo tenant, `upload_to` ejecutado como
  función real y bloqueo FEFO limitado a la fila principal (`of=('self',)`).
  La revisión productiva final es `74f64f5`.
- Suite por grupos ejecutada en este corte: `31/31 OK` para equipos, HL7,
  CCI/Westgard, contingencias y consumo; `39/39 OK` para recepción, captura,
  validación, PDF, entrega, aislamiento y seguridad; `34/34 OK` para la suite
  completa de `laboratorio.tests` con 3 pruebas omitidas por requerir
  PostgreSQL.

## Bloqueadores honestos para el cierre E2E

- No se puede simular una falla física de INCCA, Icon o Wondfo desde el código.
  Requiere desconectar o poner fuera de servicio un equipo de prueba y dejar
  evidencia de la conmutación.
- No se puede demostrar una caída eléctrica real sin un procedimiento de
  contingencia autorizado y datos de prueba; no se debe provocar en producción.
- La recepción de maquila y el aislamiento de equipos están desplegados; falta
  probarlos con un envío/archivo de resultado controlado en producción.
- Producción fue comprobada con `/health/` y devolvió `status=ok`, base de datos
  y cache operativos. `DEPLOYED_REVISION` remoto coincide con `74f64f5`.
- La prueba productiva con efectos debe usar una orden y paciente de prueba
  autorizados, nunca datos clínicos reales sin control.

## Criterio de cierre

Laboratorio/LIMS no se marca 100% cerrado todavía. El siguiente gate es:

1. desplegar este corte local después de revisar diff y pruebas;
2. ejecutar una orden controlada completa en producción;
3. probar dos equipos o equipo alterno con resultado trazado;
4. ejecutar una contingencia de maquila controlada;
5. demostrar bloqueo y liberación autorizada de CCI;
6. verificar PDF, entrega y auditoría final.
