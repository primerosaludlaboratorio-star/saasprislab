# Fase 4 - Controles negativos

## Alcance

El ejecutor scripts/audit/run_negative_controls.py valida regresiones
estaticas sobre archivos reales del checkout. No sustituye pruebas
funcionales, multi-tenant, LIMS, concurrencia o E2E.

En execute, cada invariante se elimina solo en una copia temporal. Se
comprueba que el detector la encuentre ausente y se compara SHA-256 antes y
despues de restaurarla. El checkout principal nunca se modifica.

## Estados

- PASS: la mutacion fue detectada y el archivo fue restaurado con el mismo SHA-256.
- FAIL: la mutacion no fue detectada o la restauracion no coincide.
- BLOCKED: falta el archivo o la invariante base; no es un resultado positivo.
- READY: catalogo valido en dry-run, sin mutar archivos.

## Ejecucion reproducible

    python scripts/audit/run_negative_controls.py --mode dry-run --output audit/fase4-runtime/negative-controls-dry-run.json
    python scripts/audit/run_negative_controls.py --mode execute --output audit/fase4-runtime/negative-controls-execute.json

El workflow .github/workflows/fase4-negative-controls.yml ejecuta ambos pasos
en un contenedor efimero de Python 3.12 y publica los JSON como artifact. No
usa credenciales, no accede al VPS y no escribe sobre la rama principal.

## Limite de evidencia

Un PASS certifica el detector estatico y el aislamiento del harness, no la
seguridad completa de la aplicacion. La Fase 4 solo puede cerrarse despues de
conservar el run de Actions, su exit code, los JSON y el SHA-256 del artifact.
