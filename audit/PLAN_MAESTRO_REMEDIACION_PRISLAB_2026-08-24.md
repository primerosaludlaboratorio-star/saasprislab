# PLAN MAESTRO DE REMEDIACION Y CIERRE PRISLAB

**Fecha de control:** 2026-08-24
**Sistema:** PRISLAB SaaS
**Empresa auditada:** Primero Salud Laboratorio SAS de CV
**Tenant:** Empresa 1
**Sucursal base:** Sucursal 1
**Repositorio operativo:** C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master
**Produccion:** https://prislab.labcorecloud.com/

## Reglas de control

1. No modificar, eliminar ni rotar claves o contrasenas sin instruccion expresa.
2. No borrar datos productivos, usuarios, historiales, ventas, resultados, respaldos ni evidencia.
3. No declarar un bloque cerrado por lectura estatica: cada cierre requiere prueba reproducible y evidencia.
4. No agregar propietarios ficticios al manifiesto de rutas.
5. Toda modificacion de produccion debe tener diff, prueba local, validacion remota y rollback identificable.
6. Las pruebas destructivas solo pueden ejecutarse con datos sinteticos y reversibles en staging.
7. El aislamiento de empresa debe probarse con al menos dos empresas y dos roles.

## Estado de partida

- manage.py check: correcto.
- Migraciones: sin cambios pendientes.
- Produccion: salud y disponibilidad verificadas.
- Nginx: sintaxis correcta, media clinica bloqueada y rate limiting aplicado.
- Frontend: 428 plantillas, 249 scripts, 439 handlers, 0 errores de parseo.
- Python: 1,299 archivos, 3,652 funciones productivas sin evidencia conductual individual.
- Rutas: 1,956 inventariadas; 1,956 asignadas y 0 sin owner; pruebas conductuales aun pendientes.
- Suite completa: no cerrada en este entorno por falta de Python 3.12/PostgreSQL.
- Docker: no disponible en el entorno local.
- Credenciales y contrasenas: fuera del alcance de remediacion por instruccion.

## Fase 0 - Control de cambios y evidencia

**Objetivo:** impedir que las sesiones paralelas vuelvan a desalinear el proyecto.

- Confirmar siempre el checkout canonico antes de editar.
- Registrar cada cambio en este plan y en el informe de auditoria.
- Separar cambios de codigo, infraestructura, pruebas y documentacion.
- Mantener un registro de revision, despliegue, resultado y rollback.
- Verificar git diff --check, estado del arbol y migraciones antes de cada despliegue.

**Cierre:** un solo checkout operativo, cambios trazables y ningun archivo generado fuera de control.

## Fase 1 - Calidad estatica y catalogos de evidencia

**Objetivo:** eliminar errores de tooling y desfasajes documentales.

- Mantener el ledger Python sin errores de sintaxis ni señales sin disposicion.
- Mantener el ledger frontend con 0 errores de parseo.
- Regenerar inventario de rutas y resumen en cada cambio de URLconf.
- Mantener owners reales para las 1,956 rutas por modulo y tipo.
- Actualizar tools/omni_manifest.json sin falsificar cobertura.
- Validar templates principales con parseo y render controlado.

**Cierre:** gate de rutas sin faltantes, parseo limpio y evidencia de cada owner.

## Fase 2 - Seguridad y aislamiento multi-tenant

**Objetivo:** comprobar que ningun usuario puede cruzar empresas o elevar privilegios.

- Revisar modelos sin TenantModel y justificar o corregir cada excepcion.
- Probar consultas, admin, APIs, archivos y exportaciones con Empresa 1 y Empresa 2.
- Auditar todos los endpoints de administracion, Sentinel, IoT, suscripciones y transferencias.
- Confirmar segregacion de funciones en contabilidad, devoluciones, autorizaciones y resultados.
- Validar CSRF, rate limiting, sesiones, 2FA y almacenamiento de datos sensibles.
- Mantener las credenciales existentes intactas, pero documentar su riesgo sin reutilizarlas.

**Cierre:** matriz de autorizacion aprobada para roles ADMIN, GERENTE, QUIMICO, FARMACIA, RECEPCION y paciente.

## Fase 3 - LIMS y laboratorio

**Objetivo:** cerrar el flujo clinico completo.

- Alta de paciente y orden.
- Seleccion de analitos, perfiles, paquetes y precios.
- Recepcion, toma, consentimiento y trazabilidad.
- Captura manual y por interfaz de equipos.
- Validacion tecnica y clinica.
- Bloqueo de resultados validados, correcciones controladas y auditoria append-only.
- Rangos, unidades, valores criticos, delta check y Westgard.
- Reactivos, lotes, consumo, caducidad, controles y calibradores.
- Maquila, resultado externo, equipo alterno y contingencia.
- Impresion, PDF, entrega y portal autorizado.
- Pruebas de errores: equipo caido, reactivo agotado, control fuera de rango, corte de energia y resultado incompleto.

**Cierre:** cada escenario tiene resultado esperado, resultado real, evidencia y rollback.

## Fase 4 - Farmacia, inventario y caja

**Objetivo:** cerrar el flujo comercial y financiero de farmacia.

