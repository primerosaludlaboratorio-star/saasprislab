# REPORTE MAESTRO FINAL PARA CLAUDE Y CASCADA

Fecha de consolidacion: 2026-06-18  
Estado de corte: listo para revision externa tecnica y funcional  
Responsable de este corte: Codex

## Actualizacion critica 2026-06-19 - Diagnostico real del login en produccion

Hallazgo confirmado:

- las verificaciones iniciales de usuarios en VPS se ejecutaron con `manage.py shell` fuera del entorno real cargado por `systemd`
- en ese contexto, Django cayó a la base local `sqlite` del servidor en lugar de PostgreSQL productivo
- por eso las cuentas parecían autenticar en consola pero seguían fallando en `https://prislab.labcorecloud.com/login/`
- el login web no estaba contradiciendo a Django: estaban usando dos bases distintas

Causa raíz:

- el archivo `/opt/prislab/app/.env` es válido para `EnvironmentFile=` de `systemd`
- pero no es seguro usar `source .env` en bash porque `SECRET_KEY` contiene caracteres especiales sin quoting shell
- eso vuelve frágiles o engañosas las pruebas manuales en producción

Corrección estructural aplicada en el repo:

- nuevo wrapper seguro: [scripts/run_manage_with_env.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\scripts\run_manage_with_env.py)
- nuevo comando de sincronización: [core/management/commands/sync_usuarios_auditoria.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\management\commands\sync_usuarios_auditoria.py)
- `scripts/aplicar_fixes_produccion.sh` ya no usa `source .env`
- `scripts/deploy_vps.sh` ya no usa `source .env`

Regla nueva obligatoria para producción:

- no usar `python manage.py ...` directo para operaciones manuales críticas en VPS si dependen del `.env`
- usar siempre `python scripts/run_manage_with_env.py ...`
- si no se sigue esta regla, existe riesgo real de tocar la base equivocada y validar datos falsos

## 1. Regla operativa obligatoria

Toda persona, agente o IA que haga cualquiera de estas acciones:

- cambio de codigo
- cambio de infraestructura
- cambio de variables de entorno
- despliegue
- prueba funcional
- correccion de bug
- carga de catalogos
- validacion de produccion

debe actualizar en el mismo movimiento:

1. [CHECKLIST_CONTROL_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\CHECKLIST_CONTROL_PRISLAB.md)
2. [REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md)

Si no se actualizan esos dos documentos, el trabajo se considera incompleto aunque el codigo funcione.

## 2. Documentos fuente de verdad

Documentos que Claude y Cascada deben revisar primero, en este orden:

1. [REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md)
2. [CHECKLIST_CONTROL_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\CHECKLIST_CONTROL_PRISLAB.md)
3. [PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md)
4. [DEPLOY.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\DEPLOY.md)
5. [README.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\README.md)
6. [env_produccion.txt](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\env_produccion.txt)
7. [nginx/conf.d/prislab.conf](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\nginx\conf.d\prislab.conf)
8. [verify_deployment.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\verify_deployment.sh)
9. [scripts/deploy_vps.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\scripts\deploy_vps.sh)
10. [scripts/aplicar_fixes_produccion.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\scripts\aplicar_fixes_produccion.sh)
11. [test_integracion_real.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\test_integracion_real.py)

Documentos de contexto adicional recomendados:

- [PLAN_CIERRE_MIGRACION_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\PLAN_CIERRE_MIGRACION_PRISLAB.md)
- [PLAN_BLOQUE_POR_BLOQUE_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\PLAN_BLOQUE_POR_BLOQUE_PRISLAB.md)
- [ANEXO_TECNICO_PRISLAB_LEGACY_VS_SAAS.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\ANEXO_TECNICO_PRISLAB_LEGACY_VS_SAAS.md)

## 3. Estado ejecutivo real

PRISLAB SaaS ya esta en un punto tecnicamente serio para auditoria externa.

Estado actual confirmado en local:

- `manage.py check` sin errores
- `makemigrations --check --dry-run` sin cambios pendientes
- suite global `manage.py test` completada con `251 tests OK` y `23 skipped`
- modulo `academia` ya cubierto con pruebas
- `PRIS IA` ya no esta bloqueado por el stub muerto
- proveedor de IA ya tiene fallback seguro entre Gemini y DeepSeek
- smoke script de integracion ya no rompe descubrimiento de pruebas
- se agrego `core/management/commands/simular_operacion_anual.py` para poblar pacientes, ordenes LIMS y ventas/devoluciones reales de farmacia con carga masiva controlada
- se agrego `core/management/commands/importar_medicos_xlsx.py` para importar el catalogo medico desde el Excel original del laboratorio

Conclusiones:

- el codigo esta estable para revision
- el proyecto no esta "terminado funcionalmente al 100%" respecto al reemplazo total del legacy
- pero ya esta lo bastante solido para que Claude y Cascada revisen con rigor y ayuden a cerrar la ultima milla

