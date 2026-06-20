# Checklist de control PRISLAB

Fecha de corte: 2026-06-18

Este checklist consolida el estado de la migración entre el sistema legado y PRISLAB SaaS.
La intención es tener un tablero único para avanzar sin perder contexto.

## Protocolo obligatorio de actualización

Toda IA, desarrollador o revisor que haga cambios en código, despliegue, pruebas, variables, infraestructura o datos debe actualizar este archivo en el mismo movimiento.

También debe actualizar:

- [REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md)
- [PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md) si cambia el enfoque de auditoría o la forma oficial de revisión

Si este checklist no se actualiza, el cambio no cuenta como cerrado.

## Estado técnico de corte

- [x] `manage.py check` OK
- [x] `makemigrations --check --dry-run` OK
- [x] `manage.py test` global OK (`251 tests`, `23 skipped`, `0 failures`, `0 errors`)
- [x] Endurecimiento post-auditoría aplicado en `settings.py`, `docker-compose.yml` y `nginx/conf.d/prislab.conf`
- [x] Regresión focalizada post-endurecimiento OK (`16 tests`, `0 failures`)
- [x] Hallazgos reales de auditoría cerrados en código: rate limit con IP final de `X-Forwarded-For` y bloqueo de cantidades no válidas en `registrar_venta_farmacia`
- [x] Regresión de auditoría adicional OK (`4 tests`, `0 failures`) en `core.tests.test_rate_limit_middleware` y `core.tests.test_pris_tools_operativos_security`
- [x] Endurecimiento adicional aplicado: `PRISLAB_TENANT_STRICT_MODE`, `buscar_o_crear_paciente` ya no crea sin confirmación, y `OMNI_BYPASS_TOKEN` queda bloqueado por defecto en producción salvo habilitación explícita
- [x] Regresión de endurecimiento final OK (`4 tests`, `0 failures`) en `core.tests.test_tenant_strict_mode` y `core.tests.test_buscar_o_crear_paciente_confirmation`
- [x] `PRIS IA` desbloqueado del stub y flujo real activo
- [x] `Academia` cubierta con pruebas y blindaje tenant
- [x] Integración Google Drive unificada a Service Account centralizada (`GOOGLE_APPLICATION_CREDENTIALS` / `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`) con scope único `https://www.googleapis.com/auth/drive`
- [x] Migración de código preparada para OAuth 2.0 de usuario (`GOOGLE_DRIVE_TOKEN_PATH` + `GOOGLE_DRIVE_CREDENTIALS_PATH`) con refresco automático de token y compatibilidad transitoria con Service Account
- [~] Verificación real contra VPS ejecutada: la cuenta de servicio carga, pero el `GOOGLE_DRIVE_FOLDER_ID` actual en producción responde `404 notFound`; falta corregir el ID real de carpeta o compartir exactamente esa carpeta con la cuenta de servicio
- [x] Diagnóstico final Drive completado: lectura de carpeta productiva OK, escritura bloqueada por `403 storageQuotaExceeded` al usar Service Account sobre `My Drive`
- [x] Producción blindada para seguir operando con `BufferLocalStorage` por defecto mientras se migra a `Shared Drive` o se cambia el modelo de autenticación
- [x] Validado el `2026-06-19` que el JSON entregado localmente corresponde a `811785477499-compute@developer.gserviceaccount.com`; la identidad debe coincidir exactamente con el share activo de la carpeta o del `Shared Drive`
- [~] Producción funcional localmente validada; falta seguir la verificación manual módulo por módulo en el entorno real
- [x] Endurecimiento de seguridad complementario aplicado el `2026-06-19` en cron, audio médico/laboratorio y storage Drive
- [x] Drive ya no publica archivos con permiso `anyone-with-link` al guardar desde `GoogleDriveStorage`
- [x] `GoogleDriveStorage` preparado para `Shared Drive` con `supportsAllDrives/includeItemsFromAllDrives`
- [x] Endpoints `cron/*` ahora exigen `CRON_SECRET` en producción; fallback por headers solo queda permitido en `DEBUG=True`
- [x] Endpoints de audio médico/laboratorio ya no usan `csrf_exempt`, validan rol autorizado y requieren usuario con empresa asignada
- [x] Bug real corregido en audio laboratorio: ya no consulta `Parametro.keywords` inexistente; usa `abreviatura` como contexto derivado
- [x] Smoke verification directa `2026-06-19` OK: `403` para rol no autorizado en audio consulta, `403` para usuario sin empresa, `400` para analito de otra empresa y `403/200` correctos en cron sin/con secreto
- [x] Hallazgo de producción documentado: pruebas manuales fuera de `systemd` podían caer en `sqlite` local en vez de PostgreSQL por carga insegura de `.env`
- [x] Wrapper seguro agregado: `scripts/run_manage_with_env.py`
- [x] Scripts de despliegue/fixes actualizados para no usar `source .env`
- [~] Sincronización final de usuarios de auditoría pendiente de ejecutarse en PostgreSQL real con `sync_usuarios_auditoria`
- [x] Nuevo comando de carga masiva operativa agregado: `simular_operacion_anual`
- [x] Nuevo importador de catálogo médico agregado: `importar_medicos_xlsx`
- [x] Cierre de hallazgos críticos de auditoría 2026-06-19:
  - [x] `test_final_verification.py`, `test_laboratorio_full_e2e.py`, `test_farmacia_pdv_e2e.py`, `test_farmacia_full_user_flow.py` sin contraseñas hardcodeadas; usan `PRISLAB_TEST_PASSWORD` y validan existencia en runtime.
  - [x] URL de verificación QR/PDF corregida a `/validar/resultado/<uuid:token>/` usando `orden.token_acceso`.
  - [x] `import os` agregado en `core/views/laboratorio.py` para la ruta alterna de PDF.
  - [x] Filtro de worklist por departamento ampliado para incluir analitos dentro de `PerfilLims` y `PaqueteLims`.
  - [x] Endpoint público de validación de resultados confirmado y protegido con UUID token.
  - [x] Creación de órdenes de laboratorio normalizada a `estado='PENDIENTE_PAGO'`.
  - [x] Kiosko público ya no muta estado operativo a `EN_PROCESO`; solo registra check-in en sesión.
  - [x] Impresión de etiquetas de farmacia elimina respuesta de éxito ficticio; retorna `501` si no se puede generar el PDF real.
  - [x] URL de búsqueda de venta en pantalla de devoluciones corregida a `/farmacia/devoluciones/buscar/?busqueda=` para coincidir con la ruta real del backend.
  - [x] API de búsqueda de venta (`buscar_venta_devolucion`) acepta `busqueda` y `folio`, y devuelve `cliente`, `cajero_original` y `detalles` según contrato del frontend.
  - [x] API de devoluciones de farmacia sincronizada con nombres de campos del frontend (`tipo_devolucion`, `monto_reembolsado`, `motivo_error`, `accion_stock`).
  - [x] Servicio de devoluciones usa `accion_stock` enviado desde el frontend y aplica `REINGRESAR` o `MERMA`.
  - [x] Backend de devoluciones ahora acepta y persiste el array `productos` en `observaciones` de `SalesReturn` para auditoría granular (valida que los `detalle_id` pertenezcan a la venta).
  - [x] Agenda de consultorio filtrada por el médico asociado al usuario; solo superusuarios ven agenda general.
  - [x] Formulario `agendar_cita.html` ya no exige médico cuando el catálogo está vacío; indica que se creará automáticamente y el backend lo crea vinculado al usuario.
  - [x] Campo de búsqueda de paciente en `agendar_cita` ahora tiene `name="paciente_nombre"` y la vista conserva el nombre visible al re-renderizar con errores de validación.
  - [x] Rol `RECEPCION` redirige a `consultorio:tablero_recepcion` (agenda de citas) en lugar de `recepcion_lab`.
  - [x] Catálogo médico corregido a unicidad por empresa (`empresa`, `cedula_profesional`) en lugar de global; migración `0077` generada.
  - [x] API de guardado de reporte en storage (`api_generar_y_guardar_reporte`) ya no retorna `success` cuando `guardar_reporte_en_storage` devuelve `None`; devuelve error `STORAGE_ERROR` con `503`.
  - [x] Endpoints Sentinel restringidos a `POST` y token en header/body; fallback por `SECRET_KEY` eliminado.
  - [x] Verificación WebAuthn bloqueada: no se acepta autenticación simulada.
  - [x] `resetear_password` ya no eleva a `is_staff`/`is_superuser` al resetear.
  - [x] `provision_usuarios_base` requiere variables de entorno `PRISLAB_INIT_PASSWORD*` en lugar de contraseñas por defecto.
  - [x] `README.md` sin credenciales reales; instrucciones apuntan a variables de entorno.
  - [x] `api_test_github_sentinel` ya no expone token GitHub parcial.
  - [x] `manage.py check` OK y `makemigrations --check --dry-run` OK tras cambios.
  - [x] Regresión focalizada: `core.tests.test_pris_tools_operativos_security` OK (2 tests).
  - [x] Regresión completa de `core.tests`: OK (128 tests, 2 skipped) incluyendo cobertura, devoluciones, seguridad/tenant, rate limit, auditoría, entrega de resultados y más.
  - [x] Regresión de cobertura: `core.tests.test_coverage_boost` OK (19 tests).
  - [x] Regresión de devoluciones: `core.tests.test_devoluciones_farmacia_api` OK (3 tests).
  - [x] Regresión de seguridad/tenant: `core.tests.test_rate_limit_middleware`, `test_tenant_strict_mode`, `test_buscar_o_crear_paciente_confirmation` OK (6 tests).
  - [x] Regresión de consultorio: `consultorio.tests` OK (26 tests, 4 skipped) tras ajustar test frágil a mensaje actual del endpoint de audio laboratorio.
  - [x] Smoke funcional adicional `2026-06-19`: `tool_buscar_o_crear_paciente` exige confirmación antes de crear y crea correctamente al confirmar.
  - [x] Smoke funcional adicional `2026-06-19`: `/farmacia/devoluciones/buscar/` y `/farmacia/devoluciones/procesar/` responden `200` en HTTPS y persisten auditoría granular en `SalesReturn.observaciones`.
  - [x] Smoke funcional adicional `2026-06-19`: `/consultorio/api/procesar-audio-consulta/` rechaza rol `RECEPCION` con `403`.
  - [x] Hallazgo real corregido `2026-06-19`: `/laboratorio/api/crear-orden/` ya no rompe por `ImportError` ni por contrato viejo; crea orden `PENDIENTE_PAGO` usando `DetalleOrden` core con snapshot textual del estudio legacy.
  - [x] Hallazgo real corregido `2026-06-19`: `/laboratorio/api/medicos/` ya soporta filtro por `q`/`term` además de la carga completa del catálogo activo.
  - [x] Hallazgo real corregido `2026-06-19`: `/laboratorio/api/orden/<id>/datos/` ya serializa correctamente líneas legacy creadas como snapshot textual en `descripcion_linea`; antes devolvía `estudios: []`.
  - [x] Hallazgo real corregido `2026-06-19`: `/laboratorio/api/orden/<id>/editar-estudios/` ya acepta conservar líneas `legacy:*` sin exigir que todo el payload sea catálogo LIMS resoluble.
  - [x] Hallazgo real corregido `2026-06-19`: el PDV de farmacia ya no queda inconsistente entre `Producto.stock` y lotes; si existe stock heredado sin lotes, el backend materializa un lote operativo automático antes de vender o devolver detalle FEFO al frontend.
  - [x] Hallazgo real corregido `2026-06-19`: la venta PDV ahora asigna sucursal operativa mínima (`Matriz Principal`) cuando la empresa aún no tiene una configurada, permitiendo crear `MovimientoCaja` y evitar omisiones silenciosas.
  - [x] Hallazgo real corregido `2026-06-19`: se evitó el doble descuento de inventario marcando `inventario_descontado=True` en ventas ya descontadas por Kardex desde `VentaFarmaciaService`.
  - [x] Smoke funcional adicional `2026-06-19`: venta PDV directa OK con producto no antibiótico, baja exacta de `1` unidad, lote `AUTO-*`, sucursal asignada y `MovimientoCaja` creado.
  - [x] Utilidad operativa nueva `2026-06-19`: `python manage.py backfill_lotes_operativos_farmacia --empresa-id 1` deja vendible el inventario legado cargado solo en `Producto.stock`.
  - [x] Smoke funcional adicional `2026-06-19`: alta rápida de paciente OK (`/api/pacientes/guardar/`) y búsqueda incremental OK (`/api/pacientes/buscar/`).
  - [x] Smoke funcional adicional `2026-06-19`: flujo laboratorio end-to-end local OK con paciente nuevo + orden nueva + lectura de orden + cobro + visualización en `ordenes-recientes`.
  - [x] Smoke funcional adicional `2026-06-20`: consultorio rápido OK (`/consultorio/api/crear-paciente-y-consulta/`, `/consultorio/api/buscar-pacientes/`, `/consultorio/api/crear-consulta-directa/`, `/consultorio/api/generar-receta-inmediata/`).
  - [x] Hallazgo real corregido `2026-06-20`: los endpoints rápidos de consultorio ahora crean también la `ConsultaMedica` base; antes solo creaban `CitaMedica` y dejaban sin respaldo clínico ni destino de transcripción.
  - [x] Hallazgo real corregido `2026-06-20`: `/consultorio/api/analizar-transcripcion/` ya puede dejar `transcripcion_guardada=true` en consultas creadas por el flujo rápido.
  - [x] Hallazgo real corregido `2026-06-20`: `/medico/receta/<id>/pdf/` ya no rompe por campos inexistentes (`medico_universidad`) y vuelve a emitir PDF válido.
  - [x] Smoke funcional adicional `2026-06-20`: `/consultorio/pdf/receta/<consulta_id>/` responde PDF correcto y `/medico/receta/<id>/pdf/` responde `200 application/pdf`.
  - [x] Smoke funcional adicional `2026-06-20`: `/farmacia/ticket/<venta_id>/raw/` y `/laboratorio/ticket/<orden_id>/` responden `200`.
  - [~] Comportamiento esperado confirmado `2026-06-20`: `/laboratorio/resultados/<orden_id>/pdf/` redirige a captura cuando la orden aún no está validada clínicamente o falta la triple llave documental.
  - [~] Hallazgo transversal en auditoría `2026-06-19`: endpoints simples (`/api/pacientes/buscar/`, `/laboratorio/api/orden/<id>/datos/`, `/laboratorio/api/orden/<id>/editar-estudios/`) siguen marcando latencias de ~4-6s con bajo query count; investigar causa real fuera de lógica SQL.
  - [x] Perfilado de performance `2026-06-20`: la vista `api_buscar_pacientes` sola tarda ~`3.75 ms`, pero la request completa tardaba ~`4569 ms`; el cuello quedó confirmado en la capa transversal y no en la lógica del módulo.
  - [x] Hallazgo real corregido `2026-06-20`: `consultorio/api_views.py` ya no importa `core.services.ai_medico` en module import. El import de Gemini/audio pasó a nivel función (`procesar_audio_consulta`, `procesar_audio_laboratorio`).
  - [x] Mejora medida `2026-06-20`: primer request perfilado a `/api/pacientes/buscar/` bajó de ~`6.97 s` perfilados a ~`3.31 s` tras diferir el import pesado de `google.genai`.
  - [~] Hallazgo de performance aún abierto `2026-06-20`: persiste costo de cold-start/import tree en resolución inicial de rutas (`config/urls.py`, `consultorio/urls.py` y otros imports globales). No es SQL ni lógica de pacientes; requiere segunda pasada de lazy-loading estructural si queremos bajar más el arranque en frío.

