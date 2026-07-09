# Plan de Colaboración — Editor 1 (Cascade) + Editor 2 (Antigravity)

**Versión:** 1.0  
**Fecha:** 2026-07-09  
**Rama base:** `release/v1.0-local`  
**Nivel de los editores:** 11 (arquitectura, código limpio, seguridad, operación)

---

## 1. Objetivo

Dividir el trabajo faltante para llevar PRISLAB SaaS a un estado **enterprise-ready y funcionalmente paritario con el sistema legado**, usando dos editores senior. Cada editor tiene ownership claro de paquetes para minimizar conflictos de merge y maximizar velocidad sin sacrificar calidad.

---

## 2. Principios de colaboración

1. **Rama base única:** `release/v1.0-local`.  
2. **Sin push directo:** todo cambio pasa por PR con revisión cruzada.  
3. **Ownership por archivos:** cada editor respeta las áreas asignadas; si se requiere tocar archivo ajeno, se notifica en el PR.  
4. **Definition of Done (DoD) común:** tests + CI verde + docs + revisión cruzada.  
5. **Sincronización diaria:** comentario de progreso en el PR activo.  
6. **No dependencias circularies:** Editor 1 entrega infra/estructura primero; Editor 2 consume esos cimientos para los módulos funcionales.  
7. **Evidencia antes de merge:** cada bloque se cierra con un documento de evidencia y un test o CI que lo respalde.

---

## 3. División de paquetes de trabajo

### Paquete A — Editor 1 (Cascade): Infraestructura, CI/CD, SRE/Performance, Core Backend y Bloques P0

**Ownership de directorios/archivos principales:**
- `.github/workflows/`
- `Dockerfile`, `docker-compose.yml`, `nginx/`
- `scripts/deploy_vps.sh`, `scripts/web_entrypoint.sh`, `scripts/backup/`
- `config/settings.py`, `config/urls/` (cambios aquí requieren coordinación)
- `core/middleware/sre_metrics.py`, `core/views/monitoring.py`, `docs/SRE_RUNBOOKS.md`, `docs/SLO_SLI.md`
- `lims/`, `laboratorio/`, `core/views/laboratorio*.py`, `core/views/finanzas*.py`
- `docs/DR_PLAN.md` (mantenimiento)

**Tareas:**

| # | Bloque/Tarea | Descripción | Evidencia de cierre |
|---|-------------|-------------|----------------------|
| A.1 | **CI/CD pipeline de deploy** | Crear `.github/workflows/deploy-vps.yml` que haga SSH al VPS, haga pull de `release/v1.0-local`, ejecute migraciones y reinicie contenedores con zero-downtime. | Workflow SUCCESS en staging. |
| A.2 | **Entornos formales** | Crear `.env.staging.example` y `.env.production.example`; documentar variables por ambiente. | Archivos + README de despliegue. |
| A.3 | **Secret scanning** | Agregar workflow con `gitleaks` o GitHub secret scanning; fallar build si hay secretos. | Workflow SUCCESS y detección de 1 secreto de prueba. |
| A.4 | **Prometheus + Grafana + Alertmanager** | Añadir `docker-compose.monitoring.yml`, configs de Prometheus, dashboards de Grafana y reglas de alerta. | `/metrics/` consumido, alertas de prueba disparadas. |
| A.5 | **Pruebas de carga** | Crear `tests/load/locustfile.py` o script k6 para `/health/`, login, creación de orden. | Reporte de latencia p95. |
| A.6 | **SBOM y auditoría de dependencias** | Generar `sbom.json`/`sbom.csv` con `pip-audit` o similar; agregar a CI. | Archivo + workflow. |
| A.7 | **Deprecar `scripts/backup_to_drive.py`** | Retirar script legado o marcarlo como obsoleto; asegurar que `backup_postgres.sh` sea el flujo oficial. | Eliminación/documentación. |
| A.8 | **Bloque 1: Catálogo LIMS base** | Completar cardinalidad, rangos, perfiles, paquetes y tarifas vs legado. | Script de comparación + test. |
| A.9 | **Bloque 2: Resultados y referencias** | Validar rangos por sexo/edad, impresión y PDF idénticos a captura. | Tests de PDF + capturas. |
| A.10 | **Bloque 3: Recepción y órdenes** | Sincronizar payload frontend/backend, cobro exacto, cobro mixto, CxC, confirmación. | E2E test o Playwright. |
| A.11 | **Bloque 8: Cobranza** | Todas las formas de pago, pagos mixtos, anticipo, cancelación con motivo. | Tests de estados de pago. |
| A.12 | **Bloque 13: Reportes críticos** | Corte por sucursal, ventas por cliente, caja, cobranza pendiente, exámenes, hoja de trabajo. | Comparativa vs legado. |