## 4. Cambios tecnicos mas importantes consolidados

### 4.1 IA y PRIS

Archivo principal:

- [core/views/pris_ia.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\views\pris_ia.py)

Estado:

- se elimino el bloqueo por retorno temprano del stub
- el flujo real con Gemini, function calling, herramientas, confirmaciones y `AccionPRIS` ya esta activo
- `deepseek` queda como ruta legacy opcional, no como secuestro accidental del flujo principal

### 4.2 Cliente IA unificado

Archivo principal:

- [core/utils/gemini_client.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\utils\gemini_client.py)

Estado:

- `GOOGLE_API_KEY` se mantiene como clave canonica
- aliases `GOOGLE_GEMINI_API_KEY` y `GEMINI_API_KEY` siguen soportados
- si `AI_PROVIDER=deepseek` pero no hay `DEEPSEEK_API_KEY` y si hay Gemini, hace fallback seguro a Gemini
- si `AI_PROVIDER=gemini` pero no hay `GOOGLE_API_KEY` y si hay DeepSeek, hace fallback seguro a DeepSeek
- errores 403 de Gemini ya generan mensajes utiles

### 4.3 Drive y credenciales

Archivos principales:

- [config/drive_credentials.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\config\drive_credentials.py)
- [core/utils/google_drive.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\utils\google_drive.py)
- [config/storage_backends.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\config\storage_backends.py)

Estado:

- Drive usa cuenta de servicio, no API key
- desde `2026-06-19` el código ya soporta también OAuth 2.0 de usuario vía `GOOGLE_DRIVE_TOKEN_PATH` y `GOOGLE_DRIVE_CREDENTIALS_PATH`, priorizándolo sobre Service Account para cuentas personales Gmail
- sin credenciales, el sistema cae a fallback local sin tumbar el arranque
- errores 403 y 404 de Drive ya devuelven mensajes utiles
- `config/drive_credentials.py`, `core/utils/google_drive.py` y `core/utils/drive_archive.py` quedaron alineados a una sola fuente de credenciales centralizada
- el scope activo quedó unificado a `https://www.googleapis.com/auth/drive`
- en la VPS ya se instaló el archivo de credenciales en la ruta configurada por `GOOGLE_APPLICATION_CREDENTIALS`
- se ejecutó una primera prueba real en producción con la cuenta de servicio: la credencial carga correctamente, pero el `GOOGLE_DRIVE_FOLDER_ID` respondió `404 notFound` hasta alinear la cuenta de servicio correcta
- tras compartir la carpeta con la cuenta correcta, la lectura de `PRISLAB_Media` quedó operativa
- la subida real sigue bloqueada por Google con `403 storageQuotaExceeded` porque la carpeta vive en `My Drive` y no en `Shared Drive`
- conclusion operativa actual: el código y la credencial ya están bien; el bloqueo restante es arquitectónico de Google Drive y se resuelve migrando a `Shared Drive` o usando autenticación de usuario

## 4.3.1 Estado real Google Drive en produccion al 2026-06-19

Verificacion ejecutada por Codex en VPS:

- lectura de `.env` de produccion OK
- deteccion de `GOOGLE_APPLICATION_CREDENTIALS` OK
- deteccion de `GOOGLE_DRIVE_FOLDER_ID` OK
- carga de Service Account OK
- validacion local adicional `2026-06-19`: el JSON entregado corresponde a `811785477499-compute@developer.gserviceaccount.com`
- conclusion de esa validacion: no basta con \"tener un JSON\"; la identidad del Service Account debe coincidir exactamente con la carpeta o `Shared Drive` compartido
- intento inicial de lectura de carpeta maestra Drive FAIL con `404 notFound`
- causa detectada: la carpeta estaba compartida con otra Service Account distinta a la instalada en VPS
- tras corregir el share, lectura de carpeta maestra Drive OK
- intento de subida real FAIL con `403 storageQuotaExceeded`

Interpretacion correcta:

- si Google devuelve `404` para `files().get(fileId=...)`, normalmente significa que el recurso no está visible para la cuenta de servicio concreta que usa PRISLAB
- si Google devuelve `403 storageQuotaExceeded` al crear archivos con Service Account en una carpeta de `My Drive`, el remedio correcto es usar `Shared Drive` o autenticación delegada de usuario

Pendiente exacto para cerrar:

- crear o migrar `PRISLAB_Media` a `Shared Drive`
- compartir esa unidad/carpeta con `vertex-express@prislab-v5-ai.iam.gserviceaccount.com`
- mantener mientras tanto el backend por defecto en `BufferLocalStorage` para no romper cargas productivas

## 4.3.2 Endurecimiento adicional aplicado el 2026-06-19

Archivos principales:

- [config/storage_backends.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\config\storage_backends.py)
- [core/views/cron_tasks.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\views\cron_tasks.py)
- [consultorio/api_views.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\consultorio\api_views.py)
- [core/tests/test_storage_backends_security.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\tests\test_storage_backends_security.py)
- [core/tests/test_cron_tasks_security.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\tests\test_cron_tasks_security.py)
- [consultorio/tests.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\consultorio\tests.py)

Cambios ejecutados:

- se eliminó la creación automática de permisos públicos `anyone/reader` al guardar archivos en Google Drive
- se añadió compatibilidad explícita con `Shared Drive` usando `supportsAllDrives=True` e `includeItemsFromAllDrives=True` en búsquedas, lecturas, borrados y creación de carpetas/archivos
- los endpoints `cron/*` ya no aceptan headers spoofeables en producción cuando `CRON_SECRET` no está configurado; en ese caso responden `403`
- el fallback por headers tipo scheduler quedó permitido solo en entornos `DEBUG=True`
- los endpoints de audio de consultorio y laboratorio dejaron de usar `csrf_exempt`
- esos endpoints ahora validan rol autorizado y rechazan usuarios sin empresa asignada
- el flujo de laboratorio ahora filtra `Analito` por `empresa` del usuario para evitar consulta cruzada por tenant
- se corrigió un bug real oculto: el endpoint de audio de laboratorio intentaba leer `Parametro.keywords`, campo inexistente; ahora deriva `keywords` desde `abreviatura`

Evidencia de verificación:

- test focal de storage ejecutado OK: `core.tests.test_storage_backends_security` (`2 tests`, `0 failures`)
- smoke verification directa contra Django local ejecutada OK con estos resultados:
  - audio consulta con rol no autorizado -> `403`
  - audio consulta con usuario sin empresa -> `403`
  - audio laboratorio contra analito de otra empresa -> `400`
  - cron en producción sin `CRON_SECRET` -> `403`
  - cron con `X-Cron-Secret` válido -> `200`

Nota operacional importante:

- el harness completo de pruebas en Windows sigue teniendo fricción por salida `cp1252` y `flush` durante migraciones de prueba cuando se usa cierto wrapper; no bloquea el cambio aplicado, pero sí conviene que Claude o Cascada vuelvan a correr estas clases en un entorno Linux o directamente en la VPS durante la siguiente ronda de verificación
- una vez exista `Shared Drive`, reejecutar la prueba de subida/borrado real para cerrar el punto

### 4.4 Academia

Archivos principales:

- [academia/views.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\academia\views.py)
- [academia/tests.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\academia\tests.py)
- [academia/models.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\academia\models.py)

Estado:

- modulo integrado dentro del sistema
- acceso limitado por empresa
- se blindo el flujo para no otorgar accesos cross-tenant por error
- heartbeat y reproduccion tienen cobertura

### 4.5 Entornos y documentacion

Archivos principales:

- [.env.example](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\.env.example)
- [.env.production.example](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\.env.production.example)
- [env_produccion.txt](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\env_produccion.txt)

Estado:

- ya no se deja `deepseek` como default riesgoso
- ejemplos actualizados a estrategia de Gemini canonico + DeepSeek opcional
- archivo de guia local de produccion limpiado de valores sensibles incrustados

### 4.6 Endurecimiento posterior a auditoria externa

Archivos principales:

- [config/settings.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\config\settings.py)
- [docker-compose.yml](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\docker-compose.yml)
- [nginx/conf.d/prislab.conf](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\nginx\conf.d\prislab.conf)

Cambios aplicados:

- `LAB_VALIDATION_PIN` ya no usa `1234` como valor por defecto en código
- en producción ahora se exige que `LAB_VALIDATION_PIN` exista y tenga al menos 8 caracteres
- `docker-compose.yml` ya no deja contraseña Redis por defecto visible
- `docker-compose.yml` ya no deja `LAB_VALIDATION_PIN` por defecto
- `docker-compose.yml` ya no deja `deepseek` como proveedor IA por defecto; ahora el default es `gemini`
- Nginx ya alinea `X-Frame-Options` con Django usando `DENY`
- `RateLimitMiddleware` ya usa la última IP de `X-Forwarded-For`, cerrando el bypass por spoofing de la primera IP
- `tool_registrar_venta_farmacia` ya rechaza cantidades cero, negativas o inválidas antes de calcular total o descontar stock
- `PRISLAB_TENANT_STRICT_MODE` ya bloquea requests autenticados sin empresa antes de permitir consultas globales silenciosas
- `tool_buscar_o_crear_paciente` ya no fuerza creación automática; ahora exige confirmación humana antes de crear
- `OMNI_BYPASS_TOKEN` queda bloqueado por defecto en producción salvo habilitación explícita y deja huella en logs cuando se usa o se bloquea

### 4.7 Ajustes funcionales reales cerrados el 2026-06-19