## Documento de cierre de auditoría

- **Resumen escrito de todos los fixes de esta sesión:** `docs/CIERRE_AUDITORIA_2026-06-19.md`
- **Revisión asignada a:** Codex / Claude

## Estado general

- [x] Bloque 0 - Base de control
- [~] Bloque 1 - Catálogo LIMS base
- [~] Bloque 2 - Valores de referencia y resultados
- [~] Bloque 3 - Recepción y órdenes
- [ ] Bloque 4 - Pacientes
- [ ] Bloque 5 - Clientes
- [~] Bloque 6 - Médicos
- [~] Bloque 7 - Cotización
- [~] Bloque 8 - Cobranza
- [~] Bloque 9 - Auditoría
- [x] Bloque 10 - Seguridad y permisos
- [ ] Bloque 11 - Programa de lealtad
- [ ] Bloque 12 - Microbiología
- [~] Bloque 13 - Reportes
- [~] Bloque 14 - Integraciones externas
- [ ] Bloque 15 - Validación final de reemplazo

Leyenda:
- `[x]` cerrado
- `[~]` parcialmente cerrado
- `[ ]` pendiente

## Bloque 0 - Base de control

- [x] Matriz de migración creada
- [x] Anexo técnico creado
- [x] Plan de cierre por prioridades creado
- [x] Plan de cierre por bloques creado

