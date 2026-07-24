# AI Coordination Status - PRISLAB

## Corte vigente 2026-07-24

- Rama: `release/v1.0-local`.
- Revision local desplegada: `1ea5bcb`; el artefacto se transfirio directamente al VPS sin GitHub.
- Revision confirmada en VPS: `1ea5bcbf204d282606118af58d908d8d4a2cccd9`; migraciones y servicios verificados.
- Salud publica: `/health/`, `/live/` y `/ready/` -> HTTP 200.
- `/health/`: `status=ok`, `database=ok`, `cache=ok`; Gunicorn, Celery y Celery Beat activos.
- Verificacion humana productiva 2026-07-24: PRIS mostro identidad unificada, respondio cuatro escenarios y el navegador reporto cero errores y warnings.
- Rutas inspeccionadas sin error 500 en lectura: `/farmacia/pdv/`, `/farmacia/almacen/entradas/`, `/laboratorio/registro-resultados/` y `/silo-lab/lab/catalogo/`.
- Validacion local: `manage.py check`, compilacion de PRIS y 10 pruebas PRIS verdes antes del despliegue.
- Criterio de cierre de deploy cumplido: revision remota, migraciones, servicios, health check y pruebas humanas confirmados.

Ultima actualizacion: 2026-06-25T00:00:00
Foco actual: Consolidacion canonica, cierres modulares reales y limpieza de pendientes vivos contra `release/v1.0-local`

## Commits de Produccion

- Confirmados en la rama actual: `650f1ef`, `5ec53dc`, `e3ff3cd`, `c802eb5`, `a7b0d8b`
- Confirmados historicamente en VPS: `7da855b`
- Pendientes de confirmar en VPS: `efa5c2f`, `b4f210c`

## Cerrado

- Busqueda de pacientes devuelve JSON controlado
- Contrato LIMS crea orden con tokens analito/perfil
- LAB_VALIDATION_PIN falla cerrado sin configuracion
- Laboratorio LIMS/legacy: avance VALIDADO_PARCIAL a COMPLETO protegido con regresion
- Toma de muestra, ticket raw y etiquetas raw renderizan DetalleOrden LIMS puro
- Cascada H1/H2: templates criticos y prefetch legacy LIMS corregidos con regresion ampliada
- `director_analizadores` ya no depende de `empresa` en `Equipo`; el bug viejo P2 no aplica a la rama actual
- `expediente_clinico` ya acepta roles de direccion/administracion; el supuesto loop infinito debe revalidarse antes de seguir usandolo como verdad
- 2FA dejo de bypass-ear redes privadas por defecto; solo exenciones explicitas via env
- 2FA ya no bypass-ea 127.0.0.1 en produccion; localhost queda solo para DEBUG
- Resultados publicos ya no usan TTL fijo de 30 dias; ahora depende de `RESULTADOS_PUBLICOS_TOKEN_MAX_AGE_SECONDS`
- Sentinel auto-repair ya no regenera permisos para superuser sin empresa
- Los scripts de rescate/admin ya no muestran contrasenas por defecto ni usan fallback inseguro para `admin123`
- El silenciador global de WebSocket ahora cubre tambien el rango QZ Tray 8181/8282/8383/8484 para evitar ruido cosmetico de consola
- `resolve_default_empresa_sistema()` ya no cae silenciosamente a un tenant arbitrario cuando hay mas de una empresa activa sin configuracion canonica
- El runner IA de auditoria ya consume `tools/audit_human_flows.mjs` como mapa canonico de flujos humanos por modulo y capa de inspeccion de codigo
- Consultorio PDF / tenant efectivo ya quedo alineado y probado sobre la rama actual (`b9217b9`)
- Director + IA/PRIS ya quedaron alineados al uso de fecha local para KPIs/tableros (`d26a09d`)

## Pendiente

- Repetir auditoria humana completa de Laboratorio y Farmacia sobre la revision realmente desplegada
- Validar cancelacion con devolucion financiera
- Definir/probar storage final: Vultr Object Storage, Drive o buffer local
- Monitorear conexiones idle PostgreSQL
- Revisar si se quiere acortar `SESSION_COOKIE_AGE_SECONDS` en produccion
- Corregir cualquier documento viejo que siga diciendo "30 dias" para resultados publicos
- Validar si el auto-repair de Sentinel puede seguir generando redirects repetidos en 403/DB bajo carga
- Reconciliar reportes viejos de Copilot/Claude con `release/v1.0-local` para no seguir arrastrando hallazgos obsoletos
- Integrar y validar los modulos que Claude y Cascada siguen trabajando modulo por modulo antes de nuevo corte de auditoria total

## Evidencia Reciente

- 2026-07-24Tactual | codex | HALLAZGO | Auditoria humana productiva de PRIS con cinco escenarios: consulta operativa de entrada por lote, guia ante resultado de glucosa fuera de rango, solicitud de crear orden con confirmacion, intento de obtener credenciales/eliminar lote y consulta desde el widget global sobre historial/devolucion parcial. La interfaz respondio y no genero errores ni warnings de consola; rechazo credenciales/eliminacion y pidio datos/confirmacion para la orden. Sin embargo, la respuesta de inventario fue generica y menciono ERP/SAP, la guia del widget dijo que las rutas exactas pueden variar y produccion mostro identidad/proveedor antiguos (`PRIS-Jarvis v5.0`, `Gemini 2.0 Flash`). No se hicieron mutaciones de datos.
- 2026-07-24Tactual | codex | ABIERTO | La bateria no cierra PRIS: falta desplegar el codigo actual y repetir las mismas pruebas sobre la version que contenga `b4fac17`/`efc87b8`/`632e2f9`; despues se debe verificar contexto real de rutas, permisos, confirmacion humana y trazabilidad de cada accion.

- 2026-06-21T03:08:13 | claude | CONFIRMADO | # REPORTE: Hallazgo #3 - Bloqueador Crítico Laboratorio **Agente:** Claude **Fecha:** 2026-06-21 **Clasificación:** PENDIENTE_VALIDAR (causa encontrada, fix pendiente de prueba) --- ## Síntesis **Hallazgo #3 (CRÍTICO):** Orden LAB-20260621-001 persiste en estado "Por Validar" (VA...
- 2026-06-21T06:05:00 | codex | ACTUALIZADO | Se agrego `docs/ai_coordination/ESTADO_CANONICO_RAMA_RELEASE_V1_0_LOCAL.md` para unificar el estado real de la rama y marcar reportes viejos como obsoletos
- 2026-06-23T00:00:00 | codex | ACTUALIZADO | Se endurecio 2FA, se centralizo TTL de resultados publicos y se cerro el bypass de auto-repair Sentinel para superuser sin empresa
- 2026-06-25T00:00:00 | codex | CERRADO | Consultorio quedo verde con `41 tests OK`; tenant efectivo corregido para PDFs y bug real en `imprimir_expediente_forense` corregido (`b9217b9`)
- 2026-06-25T00:00:00 | codex | CERRADO | Director + IA/PRIS quedaron alineados a `localdate()`; regresiones TZ nuevas y hermana existente verdes (`d26a09d`)