Archivos principales:

- [core/views/laboratorio.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\views\laboratorio.py)
- [core/views/farmacia.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\views\farmacia.py)
- [core/services/ventas/venta_farmacia_service.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\services\ventas\venta_farmacia_service.py)
- [CHECKLIST_CONTROL_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\CHECKLIST_CONTROL_PRISLAB.md)

Cambios ejecutados:

- se corrigió el endpoint `POST /laboratorio/api/crear-orden/`, que estaba roto por mezclar imports y campos de contratos antiguos (`OrdenDetalle`, `Estudio`, `precio_publico`, `usuario`) con el modelo core actual
- el endpoint ahora usa `core.DetalleOrden`, `laboratorio.models.Estudio`, `precio_base`, `responsable_ingreso`, `estado_pago='PENDIENTE'` y guarda el estudio legacy como snapshot textual en `descripcion_linea`
- se validó por smoke directo que el endpoint vuelve a responder `200` y crea una `OrdenDeServicio` en estado `PENDIENTE_PAGO`
- se ajustó `GET /laboratorio/api/medicos/` para soportar búsqueda incremental por `q` o `term`, manteniendo la carga completa cuando no hay filtro
- se validó por smoke directo que al consultar con `q=Bri` la API devuelve solo `Brizia Gonzalez`
- se corrigió un bug operativo crítico del PDV de farmacia: el frontend mostraba productos con `Producto.stock`, pero el backend de cobro exigía lotes y fallaba con `Stock insuficiente` cuando el inventario legado no tenía lotes registrados
- el backend ahora materializa un lote operativo `AUTO-*` si encuentra stock heredado sin lotes, tanto al consultar `/farmacia/api/lotes-producto/<id>/` como al ejecutar la venta
- la venta PDV ahora resuelve una sucursal operativa mínima (`Matriz Principal`) si la empresa todavía no tiene una configurada, evitando que `MovimientoCaja` quede omitido por falta de `sucursal_id`
- se cerró una regresión de doble descuento: las ventas descontadas directamente por Kardex en `VentaFarmaciaService` nacen con `inventario_descontado=True`, evitando que la signal legacy vuelva a restar stock en el guardado final
- se agregó el comando operativo `python manage.py backfill_lotes_operativos_farmacia --empresa-id 1` para convertir inventario legado basado solo en `Producto.stock` a lotes vendibles
- se ejecutó smoke end-to-end de laboratorio con caso real mínimo: alta rápida de paciente (`Paciente Auditoria Lab`), creación de orden `LAB-202606-00002`, lectura de orden, cobro total y aparición en `ordenes-recientes`
- se corrigió compatibilidad de lectura para órdenes legacy: `GET /laboratorio/api/orden/<id>/datos/` ahora devuelve líneas `legacy:*` usando `descripcion_linea` cuando el detalle no está vinculado a `analito/perfil/paquete`
- se corrigió compatibilidad de edición para órdenes legacy: `POST /laboratorio/api/orden/<id>/editar-estudios/` ya puede conservar líneas `legacy:*` existentes sin exigir que todo el payload provenga del catálogo LIMS resoluble
- se ejecutó smoke adicional del módulo de pacientes: `POST /api/pacientes/guardar/` y `GET /api/pacientes/buscar/` responden `200` y reflejan el nuevo paciente correctamente
- se ejecutó smoke funcional de consultorio rápido: creación combinada paciente+consulta, búsqueda de pacientes del consultorio, consulta directa con paciente existente y receta inmediata
- se corrigió un hueco funcional de consultorio: los endpoints rápidos solo creaban `CitaMedica`, por lo que la transcripción inteligente no tenía dónde guardarse; ahora crean también la `ConsultaMedica` base en estado `EN_CURSO`
- tras ese ajuste, `POST /consultorio/api/analizar-transcripcion/` ya devuelve `transcripcion_guardada=true` y persiste `transcripcion_completa` en la consulta creada por flujo rápido
- se corrigió el endpoint legacy `GET /medico/receta/<id>/pdf/`, que fallaba por usar campos inexistentes del modelo `Receta` (`medico_universidad`) y por formateo frágil del IMC; ahora responde `200 application/pdf`
- se validó que `GET /consultorio/pdf/receta/<consulta_id>/` ya genera PDF correcto para la receta inmediata y que la URL devuelta por `api_generar_receta_inmediata` es coherente con la ruta real del proyecto
- se validó impresión operativa adicional: `GET /farmacia/ticket/<venta_id>/raw/` y `GET /laboratorio/ticket/<orden_id>/` responden `200`
- `GET /laboratorio/resultados/<orden_id>/pdf/` redirige a captura en el caso de prueba actual; se clasificó como comportamiento esperado por triple llave incompleta (orden pagada pero no validada ni firmada para entrega digital), no como bug del endpoint
- se perfiló la latencia transversal y se confirmó que la vista de pacientes no era el problema: `api_buscar_pacientes` ejecutada directamente tarda ~`3.75 ms`, mientras que la request completa en frío tardaba ~`4.5 s`
- la causa principal encontrada fue el costo de importación de rutas/módulos al primer request, especialmente `consultorio/api_views.py -> core.services.ai_medico -> google.genai`
- se corrigió ese punto moviendo los imports de `procesar_consulta_medica` y `procesar_resultados_lab` a nivel función dentro de `consultorio/api_views.py`
- mejora medida tras el ajuste: request perfilada en frío a `/api/pacientes/buscar/` bajó de ~`6.97 s` perfilados a ~`3.31 s`, y la latencia registrada del endpoint bajó a ~`2.79 s`
- hallazgo aún abierto de performance: sigue existiendo cold-start import tax por el árbol de rutas/imports globales (`config/urls.py`, `consultorio/urls.py` y módulos top-level relacionados). La siguiente optimización estructural sería lazy-loading adicional de imports pesados en el router principal
- se reconfirmó por smoke directo que:
  - `tool_buscar_o_crear_paciente` pide confirmación antes de crear y sí crea al confirmar
  - `/farmacia/devoluciones/buscar/` y `/farmacia/devoluciones/procesar/` funcionan en HTTPS y persisten auditoría granular
  - `/consultorio/api/procesar-audio-consulta/` devuelve `403` para un usuario de `RECEPCION`
  - una venta PDV real sobre `PARACETAMOL 500MG TAB AUDIT-04` respondió `200`, generó lote `AUTO-4-20260620`, asignó sucursal `Matriz Principal`, creó `MovimientoCaja` y bajó stock exacto `100 -> 99`

