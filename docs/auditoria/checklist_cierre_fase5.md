# Checklist de cierre — Fase 5 Auditoría humana integral (L11)

## Regla STOP (obligatoria)
- [ ] **STOP:** Si existe algún FAIL de severidad **CRITICA** abierto, se detiene el cierre inmediatamente.

## Gates de cierre
- [ ] Matriz Módulo x Rol x Tipo de prueba ejecutada y consolidada (`cubierto|parcial|no_cubierto|bloqueado`).
- [ ] Todos los flujos principales con PASS de inicio a fin por perfil aplicable.
- [ ] No hay FAIL ALTA abierto (o, si existe, cuenta con dispensa formal aprobada y fecha de remediación comprometida).
- [ ] Cada corrección aplicada tiene regresión en verde (misma ruta/flujo afectado).
- [ ] PDFs/reportes/exportaciones (PDF, Excel, CSV) fueron abiertos y validados como legibles.
- [ ] Inventario de ortografía, consistencia y lenguaje humano completado e inventariado.
- [ ] Variaciones obligatorias ejecutadas (doble clic, recarga POST, back, doble sesión, concurrencia, red, timeout, CSRF ausente, etc.).
- [ ] Verificación de aislamiento tenant y RBAC por URL directa completada.
- [ ] Limpieza de datos sintéticos completada y evidenciada.

## Muestra cruzada y conciliación
- [ ] Muestra cruzada independiente completada en **20%** de flujos de otros auditores (**redondeo hacia arriba**).
- [ ] Conciliación independiente completada sin leer reportes ajenos durante primera entrega.
- [ ] Coincidencias, exclusivos y discrepancias de severidad reconciliados con evidencia.
- [ ] Exclusivos reproducidos manualmente antes de confirmar o refutar.

## Integridad documental
- [ ] Cada escenario contiene commit, entorno, fecha UTC, URL base, rol, empresa, sucursal y evidencia.
- [ ] Cada hallazgo separa HECHO/OBSERVACION/INFERENCIA/HIPOTESIS/RECOMENDACION.
- [ ] Reporte consolidado incluye omisiones y límites.
- [ ] Declaración final de modo (solo lectura / datos creados / limpieza) completada.