## Bloque 1 - Catálogo LIMS base

- [x] `Analito` definido
- [x] `ValorReferenciaAnalito` definido
- [x] `PerfilLims` definido
- [x] `PaqueteLims` definido
- [x] `PrecioItem` definido
- [x] `ensamblar_lims_v75` definido
- [~] Catálogo final 1:1 contra legado
- [~] Cardinalidad exacta validada
- [~] Nombres exactos validados

## Bloque 2 - Valores de referencia y resultados

- [x] Captura y PDF ya muestran referencias
- [x] Soporte de rangos numéricos y textuales
- [x] Compatibilidad con captura vieja y nueva
- [~] Validación final por sexo / edad
- [~] Casos pediátricos revisados con evidencia final
- [~] Impresión igual al legacy al 100%

## Bloque 3 - Recepción y órdenes

- [x] Selección de estudios robustecida
- [x] Backend acepta `estudios` y `estudio_ids`
- [x] Validación de orden vacía endurecida
- [~] Cobro completo validado en producción con todos los casos
- [~] Matching exacto de formulario vs sistema legado
- [~] Flujo de edición en vivo completamente cerrado

## Bloque 4 - Pacientes

- [ ] Campos de ficha comparados uno a uno
- [ ] Campos extra configurables revisados
- [ ] Expediente con pestañas equivalentes
- [ ] Validación de cambio de nombre comparada
- [ ] Geografía dinámica comparada