---

### Paquete B — Editor 2 (Antigravity): Módulos Funcionales P1, Seguridad/GRC y Governance

**Ownership de directorios/archivos principales:**
- `pacientes/`, `core/views/paciente*.py`
- `seguridad/`, `core/views/administracion_usuarios.py`
- `consultorio/`, `enfermeria/`
- `marketing/` (programa de lealtad, CRM)
- `contabilidad/` (facturación, si aplica)
- `docs/` para governance y políticas
- `core/middleware/seguridad.py`, `core/middleware/rate_limit.py`, `core/middleware/admin_access.py`

**Tareas:**

| # | Bloque/Tarea | Descripción | Evidencia de cierre |
|---|-------------|-------------|----------------------|
| B.1 | **Mergear PRs de Copilot** | Revisar y mergear PR #8 (CI `makemigrations --check`) y PR #9 (fix PDF regression test). | PRs mergeados, CI verde. |
| B.2 | **Revisar dependabot PRs** | Evaluar y mergear/rechazar PRs #13 y #35. | PRs resueltos. |
| B.3 | **Bloque 4: Pacientes** | Paridad fina de alta, edición, búsqueda, duplicados, expediente. | Tests + comparativa. |
| B.4 | **Bloque 5: Clientes** | Clave, tarifa base, bloqueo, sucursales, catálogos por cliente. | Tests + datos de prueba. |
| B.5 | **Bloque 6: Médicos** | Alta, búsqueda, asignación a órdenes, comisiones, entregas físicas. | Tests. |
| B.6 | **Bloque 7: Cotización** | Presupuestos, promociones, PDF, conversión a orden. | Tests + comparativa de totales. |
| B.7 | **Bloque 9: Auditoría** | Filtros, exportación, eventos críticos, cambios de precios/resultados. | UI + export tests. |
| B.8 | **Bloque 10: Seguridad y permisos** | Paridad fina de perfiles vs legado; matriz de roles. | Documento + tests de permisos. |
| B.9 | **Bloque 11: Programa de lealtad** | Monedero, acumulación, redención, vencimiento, excepciones. | Tests de saldo y redención. |
| B.10 | **Bloque 12: Microbiología** | Catálogo de bacterias/antibióticos, antibiograma automático. | Tests de despliegue. |
| B.11 | **Bloque 14: Integraciones externas** | TuLab, WhatsApp, CFDI, analizadores HL7, DICOM/EvaPacs, S3. | Estado documentado por integración; críticas activas. |
| B.12 | **Política de seguridad** | Crear `docs/POLITICA_SEGURIDAD.md` con inventario de riesgos, controles y responsables. | Documento aprobado. |
| B.13 | **Matriz de roles y permisos** | Crear `docs/MATRIZ_ROLES_PRISLAB.md` comparando legado vs SaaS. | Documento + tests. |
| B.14 | **Governance: ADRs** | Crear `docs/adr/` con decisiones arquitectónicas clave. | 5+ ADRs. |
| B.15 | **Governance: Definition of Done y RACI** | Crear `docs/DEFINITION_OF_DONE.md` y `docs/RACI.md`. | Documentos. |
| B.16 | **Governance: Roadmap** | Crear `docs/ROADMAP_PRISLAB.md` con milestones, owners y fechas. | Documento. |

---

## 4. Zonas compartidas / coordinación obligatoria

| Zona | Responsable | Regla |
|------|------------|-------|
| `config/settings.py` | **Coordinado** | Cualquier cambio notificado en PR; riesgo de romper todo. |
| `config/urls/` (paquete) | **Coordinado** | Editor 1 es guardian de rutas; Editor 2 notifica si agrega URLs. |
| `core/models/base.py` | **Coordinado** | Cambios afectan tenant y permisos. |
| `requirements.txt` | **Coordinado** | Editor 2 puede agregar librerías de módulos; Editor 1 de infra. |
| `docker-compose.yml` | **Editor 1** | Editor 2 propone cambios vía PR. |
| `docs/` generales | **Ambos** | Cada bloque actualiza docs propios. |
| CI workflows | **Editor 1** | Editor 2 notifica si necesita nuevo job. |

