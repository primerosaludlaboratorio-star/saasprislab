# Plan de Colaboración Secuencial — Editor 1 (Cascade) + Editor 2 (Antigravity)

**Versión:** 2.0 — Secuencial  
**Fecha:** 2026-07-09  
**Rama base:** 
elease/v1.0-local  
**Nivel de los editores:** 11 (arquitectura, código limpio, seguridad, operación)

---

## 1. Objetivo

Completar los bloques enterprise pendientes y la migración funcional P0 de PRISLAB SaaS usando dos editores senior en **modo secuencial**: cada fase tiene un único editor responsable. Al finalizar todas las fases, Editor 1 revisa e integra todo.

---

## 2. Principios de colaboración

1. **Rama base:** 
elease/v1.0-local.
2. **Ejecución secuencial:** solo un editor activo por fase.
3. **Sin push directo:** cada fase se entrega mediante PR revisado por Editor 1.
4. **Espera obligatoria:** ningún editor avanza a la siguiente fase sin confirmación explícita del Product Owner y de Editor 1.
5. **Definition of Done (DoD) común:** tests + CI verde + docs + sin secretos + sin migraciones faltantes + revisión aprobada.

---

## 3. Flujo de fases

`
Fase 1  -> Fase 2  -> Fase 3  -> Fase 4  -> Fase 5
Editor 1  Editor 2  Editor 1  Editor 2  Editor 1
(Infra)   (P0)      (Sec)     (Gov/Perf)(Integración)
`

---

## 4. Fases detalladas

### Fase 1 — Fundamentos de infra y CI/CD (Editor 1: Cascade)

**Duración estimada:** 3–5 días  
**Responsable:** Editor 1  
**Objetivo:** Dejar lista la base técnica sobre la cual Antigravity construirá.

| # | Tarea | Entregable |
|---|-------|-----------|
| 1.1 | Configurar branch protection en 
elease/v1.0-local | Regla activa, sin bypass |
| 1.2 | Mergear PRs #8 y #9 | PRs mergeados, CI verde |
| 1.3 | Crear .github/workflows/deploy-vps.yml | Pipeline de deploy a staging/prod |
| 1.4 | Crear .env.staging.example y .env.production.example | Variables documentadas por ambiente |
| 1.5 | Crear docker-compose.monitoring.yml | Prometheus + Alertmanager + Grafana |
| 1.6 | Verificar consumo de /metrics/ | Dashboard inicial en Grafana |
| 1.7 | Retirar scripts/backup_to_drive.py | Script eliminado o marcado obsoleto |
| 1.8 | Actualizar docs/SRE_RUNBOOKS.md y docs/SLO_SLI.md | Docs con URLs de monitoreo |

**Branch:** eat/editor1-fase1-infra  
**Criterio de salida:** CI verde, deploy a staging funcional, stack de monitoreo levantado.

---

### Fase 2 — Migración funcional P0 (Editor 2: Antigravity)

**Duración estimada:** 10–18 días  
**Responsable:** Editor 2  
**Objetivo:** Cerrar paridad operativa con el sistema legado.

| # | Tarea | Entregable |
|---|-------|-----------|
| 2.1 | Bloque 1: Catálogo LIMS base | Cardinalidad, perfiles, paquetes, tarifas |
| 2.2 | Bloque 2: Valores de referencia y PDF | Rangos por sexo/edad, PDF idéntico a captura |
| 2.3 | Bloque 3: Recepción y órdenes | Payload frontend/backend, cobro mixto, CxC, confirmación |
| 2.4 | Bloque 8: Cobranza | Formas de pago, pagos mixtos, anticipo, cancelación |
| 2.5 | Bloque 13: Reportes críticos | Corte, caja, cobranza, hoja de trabajo |

**Branch:** eat/editor2-fase2-p0-funcional  
**Criterio de salida:** Tests por bloque, comparativa con legado, CI verde.

---

### Fase 3 — Seguridad y Supply Chain / SDLC (Editor 1: Cascade)

**Duración estimada:** 5–8 días  
**Responsable:** Editor 1  
**Objetivo:** Cerrar controles enterprise de seguridad y cadena de suministro.

| # | Tarea | Entregable |
|---|-------|-----------|
| 3.1 | Agregar secret scanning (gitleaks) al CI | Workflow que falla ante secretos |
| 3.2 | Resolver PRs dependabot #13 y #35 | Dependencias actualizadas |
| 3.3 | Generar SBOM | sbom.json/sbom.csv + CI |
| 3.4 | Documentar entornos dev/staging/prod | docs/ENTORNOS_PRISLAB.md |
| 3.5 | Refinar pipeline de deploy con smoke tests | Deploy + smoke test post-deploy |