## Bloque 5 - Clientes

- [ ] Catálogo de clientes replicado
- [ ] Tarifa base validada
- [ ] Bloqueo / activación validado
- [ ] Sucursales permitidas validadas
- [ ] Estudios por cliente validados
- [ ] Facturación especial validada

## Bloque 6 - Médicos

- [~] Catálogo médico ya tiene ruta formal de importación desde Excel legacy (`importar_medicos_xlsx`)
- [ ] Médico que refiere validado
- [ ] Entrega de solicitudes físicas validada
- [ ] Comisión por médico validada
- [ ] Reportes por médico comparados

## Bloque 7 - Cotización

- [x] Consulta inválida corregida
- [~] Cálculo comercial comparado
- [~] PDF de cotización comparado
- [~] Conversión a orden comparada

## Bloque 8 - Cobranza

- [~] Pago mixto validado de forma funcional
- [~] Efectivo, tarjeta y transferencia soportados
- [~] Anticipo y cancelación revisados
- [~] Monedero y bonos comparados con legado

## Bloque 9 - Auditoría

- [~] Base de auditoría funcional
- [~] Eventos críticos registrados
- [ ] Exportaciones y filtros idénticos al legacy
- [ ] Cobertura completa de actividades comparada

## Bloque 10 - Seguridad y permisos