Hallazgo aún abierto en esta ronda:

- rendimiento transversal: varios endpoints simples siguen registrando latencias locales de ~4s a ~6s con apenas 2-8 queries (`/api/pacientes/buscar/`, `/laboratorio/api/orden/<id>/datos/`, `/laboratorio/api/orden/<id>/editar-estudios/`); la telemetría crítica de performance no parece ser la causa directa porque crea incidencias en hilo aparte

## 5. Verificaciones ejecutadas por Codex en este cierre

Verificaciones estructurales:

- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test`

Suites relevantes que pasaron en rondas intermedias:

- `core.tests.test_ai_provider_views`
- `core.tests.test_ai_provider_deepseek`
- `core.tests.test_prisci_unified_ai`
- `core.tests.test_public_api_tokens`
- `core.tests.test_tenant_isolation`
- `core.tests.test_dashboard_unificado`
- `core.tests.test_entrega_resultados_bitacora`
- `core.tests.test_read_only_middleware_unit`
- `core.tests.test_farmacia_carga_masiva_excel`
- `core.tests.test_lab_validation_pdf`
- `core.tests.test_blindaje_capacitacion_push`
- `core.tests.test_middleware_local_drivers`
- `core.tests.test_coverage_boost`
- `core.tests.test_super_master`
- `core.tests.test_guardian_v53`
- `core.tests.test_offline_idempotency`
- `core.tests.test_concurrencia_cmms`
- `core.tests.test_clinical_math`
- `academia.tests`
- `consultorio.tests`
- `farmacia.tests`
- `seguridad.tests`
- `logistica.tests`
- `laboratorio.tests.test_westgard`
- `laboratorio.tests.test_hl7_handshake`

Resultado final global:

- `251 tests OK`
- `23 skipped`
- `0 failures`
- `0 errors`

Validación adicional posterior a endurecimiento:

- `manage.py check` -> OK
- regresión focalizada -> `16 tests OK`
- regresión de auditoría -> `4 tests OK`
- regresión de endurecimiento final -> `4 tests OK`

Hallazgos revisados del informe externo:

- corregido: bypass potencial del rate limit por confiar en la primera IP de `X-Forwarded-For`
- corregido: venta operativa de farmacia aceptaba cantidades cero o negativas
- sigue como nota arquitectónica a revisar con cuidado: `Shadow Mode` en tenant puede devolver queryset sin filtrar cuando no hay contexto, pero no se cambió en este corte para no introducir regresiones multitenant sin una ronda dedicada

## 6. Produccion e infraestructura

Entorno objetivo actual:

- VPS Vultr Ubuntu 26.04 LTS
- Nginx
- Gunicorn
- PostgreSQL
- Redis
- Celery
- Celery Beat
- dominio principal `prislab.labcorecloud.com`

Documentos y scripts de despliegue que deben usarse:

- [DEPLOY.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\DEPLOY.md)
- [scripts/deploy_vps.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\scripts\deploy_vps.sh)
- [scripts/aplicar_fixes_produccion.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\scripts\aplicar_fixes_produccion.sh)
- [verify_deployment.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\verify_deployment.sh)

Observacion importante:

- el repositorio local tiene muchisimos cambios acumulados en `git status`
- eso ya no significa "codigo roto", pero si significa que el siguiente trabajo de Claude/Cascada debe ser disciplinado con handoff y actualizacion documental

## 7. Pendientes reales

Pendientes tecnicos que no bloquean la auditoria:

- verificacion funcional real en produccion modulo por modulo con datos reales
- consolidacion de cambios en commits limpios
- revision final de catálogos y valores de referencia contra el sistema legacy
- revision final de flujos de laboratorio, pacientes, clientes, medicos y reportes para paridad total
- despliegues finales de nuevos cambios al servidor conforme se vayan aprobando
- ejecutar en entorno real la nueva carga controlada (`simular_operacion_anual`) y la importacion del Excel de medicos (`importar_medicos_xlsx`) antes de la siguiente auditoria funcional profunda

Pendientes operativos:

- mantener actualizado el documento de control
- no introducir secretos reales en archivos de ejemplo
- registrar cada prueba real de produccion con fecha y resultado

## 8. Instrucciones para Claude y Cascada

### 8.1 Antes de tocar nada

1. Leer completos estos archivos:
   [REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md)
   [CHECKLIST_CONTROL_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\CHECKLIST_CONTROL_PRISLAB.md)
   [DEPLOY.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\DEPLOY.md)
   [env_produccion.txt](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\env_produccion.txt)
2. Confirmar que entienden que el documento de control es obligatorio.
3. No asumir que un documento viejo tiene mas prioridad que estos cuatro.

### 8.2 Si van a revisar codigo

1. Empezar por `manage.py check`
2. Luego `manage.py makemigrations --check --dry-run`
3. Luego `manage.py test`
4. Si todo pasa, moverse a pruebas funcionales reales

### 8.3 Si van a desplegar

1. Usar solo la guia actual de VPS
2. No usar como fuente principal documentos historicos de Cloud Run, Railway o Nixpacks
3. Basarse en:
   [DEPLOY.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\DEPLOY.md)
   [scripts/deploy_vps.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\scripts\deploy_vps.sh)
   [scripts/aplicar_fixes_produccion.sh](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\scripts\aplicar_fixes_produccion.sh)
4. Despues de cada despliegue, documentar resultado en el checklist y en este reporte

### 8.4 Si van a probar funcionalmente

Orden recomendado:

1. Login y sesion
2. Recepcion y ordenes
3. Pacientes
4. Laboratorio
5. Farmacia
6. Consultorio
7. Reportes
8. Academia
9. Integraciones Google

Antes de esa ronda, si el entorno sigue casi vacio, usar primero:

1. `python manage.py importar_medicos_xlsx "C:\\ruta\\Médicos.xlsx" --empresa-id <id>`
2. `python manage.py simular_operacion_anual --empresa-id <id> --usuario <user> --pacientes 300 --ordenes-lab 800 --ventas-farmacia 1500 --devoluciones-farmacia 120 --dias 365`

En cada modulo deben registrar:

- fecha
- ambiente
- usuario usado
- flujo probado
- resultado
- bug encontrado
- si se corrigio o no

### 8.5 Regla de actualizacion documental

Al terminar cualquier cambio, deben actualizar al menos:

- [CHECKLIST_CONTROL_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\CHECKLIST_CONTROL_PRISLAB.md)
- [REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md)

Sin esa actualizacion, el cambio no cuenta como cerrado.

## 9. Objetivo final compartido

La meta ya no es solo "que corra".  
La meta es:

- reemplazar al sistema legacy con paridad operativa real
- dejar PRISLAB SaaS verificable, desplegable y auditable
- construir una pared tan solida que cualquier auditoria externa encuentre muy poco por romper
- terminar el proyecto lo mas pronto posible sin sacrificar trazabilidad ni control

## 10. Cierre de Codex

Mi criterio profesional en este punto es:

- ya esta listo para que Claude y Cascada entren a revisar
- no porque "ya no haya nada mas por hacer"
- sino porque la base ya es suficientemente estable, probada y documentada para que la siguiente fase sea auditoria seria y cierre final, no rescate
 
## 11. Actualización adicional 2026-06-20
 
### 11.1 Consultorio rápido validado y corregido
 
Se auditó el flujo rápido de consultorio usando endpoints reales del módulo:
 
- `/consultorio/api/crear-paciente-y-consulta/`
- `/consultorio/api/buscar-pacientes/`
- `/consultorio/api/crear-consulta-directa/`
- `/consultorio/api/generar-receta-inmediata/`
- `/consultorio/api/analizar-transcripcion/`
- `/consultorio/pdf/receta/<consulta_id>/`
 
Hallazgo real:
 
- el flujo rápido creaba `CitaMedica`, pero no garantizaba `ConsultaMedica`
- eso provocaba que la transcripción SOAP no se persistiera realmente
 
Corrección aplicada:
 
- en [consultorio/views.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\consultorio\views.py) ahora `api_crear_consulta_directa` y `api_crear_paciente_y_consulta` crean o recuperan `ConsultaMedica`
- después del ajuste, `api_analizar_transcripcion` ya guarda `transcripcion_completa` correctamente
 
### 11.2 PDFs médicos y tickets
 
Se corrigió una falla real en el PDF legacy:
 
- ruta: `/medico/receta/<id>/pdf/`
- error original: acceso a atributo inexistente `receta.medico_universidad`
 
Corrección:
 
- [core/views/medico.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\views\medico.py) ahora usa `getattr(...)` seguro
- también se corrigió el formato del IMC para evitar errores con valores nulos
 
Validaciones:
 
- `/medico/receta/<id>/pdf/` ya responde PDF
- `/consultorio/pdf/receta/<consulta_id>/` responde PDF correcto
- `/farmacia/ticket/<venta_id>/raw/` operativo
- `/laboratorio/ticket/<orden_id>/` operativo
- `/laboratorio/resultados/<orden_id>/pdf/` mantiene redirección esperada a captura cuando aún no se cumple el blindaje completo
 
### 11.3 Rendimiento - reducción de cold start por imports
 
Se identificó que el mayor castigo del primer request no estaba en la lógica de búsqueda de pacientes, sino en imports pesados durante la carga del router.
 
Evidencia de auditoría:
 
- llamada directa a la vista de búsqueda: milisegundos
- request completo con `Client()`: varios segundos
- perfilado apuntó a carga temprana de:
  - `consultorio/api_views.py`
  - `core/services/ai_medico.py`
  - `core/views/pris_ia.py`
  - módulos del router raíz
 
Correcciones aplicadas:
 
1. [consultorio/api_views.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\consultorio\api_views.py)
   - imports de IA médica movidos dentro de las funciones de audio
 
2. [config/urls.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\config\urls.py)
   - se agregó `lazy_view(...)`
   - se difirió carga de módulos pesados:
     - `core.views.pris_ia`
     - `core.views.prisci_webhook`
     - `core.views.voice`
     - `core.views.push`
     - `core.views.notificaciones`
     - `core.views.nomina`
     - `core.views.crm`
     - `core.views.comunicacion`
 
Resultado:
 
- la penalización del primer request quedó reducida de forma tangible en pruebas locales previas
- falta validación final en VPS con stack real `Nginx + Gunicorn`
 
### 11.4 Nota importante de validación local

Al intentar correr verificaciones Django adicionales en este entorno local apareció un bloqueo ajeno al cambio:
 
- `PermissionError` sobre `logs/prislab_audit.log`
- handler afectado: `file_audit`
 
Conclusión:
 
- no apunta a error sintáctico del código nuevo
- sí conviene revisar permisos de la carpeta `logs/` o endurecer el fallback de logging para auditorías locales futuras

### 11.5 Corrección crítica de Recepción Laboratorio

Se detectó el bug que ya se había manifestado en producción:

- la interfaz de recepción mostraba estudios agregados correctamente
- pero al confirmar podía terminar en error de validación porque el endpoint seguía usando una implementación legacy basada en `laboratorio.Estudio`

Hallazgo técnico:

- [core/templates/core/recepcion_lab.html](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\templates\core\recepcion_lab.html) envía tokens del catálogo LIMS como:
  - `analito:ID`
  - `perfil:ID`
  - `paquete:ID`
- [core/views/laboratorio.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\views\laboratorio.py) todavía tenía una `crear_orden_servicio` legacy que intentaba resolver eso contra `laboratorio.Estudio`

Corrección aplicada:

- `crear_orden_servicio` ahora delega directamente a [core/services/lims/orden_recepcion_service.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\services\lims\orden_recepcion_service.py)
- con eso queda alineado al mismo flujo LIMS usado por el resto del sistema

Impacto esperado:

- desaparece el falso negativo de “sí hay estudios visualmente, pero backend dice que no”
- la orden ahora conserva:
  - líneas LIMS correctas
  - convenio
  - médico referidor
  - cortesía / CxC
  - pago inicial e idempotencia

### 11.6 Blindaje adicional en Farmacia PDV

Se agregó validación defensiva en backend para evitar ventas inconsistentes:

- [core/services/ventas/venta_farmacia_service.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\services\ventas\venta_farmacia_service.py)

Protecciones nuevas:

- rechaza carrito vacío
- rechaza cantidades no numéricas
- rechaza cantidades menores o iguales a cero

Motivo:

- aunque la UI normalmente lo evita, el backend no debe crear ventas vacías ni detalles imposibles si llega una petición dañada o incompleta

### 11.7 Ajuste multitenant en Consultorio + LIMS

Se corrigió una fuga potencial de resolución de catálogo:

- [consultorio/views.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\consultorio\views.py)

Hallazgo:

- en la generación de órdenes de laboratorio desde consultorio se llamaba `resolve_lims_cart_ids(...)` sin pasar `empresa`
- eso no siempre falla visible, pero sí permite resolver por coincidencia de IDs fuera del tenant correcto

Corrección aplicada:

- ahora los dos flujos de consultorio que convierten estudios a líneas LIMS pasan `empresa=empresa`

Impacto:

- mayor consistencia multiempresa
- menor riesgo de mezclar catálogo entre tenants cuando el sistema ya opere con más laboratorios

### 11.8 Devoluciones Farmacia - cierre operativo real

Se detectó un hueco funcional importante en devoluciones:

- el flujo sí registraba `SalesReturn`
- pero no estaba garantizando la devolución física de stock a inventario en esta capa

Correcciones aplicadas en [core/services/ventas/venta_farmacia_service.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\services\ventas\venta_farmacia_service.py):

- normalización de contrato frontend:
  - `REINGRESAR` ahora se traduce a `RETORNO_ALMACEN`
- validación de acción de stock permitida
- si la devolución total no trae detalle explícito, se construyen las partidas usando todo lo vendido
- prevención de sobredevoluciones acumuladas por partida
- reingreso real de inventario por lote con `MovimientoInventario(tipo_movimiento='ENTRADA_DEVOLUCION')` cuando la acción es retorno a almacén

Impacto:

- la devolución deja de ser solo administrativa
- el Kardex vuelve a reflejar inventario real
- se conserva trazabilidad por lote en devoluciones parciales o totales

### 11.9 Devoluciones frontend reales + corte de caja laboratorio

Se cerraron dos hallazgos más de operación real:

- [core/services/ventas/venta_farmacia_service.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\services\ventas\venta_farmacia_service.py)
- [core/views/farmacia.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\views\farmacia.py)

Hallazgo 1:

- la pantalla real de devoluciones envía `productos_devueltos`
- el backend estaba leyendo `productos`
- eso podía dejar devoluciones parciales sin detalle operativo válido

Corrección aplicada:

- el servicio ahora acepta ambos nombres de payload: `productos` y `productos_devueltos`
- además rechaza devoluciones parciales si no llega al menos una partida válida

Hallazgo 2:

- el corte de caja unificado estaba sumando laboratorio por `OrdenDeServicio.total`
- eso inflaba el corte con órdenes creadas el día aunque no estuvieran realmente cobradas

Corrección aplicada:

- laboratorio ahora aporta al corte solo por cobranzas reales registradas en `PagoOrden`
- `total_lab` queda alineado con efectivo y digital realmente cobrados

Impacto:

- devoluciones parciales ya siguen el contrato real del frontend
- el corte de caja refleja mejor la operación de laboratorio en caja diaria

### 11.10 URL rota en órdenes de laboratorio generadas desde consultorio

Se cerró un bug de navegación real:

- [consultorio/views.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\consultorio\views.py)
- [core/views/paciente_detalle.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\core\views\paciente_detalle.py)

Hallazgo:

- el flujo de consultorio devolvía `url_detalle = /laboratorio/orden/<id>/`
- esa ruta no existe en [config/urls.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\config\urls.py)
- el mismo enlace muerto aparecía en el timeline/historial clínico del paciente

Corrección aplicada:

- ambos puntos ahora enlazan a una ruta real de laboratorio: `reverse('imprimir_ticket_lab', args=[orden.id])`

Impacto:

- la orden creada desde consulta ya abre una vista existente
- el historial del paciente deja de tener botones “ver” que mandan a 404

### 11.11 Soporte preparado para Vultr Object Storage (S3-compatible)

Se dejó lista la integración del SaaS con almacenamiento S3-compatible de Vultr para media operativa:

- [config/settings.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\config\settings.py)
- [config/storage_backends.py](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\config\storage_backends.py)
- [requirements.txt](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\requirements.txt)
- [.env.example](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\.env.example)
- [env_produccion.txt](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\env_produccion.txt)

Cambios aplicados:

- nuevo backend `TenantS3Storage` basado en `django-storages` para prefijar automáticamente `{empresa_slug}/...`
- nuevas variables `VULTR_OBJECT_STORAGE_ENABLED`, `VULTR_S3_ACCESS_KEY_ID`, `VULTR_S3_SECRET_ACCESS_KEY`, `VULTR_S3_ENDPOINT_URL`, `VULTR_S3_BUCKET_NAME`
- prioridad explícita de Vultr Object Storage sobre Google Drive cuando ambos estén configurados
- dependencia `boto3` agregada para soporte S3 real

Impacto:

- PRISLAB ya no queda atado solo a local + Drive para media
- se puede mover media operativa del SaaS a `prislab-media` sin tocar Academia
- Academia puede seguir yendo a una plataforma aparte de streaming protegido
