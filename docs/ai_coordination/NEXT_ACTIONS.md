# NEXT ACTIONS - PRISLAB Multi-IA

Este archivo es la cola viva de trabajo. Cada agente debe leerlo junto con su
brief antes de empezar. Si no puede ejecutar su tarea principal, toma la
siguiente tarea de su carril sin esperar al usuario.

## Reglas de reparto

- Codex: codigo, causa raiz, pruebas automaticas, commits, documentacion tecnica.
- Claude: auditoria funcional humana en produccion, paso por paso, con evidencia UI/API.
- Cascada: analisis de evidencia, contradicciones, riesgo, priorizacion y checklist.
- Nadie debe pisar archivos que otro agente declare en uso.
- Si un hallazgo no tiene evidencia reproducible, clasificarlo como PENDIENTE_VALIDAR o RUIDO.
- Si aparece un 500, separar primero OPERATIVO vs BUG antes de concluir.

## Carril Codex

1. Cerrar el patron LIMS/legacy `DetalleOrden.estudio` en codigo productivo.
2. Agregar regresiones para cada bloqueo real confirmado.
3. Ejecutar pruebas focalizadas y `manage.py check`.
4. Hacer commit pequeno con mensaje claro y actualizar docs de control.
5. Preparar instrucciones de deploy solo cuando tests pasen.

## Carril Claude

1. Auditar Laboratorio en produccion como usuario real:
   recepcion -> paciente -> estudios -> cobro -> toma -> procesamiento -> captura -> validacion -> PDF -> entrega.
2. No saltarse pasos ni navegar directo a pantallas internas salvo para confirmar.
3. Probar variantes: descuento, cortesia, parcial/CxC, cancelacion/devolucion, impresion.
4. Si Chrome falla, reportar LIMITACION_HERRAMIENTA y pasar a auditoria UI visual de pantallas disponibles.
5. Entregar cada hallazgo con: URL, usuario, paso, esperado, real, evidencia visible, severidad.

## Carril Cascada

1. Leer reportes nuevos en `docs/ai_coordination/inbox`.
2. Clasificar: CONFIRMADO, PROBABLE, PENDIENTE_VALIDAR, OPERATIVO, LIMITACION_HERRAMIENTA, RUIDO.
3. Buscar contradicciones contra commits, tests y `AI_COORDINATION_STATUS.md`.
4. Proponer el siguiente bloque de verificacion sin tocar codigo salvo autorizacion explicita.
5. Mantener lista de deuda real, no ruido.

## Si no hay reportes nuevos

- Claude debe ejecutar `docs/ai_coordination/outbox/TAREA_ACTIVA_CLAUDE.md`.
- Cascada debe ejecutar `docs/ai_coordination/outbox/TAREA_ACTIVA_CASCADA.md`.
- Codex revisa bugs de alto impacto y agrega pruebas donde falten.
