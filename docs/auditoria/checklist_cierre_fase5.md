# Checklist de cierre — Fase 5 Auditoria humana integral (L11)

## Regla STOP (obligatoria)
- [ ] **STOP:** Si existe algun FAIL de severidad **CRITICA** abierto, se detiene el cierre inmediatamente.

## Gates de cierre
- [ ] Matriz Modulo x Rol x Tipo de prueba ejecutada y consolidada (`cubierto|parcial|no_cubierto|bloqueado`).
- [ ] Todos los flujos principales con PASS de inicio a fin por perfil aplicable.
- [ ] **No hay FAIL CRITICO/ALTO abierto** al momento de cierre (CRITICA detiene de inmediato; ALTA bloquea cierre hasta remediacion o dispensa formal).
- [ ] Cada correccion aplicada tiene regresion en verde (misma ruta/flujo afectado).
- [ ] PDFs/reportes/exportaciones (PDF, Excel, CSV) fueron abiertos y validados como legibles.
- [ ] Inventario de ortografia, consistencia y lenguaje humano completado e inventariado.
- [ ] Variaciones obligatorias ejecutadas (doble clic, recarga POST, back, doble sesion, concurrencia, red, timeout, CSRF ausente, etc.).
- [ ] Verificacion de aislamiento tenant y RBAC por URL directa completada.
- [ ] Limpieza de datos sinteticos completada y evidenciada.

## Muestra cruzada y conciliacion
- [ ] Muestra cruzada independiente completada en **20%** de flujos de otros auditores (**redondeo hacia arriba**).
- [ ] Conciliacion independiente completada sin leer reportes ajenos durante primera entrega.
- [ ] Coincidencias, exclusivos y discrepancias de severidad reconciliados con evidencia.
- [ ] Exclusivos reproducidos manualmente antes de confirmar o refutar.

## Integridad documental
- [ ] Cada escenario contiene commit, entorno, fecha UTC, URL base, rol, empresa, sucursal y evidencia.
- [ ] Cada hallazgo separa HECHO/OBSERVACION/INFERENCIA/HIPOTESIS/RECOMENDACION.
- [ ] Reporte consolidado incluye omisiones y limites.
- [ ] Declaracion final de modo (solo lectura / datos creados / limpieza) completada.
