# NEXT ACTIONS - PRISLAB Multi-IA

Este archivo es la cola viva de trabajo. Cada agente debe leerlo junto con su
brief antes de empezar. Si no puede ejecutar su tarea principal, toma la
siguiente tarea de su carril sin esperar al usuario.

## Lectura obligatoria

- `docs/ai_coordination/AI_COORDINATION_STATUS.md`
- `docs/ai_coordination/PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md`
- `docs/ai_coordination/ESTADO_CANONICO_RAMA_RELEASE_V1_0_LOCAL.md`

## Reglas de reparto

- Codex: codigo, causa raiz, pruebas automaticas, commits, documentacion tecnica.
- Claude: auditoria funcional humana en produccion, paso por paso, con evidencia UI/API.
- Cascada: analisis de evidencia, contradicciones, riesgo, priorizacion y checklist.
- Nadie debe pisar archivos que otro agente declare en uso.
- Si un hallazgo no tiene evidencia reproducible, clasificarlo como PENDIENTE_VALIDAR o RUIDO.
- Si aparece un 500, separar primero OPERATIVO vs BUG antes de concluir.
- La verificacion manual de interfaz debe seguir `docs/ai_coordination/PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md`.
- Si falla la extension de navegador o la IA, no se detiene la verificacion humana.

## Herramienta canónica de UI

- Ejecutar `npm run human:ui -- --target cloud --user <usuario> --pass <clave>` para la verificación visible.
- Agregar `--pause` si se quiere revisar cada módulo antes de continuar.
- La salida oficial es `auditoria_ui_<timestamp>/report.md` y `auditoria_ui_<timestamp>/report.json`.
- Las IAs solo consumen ese reporte final; no deben ser la fuente primaria de la validación de interfaz.

## Carril Codex

1. Integrar modulo por modulo solo lo que siga vivo y no este ya cerrado en el canon.
2. Agregar regresiones para cada bloqueo real confirmado.
3. Ejecutar pruebas focalizadas y `manage.py check`.
4. Hacer commit pequeno con mensaje claro y actualizar docs de control.
5. Preparar instrucciones de deploy solo cuando tests pasen.

### Cierres ya completados por Codex en esta ronda

- Consultorio PDF / tenant efectivo -> `b9217b9`
- Director + IA/PRIS timezone local -> `d26a09d`

No deben volver a entrar como pendiente salvo evidencia nueva.

### Prioridad viva para la siguiente ronda

1. Buzon / Comunicacion / Notificaciones
   - aislar `MensajeInterno` por tenant
   - eliminar la colision de `buzon_kanban`
   - resolver `tu_opinion` multi-tenant
   - endurecer guards de notificaciones
2. RH / Nomina
   - restringir vistas RH por rol
   - decidir/aislar `Competencia` por empresa
   - validar tenant de `mis_resultados`
   - endurecer `_empresa()` en nomina
3. Contabilidad / Finanzas
   - agregar `@role_required` en vistas sensibles
   - alinear reportes a `timezone.localdate()`
   - endurecer `autofactura_publica`
4. Farmacia
   - cerrar cobertura faltante de corte de caja, apertura, COFEPRIS, entrada express y carga masiva
   - mantener fuera del backlog los 4 hallazgos ya resueltos
5. Recepcion
   - cerrar contraste final y evidencia de pruebas para sacarla del estado pendiente

### Modulos ya cerrados y que no deben reabrirse sin repro nueva

- Consultorio PDF / tenant efectivo
- Director
- IA/PRIS (fix TZ en alcance Director/IA/PRIS)
- Pacientes
- Laboratorio funcional principal
- Enfermeria
- Inventario

### Modulos estabilizados que no deben volver al carril critico sin repro nueva

- Logistica
- Mantenimiento
- Bienestar
- Academia
- Marketing

## Carril Claude

1. Core.
2. Farmacia.
3. Laboratorio.
4. Consultorio.
5. IA.
6. Tests.
7. Refactorizar y alinear al canon oficial modulo por modulo.
8. Entregar reporte maestro por modulo antes de pasar al siguiente.

## Carril Cascada

1. Tests.
2. Consultorio.
3. Farmacia.
4. IA.
5. Clasificar evidencia, contradicciones y legacy/noise de cada modulo.
6. Leer reportes nuevos en `docs/ai_coordination/inbox`.
7. Buscar contradicciones contra commits, tests y `AI_COORDINATION_STATUS.md`.
8. Mantener lista de deuda real, no ruido.

## Si no hay reportes nuevos

- Claude debe ejecutar `docs/ai_coordination/outbox/TAREA_ACTIVA_CLAUDE.md`.
- Cascada debe ejecutar `docs/ai_coordination/outbox/TAREA_ACTIVA_CASCADA.md`.
- Codex revisa bugs de alto impacto y agrega pruebas donde falten.
