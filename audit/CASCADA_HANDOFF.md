# Handoff para Cascada

## Objetivo

Realizar una auditoria independiente, read-only, sobre el commit indicado y
reportar solo defectos reproducibles. Cascada no debe editar codigo, datos,
usuarios, credenciales, despliegues ni historiales.

## Base exacta

- Repositorio: `primerosaludlaboratorio-star/saasprislab`
- Rama local: `release/v1.0-local`
- Commit a auditar: `72bd201`
- Directorio: `PRISLAB_SaaS-master/PRISLAB_SaaS-master`
- Fuente de inventario: `audit/FUNCTION_LEDGER.md` y `audit/FRONTEND_FUNCTION_LEDGER.md`
- Manifiesto de cobertura: `tools/omni_manifest.json`

## Alcance

1. Verificar tenant isolation, RBAC, CSRF, autenticacion, IDOR, cifrado,
   logging, integridad de resultados LIMS, inventario y operaciones financieras.
2. Verificar que las rutas y funciones del ledger coincidan con el codigo
   actual y que no se usen reportes historicos como evidencia de estado actual.
3. Revisar templates e interfaces modificadas, con especial atencion a
   ortografia, textos inconsistentes, formularios, CSRF, errores visibles y
   generacion de PDF.
4. Ejecutar las pruebas automatizadas disponibles sin alterar el entorno.
5. Si se autoriza acceso web, realizar solo navegacion y operaciones de
   consulta. Para mutaciones, usar exclusivamente datos sinteticos y
   reversibles en un entorno de prueba; nunca usar produccion para vender,
   cancelar, devolver, borrar, validar resultados o cambiar inventario.

## Comandos reproducibles

```powershell
$env:DJANGO_SETTINGS_MODULE = 'config.settings'
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python -m compileall -q core contabilidad farmacia laboratorio lims seguridad iot logistica pacientes recepcion enfermeria mantenimiento
python tools/audit_coverage_gate.py --inventory tools/url_inventory.json --manifest tools/omni_manifest.json --out audit/cascada_coverage_gate.json --enforce
node --check tools/ai_agent_tools.mjs
node --check tools/audit_frontend_inventory.mjs
node --check tools/excel_builder/build_reactivos_insumos.mjs
```

La suite completa debe ejecutarse en Python 3.12 con PostgreSQL equivalente a
produccion. Si la base de pruebas no puede crearse, reportar el bloqueo y no
convertirlo en aprobacion ni en fallo funcional.

## Formato obligatorio del reporte

Cada hallazgo debe incluir: ID unico, severidad, archivo y linea, precondiciones,
pasos reproducibles, resultado esperado, resultado real, impacto, evidencia,
si fue confirmado en ejecucion, y recomendacion. Separar expresamente:

- confirmado y reproducible;
- falso positivo o codigo muerto;
- deuda tecnica sin fallo demostrado;
- bloqueo del entorno;
- no verificado.

No repetir valores de contrasenas, API keys, tokens ni secretos. Los scripts
que contienen credenciales quedan fuera de remediacion por ahora y solo deben
ser reportados como riesgo sin imprimir sus valores.

## Criterio de cierre

No declarar el sistema enterprise-ready ni los bloques cerrados por conteo de
rutas. El cierre requiere evidencia funcional, prueba de regresion, aislamiento
por tenant y resultado reproducible en el entorno correspondiente. Las
interfaces y las pruebas E2E humanas son la fase final y permanecen abiertas
hasta su ejecucion documentada.

## Correcciones recientes a verificar

- `iot/views_api.py`: check-in con campos y estados reales dentro de transaccion atomica.
- `core/services/ventas/cobro_service.py`: importes calculados desde el producto del tenant, no desde valores del navegador; medico acotado por empresa.
- `core/views/laboratorio/calidad.py`: rol clinico y rate-limit para validar PIN.
- `iot/views.py`: disponibilidad calculada con `total_seconds()`.
- `core/services/ventas/cobro_service.py`: redondeo de efectivo limitado a +/- $0.50.
- `core/services/ventas/cobro_service.py`: porcentaje de descuento derivado en servidor.
- `core/views/historial_resultados.py` y su plantilla: anotacion compatible con Django para el indicador forense.
- Plantillas de interfaz: escape de salidas dinamicas, CSRF en acciones de lista y mensajes explicitos cuando el PDF no esta disponible.
- `core/views/sentinel_api.py`: comparaciones de tokens Sentinel mediante `secrets.compare_digest`.
- Herramientas auxiliares de PRIS-IA: rechazan mutaciones sobre ordenes `RESULTADOS_LISTOS` o `ENTREGADO`; la prueba de regresion debe confirmar que no se ejecuta ninguna escritura.
- `core/views/paciente_detalle.py`: el timeline ya enlaza al endpoint protegido de PDF y no expone la URL física de `/media/`.
- La prueba `core.tests.test_lab_validation_pdf` requiere creación de base de datos; si el entorno se bloquea durante esa fase, debe reportarse como bloqueo y no como aprobación.
- `core/views/prisci_webhook.py`: los tokens de recepción y verificación usan `secrets.compare_digest`; validar ambas rutas y sus regresiones.
- `mantenimiento/views/helpers.py` y `seguridad/views/helpers.py`: se eliminaron las
  definiciones duplicadas que quedaban sombreadas; la única implementación activa
  conserva el mismo contrato de tenant y autenticación.
- En esta máquina, `python manage.py test core.tests.test_prisci_unified_ai --keepdb` llegó a `Using existing test database` y no avanzó durante 60 segundos; el proceso fue finalizado de forma controlada. La validación directa sin BD sí confirmó token válido, token alterado rechazado y challenge GET correcto. Tratarlo como bloqueo del runner, no como prueba verde.
- En la verificación posterior del commit `9b9b12e`, `manage.py check` y
  `compileall` pasaron, pero la batería `core.tests.test_tenant_boundary_views
  core.tests.test_suscripciones_iot_security core.tests.test_pris_jarvis_rbac`
  volvió a quedar bloqueada durante `Creating test database`; no se declara
  aprobación de esa batería.
- La comprobación `check --deploy` con `PRISLAB_ENV=production` y secretos
  ficticios falló cerrado al exigir `PRISLAB_ESCUDO_USUARIO_ID` y reportó
  tokens de servicio ausentes. No se rellenaron secretos ni identificadores
  reales; validar en el entorno seguro de despliegue.