- [x] Arquitectura multitenant y roles ya existe
- [x] Read-only / modo de contingencia existe
- [~] Paridad exacta de permisos por rol
- [~] Mapa de permisos del legacy replicado

## Bloque 11 - Programa de lealtad

- [ ] Implementación base localizada en código productivo
- [ ] Monedero equivalente al legacy
- [ ] Reglas de acumulación equivalentes
- [ ] Excepciones de clientes equivalentes
- [ ] Reportes equivalentes

## Bloque 12 - Microbiología

- [~] Módulo blindado para no romper imports ni requests aunque los modelos productivos aún no existen
- [ ] Catálogo de bacterias validado
- [ ] Catálogo de antibióticos validado
- [ ] Grupos de antibiograma validados
- [ ] Despliegue automático por prueba validado

## Bloque 13 - Reportes

- [~] Resultados y laboratorio ya soportan parte del flujo
- [ ] Corte por sucursal replicado
- [ ] Ventas por cliente replicado
- [ ] Caja replicada
- [ ] Cobranza pendiente replicada
- [ ] Exámenes realizados replicado
- [ ] Tiempos de proceso replicado
- [ ] Inventario / matriz replicados

## Bloque 14 - Integraciones externas

- [~] TuLab soportado parcialmente
- [~] CFDI / facturación soportado parcialmente
- [~] Interfaces de analizadores soportadas parcialmente
- [x] Google Drive centralizado por Service Account
- [x] Manejo explícito de errores `403` / `404` en capa Drive
- [~] Carpeta maestra de Google Drive validada en producción
- [~] Lectura real de carpeta maestra confirmada en producción
- [ ] Subida real de archivo a carpeta maestra confirmada en producción
- [x] Fallback seguro a buffer local desplegado en producción mientras se resuelve `Shared Drive`
- [x] Documento operativo de cierre Drive agregado: `docs/DRIVE_CIERRE_OPERATIVO_2026-06-19.md`
- [ ] WhatsApp validado como en legacy
- [ ] DICOM PACs validado
- [ ] EvaPacs validado
- [ ] S3 / adjuntos comparados

## Bloque 15 - Validación final

- [ ] P0 completo
- [ ] P1 mayormente completo
- [ ] Operación diaria sin parches
- [ ] Validación visual final aprobada
- [ ] Aceptación como reemplazo total

## Actualización 2026-06-20 - Auditoría Codex

