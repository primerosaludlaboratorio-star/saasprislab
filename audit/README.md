# Auditoría Canónica PRISLAB

Este directorio contiene evidencia y documentos de auditoría. Los archivos
históricos conservan el contexto de su fecha y no sustituyen la evidencia de
la ejecución actual.

## Ejecutores canónicos

Desde la raíz del repositorio:

```powershell
python tools/audit_url_inventory.py
python tools/audit_coverage_gate.py --enforce
python tools/audit_function_inventory.py
node tools/audit_frontend_inventory.mjs
node tools/run_omni_suite.mjs --target local --base http://127.0.0.1:8000
node tools/run_human_ui_audit.mjs --target cloud
```

Los dos últimos runners requieren credenciales suministradas por el operador
mediante variables de entorno y deben ejecutarse con datos sintéticos o
reversibles. Nunca se deben guardar credenciales en informes ni en el árbol.

## Evidencia actual

- `audit/PLAN_MAESTRO_REMEDIACION_PRISLAB_2026-08-24.md`: plan y criterios de cierre.
- `audit/VULTR_ACCESS_DIAGNOSTICO_2026-09-13.md`: diagnóstico operativo del VPS.
- `audit/coverage_gate_report.json`: último gate de cobertura de rutas.
- `audit/FUNCTION_LEDGER.md`: inventario Python generado.
- `audit/FRONTEND_FUNCTION_LEDGER.md`: inventario frontend generado.

## Regla de vigencia

Un reporte solo puede declarar un cierre si incluye fecha, commit o revisión,
comando, resultado y limitaciones. Los reportes anteriores con inventarios
distintos deben tratarse como históricos, no como baseline vigente.