- Alta y edicion de producto y codigo de barras.
- Material de curacion sin restricciones de receta.
- Antiboticos con receta, surtido parcial y total.
- Precio publico, descuentos, precio costo y cortesias.
- FEFO, lotes, caducidad y baja.
- Venta individual y combinada.
- Cobro parcial y total.
- Ticket digital detallado.
- Devolucion parcial y total con PIN y permisos.
- Historial de ventas, devoluciones, cortes, precortes y arqueos.
- Turnos, retiros, compras y conciliacion.
- Prueba de concurrencia para evitar doble descuento o sobreventa.

**Cierre:** flujo humano completo validado en produccion solo con datos permitidos y escenarios reversibles.

## Fase 5 - PDF, reportes e interfaz humana

**Objetivo:** que el personal entienda y pueda verificar el sistema.

- Revisar ortografia, capitalizacion y etiquetas.
- Renderizar PDF de receta, resultados, tickets, facturas, reportes y consentimientos.
- Validar descarga, impresion, contenido, permisos y aislamiento.
- Probar vistas en escritorio y movil.
- Confirmar mensajes de error, confirmacion, carga, bloqueo y recuperacion.
- Verificar que no existan botones que aparenten funcionar y no ejecuten accion.

**Cierre:** PDFs abiertos visualmente, legibles y completos; interfaz sin errores de parseo ni flujos ambiguos.

## Fase 6 - Dependencias y suministro

**Objetivo:** que el software instalado sea exactamente el auditado.

- Ejecutar pip-audit sobre requirements.lock.
- Confirmar versiones corregidas de Django, cryptography, pypdf y sqlparse.
- Ejecutar npm audit y npm test.
- Construir Docker con --require-hashes.
- Generar SBOM y revisar vulnerabilidades.
- Confirmar que CI y produccion instalan desde el mismo lock.

**Cierre:** auditoria de dependencias sin vulnerabilidades no aceptadas y artefacto reproducible.

## Fase 7 - Infraestructura, backups y continuidad

**Objetivo:** demostrar recuperacion operativa.

- Ejecutar docker compose config y levantar stack en staging.
- Validar PostgreSQL, Redis, Gunicorn, Celery, Nginx y health checks.
- Probar backup cifrado productivo en una copia aislada.
- Restaurar en staging y verificar conteos, integridad y acceso.
- Documentar RPO, RTO, responsables y rollback.
- Probar rotacion operacional solo cuando sea autorizada.

**Cierre:** restauracion demostrada sin tocar datos productivos.

## Fase 8 - CI/CD y despliegue

**Objetivo:** que ningun cambio llegue a produccion sin evidencia.

- Quality Gate obligatorio para el mismo SHA.
- Tests, lint, dependencias, SBOM y secret scan.
- Despliegue controlado desde el checkout canonico.
- Migraciones verificadas antes de reiniciar servicios.
- Nginx validado antes de recargar.
- Health, ready y servicios activos despues del despliegue.
- Registro de revision y rollback.

**Cierre:** una corrida real y exitosa del pipeline, mas una verificacion post-deploy.

## Fase 9 - E2E humano por modulo

**Orden obligatorio:**

1. Acceso, roles, empresa y sucursal.
2. Recepcion y pacientes.
3. Consultorio y expediente.
4. Farmacia e inventario.
5. Laboratorio y LIMS.
6. Interfaces de equipos.
7. Contabilidad y caja.
8. PDFs, reportes y entrega.
9. Sentinel, IA, notificaciones y auditoria.
10. Recuperacion, cancelaciones, devoluciones y contingencias.

Cada caso debe registrar:

- Usuario y rol.
- Empresa y sucursal.
- Datos sinteticos o identificador reversible.
- Pasos completos de inicio a fin.
- Resultado esperado.
- Resultado real.
- Evidencia.
- Incidencia, correccion y nueva prueba.

## Criterio final de cierre

PRISLAB solo se declarara cerrado cuando:

- No existan errores de parseo, migraciones ni checks.
- El gate de rutas tenga 0 faltantes reales.
- La suite autoritativa pase en Python 3.12/PostgreSQL.
- Dependencias y contenedor sean reproducibles.
- Backup y restauracion tengan evidencia.
- Los flujos humanos por modulo pasen.
- Produccion este validada despues del despliegue.
- Las excepciones restantes esten documentadas y aprobadas, sin ocultarlas.

## Registro de avance