- [x] Consultorio rápido validado: creación de paciente, cita, receta y PDF operativo
- [x] Fast flow de consultorio ahora garantiza `ConsultaMedica` además de `CitaMedica`
- [x] `api_analizar_transcripcion` ya persiste transcripción clínica sobre `ConsultaMedica`
- [x] Consultorio ahora resuelve catálogo LIMS con `empresa` explícita en generación de órdenes, evitando fugas cross-tenant por IDs coincidentes
- [x] PDF legacy `/medico/receta/<id>/pdf/` corregido y operativo
- [x] Ticket farmacia raw operativo
- [x] Ticket laboratorio operativo
- [~] `/laboratorio/resultados/<orden_id>/pdf/` redirige correctamente a captura cuando no se cumple el triple blindaje
- [x] `/laboratorio/api/crear-orden/` ya quedó alineado al servicio LIMS real; corregido el bug donde la UI sí mostraba estudios pero el backend legacy no los resolvía
- [x] PDV farmacia ahora bloquea backend si intentan vender con carrito vacío o cantidades inválidas
- [x] Devoluciones farmacia ahora normalizan `REINGRESAR -> RETORNO_ALMACEN`, previenen sobredevoluciones y reingresan stock por lote cuando corresponde
- [x] Devoluciones farmacia ya aceptan `productos_devueltos` (payload real del frontend) y rechazan devoluciones parciales sin partidas válidas
- [x] Corte de caja unificado ya calcula laboratorio por cobranzas reales (`PagoOrden`) y no por órdenes creadas no cobradas
- [x] Consultorio y timeline de paciente ya no enlazan a `/laboratorio/orden/<id>/` inexistente; ahora usan una ruta viva de laboratorio (`ticket` de orden)
- [x] Soporte S3-compatible listo para Vultr Object Storage con backend multi-tenant (`TenantS3Storage`) y prioridad sobre Drive cuando `VULTR_OBJECT_STORAGE_ENABLED=True`
- [x] Storage S3 ya no rompe el arranque del proyecto si `boto3` no está instalado y Vultr Object Storage no está habilitado
- [x] Seguridad 2FA: ya no se bypass-ea por ausencia de TOTP cuando el usuario tiene 2FA activo por otro canal; se centralizó verificación y se habilitó el `PRISLAB_MASTER_RECOVERY_CODE`
- [x] `consultorio/api_views.py` ya no importa IA médica pesada en top-level
- [x] `config/urls.py` ahora difiere módulos pesados (`PRIS IA`, `voice`, `push`, `chat`, `notificaciones`, `nomina`, `crm`) para bajar costo del primer request
- [x] Microbiología ya no cae por `NameError`/`ModuleNotFoundError`; el módulo responde `503` controlado mientras siga pendiente la implementación real de modelos
- [x] Nueva regresión dirigida: `core.tests.test_microbiologia_views` valida respuesta controlada sin modelos y guardado JSON cuando el resolver está disponible
- [x] Regresión del módulo `seguridad` validada tras ajuste 2FA (`5 tests OK`)
- [x] `manage.py check` volvió a pasar localmente tras blindaje de microbiología y arranque opcional S3
- [x] Regresión contable/CFDI revalidada `2026-06-20`: `contabilidad.tests.test_validators_cfdi40` (`12 OK`), `contabilidad.tests.test_cfdi_borrador_auto` + `core.tests.test_e2e_cfdi` (`7 OK`, `1 skipped`)
- [~] Hallazgo funcional confirmado en auditoría: `core/views/contabilidad.py` sigue siendo un frente provisional con redirecciones/placeholders; el flujo serio de CFDI vive en `contabilidad/`
- [~] Hallazgo funcional confirmado en auditoría: `core/views/reportes_financieros.py` opera, pero `balance_general` y parte del bloque contable aún usan proxies porque faltan modelos contables migrados
- [x] Regresión de resultados/PDF/storage revalidada `2026-06-20`: `core.tests.test_lab_validation_pdf`, `core.tests.test_motor_reporte_pdf_candado`, `core.tests.test_entrega_resultados_bitacora`, `core.tests.test_storage_backends_security` (`10 OK`)
- [x] Endurecimiento de entrega pública revalidado `2026-06-20`: `core.tests.test_entrega_resultados_bitacora` ampliado a `8 OK`
- [x] Hallazgo real corregido `2026-06-20`: `api_marcar_whatsapp_enviado` ya no permite marcar auditoría falsa cuando la orden no está validada, tiene saldo pendiente, falta consentimiento digital o no existe teléfono del paciente
- [x] Cobertura pública ampliada `2026-06-20`: el portal público de resultados ya tiene regresión para `token` inválido y para orden no validada
- [x] Hallazgo real corregido `2026-06-20`: `reporte_ingresos_egresos` y `exportar_excel_ingresos_egresos` ya incluyen `GastoOperativo` en el detalle diario; antes el resumen mostraba egresos completos pero la gráfica/Excel diario omitían gastos operativos
- [x] Hallazgo real corregido `2026-06-20`: `genera_reporte_caja` ya excluye ventas canceladas y pagos de ventas canceladas; antes podía inflar caja con operaciones no válidas
- [x] Optimización aplicada `2026-06-20`: los reportes diarios (`reporte_ingresos_egresos`, `reporte_flujo_caja` y sus exportaciones Excel) dejaron de hacer loops N+1 por día y ahora usan agregaciones por fecha
- [x] Nueva regresión agregada `2026-06-20`: `core.tests.test_reportes_financieros_regression` (`2 OK`) cubre egresos diarios completos y exclusión de ventas canceladas en reporte de caja
- [x] Hallazgo real corregido `2026-06-20`: `consultorio/api_subir_archivo` ya rechaza cruces paciente-consulta; antes permitía intentar adjuntar un archivo a una consulta de otro paciente
- [x] Hallazgo real corregido `2026-06-20`: `consultorio/api_liquidar_vale` ya rechaza montos `<= 0`; antes un `0` podía liquidar por completo el vale por caer en la rama de cierre total
- [x] Hallazgo real corregido `2026-06-20`: el módulo médico dejó de resolver documentos/consultas con `Medico.objects.filter(...).first()`; ahora usa resolución por usuario actual y autocreación controlada (`USR-<user.id>`) para no firmar certificados, recetas u órdenes con el médico equivocado
- [x] Nueva regresión agregada `2026-06-20`: `consultorio.tests.ConsultorioBillingAndFilesRegressionTests` amplió cobertura sobre liquidación inválida, adjuntos cruzados y resolución correcta del médico operativo en flujos inmediatos
- [x] Hallazgo real corregido `2026-06-20`: `core.ConsultaMedica.save()` ahora autogenera `folio_consulta` antes de `full_clean()`; antes el flujo `/consultorio/medico/consulta/nueva/<uuid>/` fallaba al guardar con `{'folio_consulta': ['Este campo no puede estar en blanco.']}`
- [x] Nueva regresión agregada `2026-06-20`: `consultorio.tests.ConsultorioViewTests.test_nueva_consulta_con_paciente_guarda_consulta_finalizada_con_folio` valida el guardado completo de la consulta médica con folio automático
- [x] Auditoría local desbloqueada `2026-06-20`: `config/settings.py` ahora soporta `PRISLAB_DISABLE_FILE_LOG_HANDLERS=1` para correr `check` y tests sin depender de handlers de archivo bloqueados en Windows/local
- [x] Verificación revalidada `2026-06-20`: `python manage.py check` -> `System check identified no issues (0 silenced)`
- [x] Regresión completa de consultorio revalidada `2026-06-20`: `python manage.py test consultorio.tests --keepdb` -> `OK (30 tests, 4 skipped)`
- [x] Auditoría funcional en producción `2026-06-20`: `consultorio/recepcion/agendar/` encontró paciente por búsqueda, mostró médico disponible y permitió agendar cita de prueba con éxito
- [~] Producción sigue pendiente de deploy para absorber el fix de `folio_consulta`; la corrección ya quedó validada en local con `python manage.py test consultorio.tests.ConsultorioViewTests.test_nueva_consulta_con_paciente_guarda_consulta_finalizada_con_folio -v 2` -> `OK`
- [~] Hallazgo funcional confirmado en auditoría: no se localizaron archivos productivos del bloque de lealtad/monedero, por lo que Bloque 11 sigue pendiente de implementación real
- [~] Riesgo arquitectónico confirmado en auditoría: `EmpresaIdentityMiddleware` todavía puede asignar una empresa por defecto a usuarios autenticados sin `user.empresa` mediante `resolve_default_empresa_sistema()`. En el escenario actual monotenant puede ser una tolerancia operativa útil, pero antes de abrir multiempresa real debe decidirse si ese fallback sigue permitido o si `PRISLAB_TENANT_STRICT_MODE` debe bloquear siempre a cualquier usuario autenticado sin FK de empresa.
- [~] Hallazgo de deuda técnica no bloqueante: `consultorio/api/procesar_audio.py` permanece como código legacy no cableado en rutas; el endpoint activo es `consultorio/api_views.py`
- [~] Perfilado local confirmó que el cuello de botella mayor era carga de imports del router; quedó reducido, pero falta validar en VPS la mejora exacta con Gunicorn/Nginx
- [~] Verificación local de `manage.py check` quedó bloqueada por permisos del handler `logs/prislab_audit.log`; el problema es del entorno local de logging, no de sintaxis del cambio
- [x] `manage.py check` revalidado `2026-06-20` después del cierre de auditoría estructural adicional

