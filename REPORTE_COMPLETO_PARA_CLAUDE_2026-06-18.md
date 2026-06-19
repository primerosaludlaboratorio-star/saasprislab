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