| Fecha | Fase | Accion | Evidencia | Estado |
|---|---|---|---|---|
| 2026-08-24 | 1 | Normalizacion del parser Django y correccion de politicas_descuento.html | Ledger frontend: 0 errores | Cerrado |
| 2026-08-24 | 1 | Regeneracion del ledger Python | 1,299 archivos, 0 errores de sintaxis | Cerrado |
| 2026-08-24 | 1 | Baseline de rutas actualizado a 1,956 | tools/omni_manifest.json | Cerrado |
| 2026-08-24 | 1 | Gate de propietarios de rutas | 1,956 asignadas, 0 sin owner | Cerrado (ownership) |
| 2026-08-24 | 1 | Pruebas conductuales de rutas | E2E por modulo aun no ejecutado | Abierto |
| 2026-08-24 | 2 | Aislamiento multi-tenant y seguridad base | 22/22 pruebas correctas | Cerrado |
| 2026-08-24 | 3 | Aislamiento de configuracion LIMS | 7/7 pruebas correctas | Cerrado |
| 2026-08-24 | 3 | PIN de laboratorio | `core.tests.test_lab_pin_hash`: 2/2 correctas | Cerrado |
| 2026-08-24 | 3 | Recepcion por tenant | `core.tests.test_laboratorio_recepcion_tenant`: 1/1 correcta | Cerrado |
| 2026-08-24 | 3 | HL7 y vinculacion de tenant | `core.tests.test_hl7_tenant_binding`: 3/3 correctas | Cerrado |
| 2026-08-24 | 3 | Audio de toma sensible | `core.tests.test_audio_toma_security`: 1/1 correcta; sin FERNET no persiste audio en claro | Cerrado |
| 2026-08-24 | 3 | Seguridad de kiosco | `laboratorio.tests.test_kiosko_security`: 2/2 correctas | Cerrado |
| 2026-08-24 | 3 | PDF y QR | `core.tests.test_pdf_and_qr_security`: 2/2 correctas | Cerrado |
| 2026-08-24 | 3 | Gobernanza Westgard y telemetria Sentinel | `WestgardGovernanceTests` + `SentinelTelemetryGuardTests`: 3/3 correctas | Cerrado |
| 2026-08-24 | 3 | Cifrado fail-closed | `EncryptedTextFieldSecurityTests`: 3/3 correctas | Cerrado |
| 2026-08-24 | 3 | Cierres de seguridad sensibles | Preparacion del entorno de prueba se bloquea en migraciones; sin resultado concluyente | Abierto |
| 2026-09-13 | 7 | Retencion de registros fiscales ante borrado de empresa | Relaciones `empresa` de contabilidad cambiadas a `PROTECT`; migracion `contabilidad.0014` unica; `manage.py check` y `makemigrations --check` correctos | Parcial: prueba de borrado bloqueada por preparacion SQLite |
| 2026-09-13 | 0 | Reconciliacion de reporte externo c33eeae | Checkout vigente contrastado; varios hallazgos del reporte eran anteriores y los controles actuales fueron confirmados | Registrado |
| 2026-09-13 | 7 | Validacion de contenedor | Docker CLI no disponible en este equipo | Bloqueado por entorno |
| 2026-09-13 | 7 | Alias de estaticos en Nginx Docker | `prislab.docker.conf` alineado con `static_data:/app/staticfiles`; comprobacion de referencias correcta | Pendiente de `nginx -t` dentro de contenedor |
| 2026-09-13 | 6 | Actualizacion de dependencias vulnerables | `pypdf 6.16.1`, `weasyprint 70.0`; `pip-audit`: sin vulnerabilidades; `npm audit`: 0; `npm test`: correcto | Cerrado en lock; falta validar imagen Docker |
| 2026-09-13 | 8 | Validacion de despliegue local | 7 workflows YAML validos; script PowerShell valido; `check --deploy` limpio con entorno de produccion sintético | Pendiente de corrida CI/VPS real |
| 2026-09-13 | 7 | Revisión de backup y restore | Scripts presentes con `pg_dump`/`pg_restore` y verificacion de listado; Bash no esta disponible para `bash -n` | Pendiente de ejecutar en host Linux/PostgreSQL aislado |
| 2026-09-13 | 7-8 | Acceso y reconciliacion VPS | API Vultr, SSH por clave, servicios, puertos, migraciones y hashes; evidencia en `audit/VULTR_ACCESS_DIAGNOSTICO_2026-09-13.md` | Produccion operativa; artefacto productivo sin `.git` y 24 archivos compartidos difieren del local |
| 2026-09-13 | 3 | Pruebas dirigidas posteriores al acceso VPS | 10/10 correctas: PDF/QR, PIN laboratorio, HL7, audio sensible y kiosco; `check` y `makemigrations --check` correctos | Cerrado para esta bateria; E2E humano completo sigue separado |
| 2026-09-13 | 8 | Guard de integridad del despliegue local | `scripts/deploy_local_to_vps.ps1` ahora bloquea arbol sucio, valida SHA de release y exige configuraciones Nginx presentes; prueba negativa detuvo el checkout actual antes de SSH | Cerrado como control; despliegue pendiente de release limpio |
| 2026-09-13 | 1 | Gate de cobertura de rutas | `python tools/audit_coverage_gate.py --enforce`: `covered=1956`, `uncovered=0`, `covered_ratio=1.0` | Cerrado para ownership; no sustituye pruebas conductuales |
| 2026-09-13 | 2-8 | Regresion funcional posterior | La bateria agrupada no concluyo durante la preparacion de la base de pruebas local; proceso detenido por bloqueo de entorno, sin declarar aprobacion | Abierto; requiere Python 3.12/PostgreSQL o CI autoritativo |
| 2026-08-24 | 2-8 | Pendientes de ejecucion ordenada | Informe total | Abierto |
