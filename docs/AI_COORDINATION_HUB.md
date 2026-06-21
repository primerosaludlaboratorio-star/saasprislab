# AI Coordination Hub - PRISLAB

Este hub reduce el copiado manual entre Codex, Claude y Cascada.

No conecta magicamente con las cuentas externas de cada IA. Funciona como tablero
compartido por archivos: recibe reportes, los clasifica de forma inicial, mantiene
estado comun y genera briefs limpios para cada agente.

## Archivos principales

- `scripts/ai_coordination_hub.py`: script principal.
- `AI_COORDINATION_STATUS.md`: estado compartido actual.
- `docs/ai_coordination/inbox/`: reportes recibidos.
- `docs/ai_coordination/outbox/`: instrucciones listas para cada agente.
- `docs/ai_coordination/state.json`: estado estructurado.

## Uso rapido

Inicializar:

```powershell
python scripts/ai_coordination_hub.py init
```

Registrar un reporte desde archivo:

```powershell
python scripts/ai_coordination_hub.py ingest --agent claude --file C:\ruta\reporte.txt
```

Registrar texto directo:

```powershell
python scripts/ai_coordination_hub.py ingest --agent cascada --text "Pegue aqui el resumen del hallazgo"
```

Generar brief para un agente:

```powershell
python scripts/ai_coordination_hub.py brief --agent cascada
```

Ver estado compartido:

```powershell
python scripts/ai_coordination_hub.py status
```

## Roles

Codex:
- Corrige codigo, causa raiz, pruebas y commits.
- Confirma o rechaza hallazgos contra codigo/logs.

Claude:
- Prueba flujos humanos en produccion cuando navegador esta estable.
- Reporta paso exacto, esperado, real y bloqueo.

Cascada:
- Analiza evidencia, clasifica hallazgos y detecta contradicciones.
- No reabre frentes ya cerrados con commit/prueba/despliegue confirmado.

## Clasificaciones

- `CONFIRMADO`: evidencia suficiente y coincide con codigo/logs.
- `PROBABLE`: senal util, falta prueba.
- `PENDIENTE_VALIDAR`: requiere produccion, navegador o config real.
- `OPERATIVO`: infraestructura, DB, servicios, red, deploy.
- `LIMITACION_HERRAMIENTA`: problema de navegador, extension o entorno del agente.
- `RUIDO`: conclusion demasiado grande para la evidencia.

## Regla de oro

Ningun modulo queda "aprobado final" hasta tener:

- evidencia tecnica,
- prueba funcional humana,
- estado de despliegue confirmado,
- y cierre documentado.
