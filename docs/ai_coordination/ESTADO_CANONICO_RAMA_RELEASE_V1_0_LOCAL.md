# Estado Canonico de PRISLAB SaaS

Fecha de consolidacion: 2026-06-21  
Rama canonica: `release/v1.0-local`

## Proposito

Este documento existe para que Copilot, Claude, Cascada y Codex lean una sola verdad.

Todo reporte nuevo debe contrastarse contra la rama `release/v1.0-local` y no contra snapshots viejos o ramas vacias.

## Lectura obligatoria

1. `CHECKLIST_CONTROL_PRISLAB.md`
2. `REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md`
3. `AI_COORDINATION_STATUS.md`
4. `docs/ai_coordination/GUIA_OPERATIVA_FINAL.md`
5. `docs/ai_coordination/PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md`

## Estado real confirmado

- La rama `release/v1.0-local` es la linea vigente de trabajo.
- El historial reciente incluye el fix `650f1ef` para analisis globales y acceso a expediente de director.
- No debe usarse `main` como fuente de verdad operativa.

## Hallazgos que siguen vigentes

### 1. 2FA

Archivo:

- `core/views/autenticacion_2fa.py`

Hallazgo:

- sigue existiendo bypass por redes genericas `192.168.*` y `10.*`
- esto sigue siendo un riesgo real de seguridad y configuracion

### 2. Resultados publicos

Archivo:

- `core/views/entrega_resultados.py`

Hallazgo:

- los tokens publicos siguen con vigencia larga de 30 dias
- esto sigue siendo una decision de seguridad que conviene revisar

### 3. Sesiones

Archivo:

- `config/settings.py`

Hallazgo:

- `SESSION_COOKIE_AGE` sigue con default de 30 dias
- `SECURE_SSL_REDIRECT` queda forzado en produccion, pero el default base sigue siendo `False`

### 4. Sentinel

Archivos:

- `core/views/sentinel_api.py`
- `core/middleware/sentinel.py`

Hallazgo:

- ya no depende de `SECRET_KEY` como fallback
- el reporte viejo de `admin_token` por GET ya no describe el estado actual
- sigue habiendo hardening y revisiones pendientes, pero no ese vector viejo

## Hallazgos desactualizados

### P2 Director Analizadores

Estado actual del codigo:

- `core/views/director.py` ya usa `Equipo.objects.all()`
- `laboratorio.models.Equipo` sigue siendo un catalogo global

Conclusion:

- el `FieldError` reportado por versiones anteriores ya no aplica al estado actual de la rama
- debe tratarse como `resuelto/obsoleto` en esta linea de trabajo

### H3 Medico Expediente

Estado actual del codigo:

- `core/views/expediente.py` ya permite acceso a `DIRECTOR`, `ADMIN`, `ADMINISTRADOR`, `GERENTE` y `MEDICO`
- Sentinel limita reintentos 403

Conclusion:

- no debe seguir etiquetandose como `loop infinito` sin repro actual
- si alguien quiere reabrirlo, debe reproducirse contra esta rama actual y con paciente real

### H1 Farmacia 301

Estado actual del codigo:

- el reporte venia de una ruta legacy de auditoria
- el endpoint real de farmacia usa la ruta API correcta

Conclusion:

- es falso positivo de auditor legacy

### H2 Auditoria Lab deprecated

Estado actual del codigo:

- `auditoria_lab_full.py` sigue siendo deprecated a proposito

Conclusion:

- es deuda de herramienta, no bug de producto

## Linea operativa para Copilot

- usar esta rama como verdad
- si un reporte contradice este documento, primero revisar el codigo actual
- no reabrir bugs viejos sin reproduccion en `release/v1.0-local`
- cuando haya hallazgo real nuevo, citar archivo, linea y evidencia tecnica