---

## 5. Secuencia de ejecución recomendada

### Fase 0 — Preparación (días 1–3)
- Ambos editores leen este plan y confirman ownership.
- Editor 1 crea branches `feat/editor1-infra-p0`.
- Editor 2 crea branches `feat/editor2-p1-governance`.
- Editor 2 mergea PRs #8 y #9.

### Fase 1 — Cimientos enterprise + P0 funcional (días 4–21)
- **Editor 1:** A.1, A.2, A.3, A.8, A.9, A.10.
- **Editor 2:** B.1, B.2, B.12 (política de seguridad), B.15 (DoD/RACI).
- Entregable: CI verde, deploy a staging, P0 funcional cerrado.

### Fase 2 — Módulos P1 funcionales (días 22–45)
- **Editor 1:** A.4 (monitoring), A.5 (load tests), A.6 (SBOM), A.11, A.12.
- **Editor 2:** B.3, B.4, B.5, B.6, B.7, B.8, B.9, B.10.
- Entregable: Módulos P1 cerrados con tests y docs.

### Fase 3 — Enterprise restante + integraciones (días 46–60)
- **Editor 1:** A.7 (deprecar backup legado), refinamiento de SLOs/alertas.
- **Editor 2:** B.11 (integraciones), B.13, B.14, B.16 (roadmap).
- Entregable: Bloques enterprise 3–6 cerrados.

### Fase 4 — Integración y validación final (días 61–75)
- Ambos editores integran a `release/v1.0-local`.
- Validación final de reemplazo (Bloque 15).
- Go/No-go a producción.

---

## 6. Definition of Done (DoD) común

Cada PR debe cumplir:

- [ ] Código funcional y probado localmente.
- [ ] Tests nuevos o actualizados; suite crítica pasa.
- [ ] CI relevante verde (`main.yml`, `sre-health-check.yml`, `backup-restore-test.yml`).
- [ ] Documentación actualizada (README, runbook, ADR o módulo afectado).
- [ ] Sin secretos hardcodeados.
- [ ] Sin migraciones faltantes (`makemigrations --check`).
- [ ] Revisión cruzada del otro editor aprobada.
- [ ] Merge a `release/v1.0-local` vía PR, no push directo.

---

## 7. Protocolo de resolución de conflictos

1. Si ambos tocan el mismo archivo, el **propietario del área** tiene la decisión final técnica.
2. Si el conflicto es en infraestructura compartida (`settings.py`, `urls/`, `docker-compose.yml`), se escala a discusión en el PR con evidencia de impacto.
3. Ningún editor resuelve un conflicto a favor de "funcionar rápido" si eso reduce seguridad, observabilidad o estabilidad.

---

## 8. Comunicación y handoffs

- **Daily update:** comentario en PR activo con formato:  
  `Editor X | Fase Y | Avance | Bloqueo | PR #Z`.
- **Handoff técnico:** cuando Editor 1 entrega infra que Editor 2 necesita, se documenta en el PR con ejemplo de uso.
- **Reuniones de sync:** cada 2 días o cuando un editor tenga un bloqueo > 4h.

---

## 9. Métricas de éxito

| Métrica | Meta |
|---------|------|
| Bloques P0 cerrados | 3/3 (1, 2, 3) |
| Bloques P1 cerrados | ≥ 7/10 (4–10, 13) |
| Bloques enterprise 3–6 cerrados | 4/4 |
| PRs abiertos resueltos | 100 % |
| CI verde en `release/v1.0-local` | 100 % del tiempo |
| Deploy a staging automatizado | ✅ |
| `/metrics/` consumido por Prometheus | ✅ |
| Documentación de governance | ≥ 5 documentos |

---

## 10. Notas para el usuario (Product Owner)

- Este plan asume que **Editor 1 lidera la base técnica** y **Editor 2 lidera la paridad funcional y governance**.
- Si surge un bloqueo técnico mayor, ambos editores pueden pivotar temporalmente a la misma área, pero siempre bajo PR.
- El usuario debe validar cada bloque funcional con datos reales del legado antes de declararlo cerrado.