## Bloque agregado por Claude — 2026-06-20

- [x] Hallazgo crítico corregido: bypass de 2FA vía spoofing de `X-Forwarded-For`. `nginx/conf.d/prislab.conf` ahora fija `$remote_addr`; `_get_client_ip()` en `core/views/autenticacion_2fa.py` solo lee `REMOTE_ADDR`. Defensa en profundidad aplicada en 12 archivos adicionales que leían el header sin sanitizar (`core/middleware/admin_access.py`, `core/middleware/blindaje_expediente.py`, `core/middleware/seguridad.py`, `core/utils/trazabilidad.py`, `core/services/audit_service.py`, `core/utils/auditoria_nativa.py`, `core/views/consentimiento_digital.py`, `core/views/general.py`, `core/views/finanzas.py`, `core/views/pris_jarvis.py`, `mantenimiento/views.py`, `core/services/lims/interfaces_lims_service.py`, `core/decorators.py`).
- [x] Hallazgo corregido: sin rate limiting real en `verificar_2fa()`. Ahora bloquea tras 5 intentos fallidos con cache, 15 minutos de espera.
- [x] Hallazgo corregido: fuga de tenant en `core/views/medico.py:94` (búsqueda por cédula sin `empresa=`).
- [x] `CELERY_BEAT_SCHEDULE` activado en `config/settings.py` con tarea diaria 7am (`core/tasks/notificaciones_tasks.py`).
- [x] Módulo nuevo: Contabilidad Personal privada (solo Director/superuser) en `core/views/contabilidad_personal.py`, exige factura + foto evidencia para marcar pagada una `OrdenDeCompra`. Migración `inventario/migrations/0008_agregar_evidencia_pagos_orden_compra.py` generada y aplicada.
- [x] Confirmado por lectura de código: Panel de Configuración de Cumplimiento por Empresa (`core/services/feature_flags.py` + `/configuracion/flags/`) ya existía completo, construido previamente.
- [x] `GAP_ANALYSIS_ISO15189.md` agregado: auditoría línea por línea contra ISO 15189; Westgard QC confirmado construido y probado pero apagado por defecto (`QC_WESTGARD_ACTIVO=False`).
- [x] Segunda ronda de auditoría de tenant — 5 fugas adicionales corregidas: `core/views/medico.py:881` (QR de receta exponía datos de paciente/diagnóstico de cualquier empresa), `laboratorio/views/__init__.py:322` (alta de médico por cédula sin `empresa=`), `core/views/auditoria_campo.py:42` (forja de auditoría sobre `DetalleOrden` de otra empresa), `core/utils/lims_tokens_v75.py:426` (endpoint sin auth ni scope, código muerto, blindado preventivamente), `core/management/commands/importar_medicos_xlsx.py:60` (reasignación cruzada de médico por cédula).
- [x] `VULTR_OBJECT_STORAGE_SETUP.md` agregado: guía completa de activación (el código ya soporta `TenantS3Storage`, solo falta bucket + credenciales del dueño).
- [x] Alineación cruzada con Codex (`ALINEACION_CODEX_CLAUDE_2026-06-20.md`): confirmado que los 5 fixes de tenant y el fix de 2FA/Celery no chocan con el trabajo de Codex. Aceptado el hallazgo de Codex sobre `_solo_director()` en `contabilidad_personal.py` (permitía `ADMIN` además de `DIRECTOR`, contradiciendo el reporte original de Claude); fix de Codex verificado correcto.
- [x] Revalidado `2026-06-20`: `python manage.py test consultorio.tests.ConsultorioViewTests.test_nueva_consulta_con_paciente_guarda_consulta_finalizada_con_folio core.tests.test_contabilidad_personal --keepdb` -> `OK (4 tests)`, confirma que el fix de `folio_consulta` de Codex y el fix de `_solo_director` no entran en conflicto con los cambios de Claude.
- [~] Nada de lo anterior está commiteado todavía; el HEAD actual (`afc097e`) es de Codex. Pendiente decidir si se separa en varios commits (seguridad/tenant, contabilidad personal, docs) antes de mezclar autoría.
- [~] Pendiente sin resolver: confirmar `PRISLAB_MASTER_RECOVERY_CODE` real en `.env` de producción (requiere acceso SSH).

## Próximo orden de trabajo recomendado

1. Ejecutar revisión externa de Claude y Cascada usando como fuente inicial este checklist y el reporte maestro.
2. Ejecutar `simular_operacion_anual` e `importar_medicos_xlsx` para poblar datos reales de estrés antes de la siguiente ronda funcional.
3. Continuar pruebas funcionales reales en producción módulo por módulo.
4. Terminar Bloque 1 al 3 al nivel de paridad exacta contra el legacy.
5. Cerrar Bloques 4, 5 y 6.
6. Cerrar Bloque 13 porque impacta operación diaria.
7. Cerrar Bloques 11, 12 y 14.
8. Ejecutar Bloque 15 como auditoría final de reemplazo total.