**Branch:** eat/editor1-fase3-security-sdlc  
**Criterio de salida:** Security/SDLC listo, dependencias al día, CI verde.

---

### Fase 4 — Governance, RBAC y Performance Validation (Editor 2: Antigravity)

**Duración estimada:** 7–12 días  
**Responsable:** Editor 2  
**Objetivo:** Documentar decisiones, cerrar permisos y validar performance.

| # | Tarea | Entregable |
|---|-------|-----------|
| 4.1 | Matriz RBAC | docs/MATRIZ_ROLES_PRISLAB.md + tests |
| 4.2 | ADRs | docs/adr/ con decisiones clave (multi-tenant, URLs, LIMS, seguridad) |
| 4.3 | Definition of Done | docs/DEFINITION_OF_DONE.md |
| 4.4 | Roadmap | docs/ROADMAP_PRISLAB.md |
| 4.5 | Pruebas de carga | Scripts Locust/k6 para órdenes y PDFs |
| 4.6 | Bloques 11 y 12 (opcional) | Lealtad y microbiología si aplica |

**Branch:** eat/editor2-fase4-governance-perf  
**Criterio de salida:** Docs de governance, tests de carga, CI verde.

---

## 5. Fase 5 — Revisión final e integración (Editor 1: Cascade)

**Duración estimada:** 3–5 días  
**Responsable:** Editor 1  
**Objetivo:** Revisar todo e integrar ordenadamente.

| # | Tarea | Entregable |
|---|-------|-----------|
| 5.1 | Revisar PRs de Fase 2 y Fase 4 | Aprobaciones o correcciones |
| 5.2 | Ejecutar suite completa de tests | python manage.py test |
| 5.3 | Validar CI de todos los workflows | Todos verdes |
| 5.4 | Verificar monitoreo con métricas reales | Dashboards con datos |
| 5.5 | Merge ordenado a 
elease/v1.0-local | Historial limpio |
| 5.6 | Reporte final de cierre | Documento/PR con resumen |

---

## 6. Zonas de coordinación obligatoria

Aunque las fases son secuenciales, Editor 2 necesita conocer estas zonas para no romper el trabajo de Editor 1:

| Zona | Regla |
|------|-------|
| config/settings.py | Editor 2 puede modificarlo en Fase 2/4, pero con cuidado y notificación en PR. |
| config/urls/ | Editor 2 agrega rutas de módulos en Fase 2. Editor 1 ya estableció la estructura en Fase 1. |
| 
equirements.txt | Editor 2 añade deps de funcionalidad; Editor 1 las audita en Fase 3. |
| docker-compose.monitoring.yml | Editor 1 lo crea; Editor 2 lo consume en pruebas de carga. |
| docs/ | Cada editor actualiza docs de su fase. |

---

## 7. Definition of Done (DoD) común

Cada PR de cada fase debe cumplir:

- [ ] Código funcional y probado localmente.
- [ ] Tests nuevos o actualizados.
- [ ] CI relevante verde.
- [ ] Documentación actualizada.
- [ ] Sin secretos hardcodeados.
- [ ] Sin migraciones faltantes (makemigrations --check).
- [ ] Revisión aprobada por Editor 1.
- [ ] Merge a 
elease/v1.0-local vía PR, no push directo.

---

## 8. Comunicación

- **Inicio/fin de fase:** Editor activo avisa al Product Owner y a Editor 1.
- **Daily update:** comentario en PR activo con formato: Fase X | Avance % | Bloqueo | PR #Y.
- **Bloqueos > 4h:** se escala al Product Owner.

---

## 9. Métricas de éxito

| Métrica | Meta |
|---------|------|
| Fases completadas | 5/5 |
| Bloques P0 cerrados | 5/5 (1, 2, 3, 8, 13) |
| Bloques enterprise 3–6 cerrados | 4/4 |
| PRs abiertos resueltos | 100 % |
| CI verde en 
elease/v1.0-local | 100 % del tiempo |
| Deploy a staging automatizado | ✅ |
| /metrics/ consumido por Prometheus/Grafana | ✅ |
| Documentos de governance | ≥ 4 |

---

## 10. Notas para el Product Owner

- Este plan asume que **Editor 1 controla la base técnica y la integración final**, y **Editor 2 lidera la paridad funcional y governance**.
- El Product Owner debe validar cada bloque funcional con datos reales del legado antes de declararlo cerrado.
- El plan puede ajustarse si una fase se retrasa, pero no se debe saltar fases.
