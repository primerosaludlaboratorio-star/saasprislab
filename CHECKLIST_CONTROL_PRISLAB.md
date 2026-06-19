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
- [~] Verificación real contra VPS ejecutada: la cuenta de servicio carga, pero el `GOOGLE_DRIVE_FOLDER_ID` actual en producción responde `404 notFound`; falta corregir el ID real de carpeta o compartir exactamente esa carpeta con la cuenta de servicio
- [x] Diagnóstico final Drive completado: lectura de carpeta productiva OK, escritura bloqueada por `403 storageQuotaExceeded` al usar Service Account sobre `My Drive`
- [x] Producción blindada para seguir operando con `BufferLocalStorage` por defecto mientras se migra a `Shared Drive` o se cambia el modelo de autenticación
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

- [ ] Monedero equivalente al legacy
- [ ] Reglas de acumulación equivalentes
- [ ] Excepciones de clientes equivalentes
- [ ] Reportes equivalentes

## Bloque 12 - Microbiología

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

## Próximo orden de trabajo recomendado

1. Ejecutar revisión externa de Claude y Cascada usando como fuente inicial este checklist y el reporte maestro.
2. Ejecutar `simular_operacion_anual` e `importar_medicos_xlsx` para poblar datos reales de estrés antes de la siguiente ronda funcional.
3. Continuar pruebas funcionales reales en producción módulo por módulo.
4. Terminar Bloque 1 al 3 al nivel de paridad exacta contra el legacy.
5. Cerrar Bloques 4, 5 y 6.
6. Cerrar Bloque 13 porque impacta operación diaria.
7. Cerrar Bloques 11, 12 y 14.
8. Ejecutar Bloque 15 como auditoría final de reemplazo total.
