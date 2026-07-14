# Roadmap de Remediación — Auditoría PRISLAB SaaS

**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## Quick Wins (bajo esfuerzo, alto impacto)

| ID | Acción | Prioridad | Hallazgo | Esfuerzo | Impacto |
|----|--------|-----------|----------|----------|---------|
| QW-01 | Eliminar bypass de branch protection en `release/v1.0-local` | P1 | H-001 | Bajo | Crítico |
| QW-02 | Rechazar arranque si `SECRET_KEY` no está definida (sin fallback) | P1 | H-002 | Bajo | Alto |
| QW-03 | Rechazar arranque en producción si falta `DB_HOST` | P1 | H-003 | Bajo | Alto |
| QW-04 | Documentar variables requeridas en `.env.production.example` | P2 | H-004, H-006, H-011 | Bajo | Medio |
| QW-05 | Añadir warning o error en `DEBUG=True` + producción | P2 | H-010 | Bajo | Medio |

---

## Sprint 1 — Controles críticos de seguridad y calidad (1-2 días)

**Objetivo:** Cerrar los riesgos que permiten introducir cambios sin revisión o ejecutar con configuraciones inseguras.

- [ ] **H-001**: Configurar branch protection real en `release/v1.0-local` y `main` sin bypass para usuarios automatizados. Usar PRs con required status checks.
- [ ] **H-002**: Eliminar fallback de `SECRET_KEY`; lanzar `RuntimeError` si no está definida en cualquier entorno. Documentar comando de generación.
- [ ] **H-003**: En producción, lanzar `RuntimeError` si `DB_HOST` no está configurado.
- [ ] **H-004**: Convertir advertencia de tokens faltantes en error crítico en producción (o documentar explícitamente en checklist de deploy).
- [ ] **H-005**: Configurar base de datos de prueba y asegurar que `python manage.py test` finalice en < 5 min en CI.
- [ ] Validar que todos los workflows de CI pasen verdes con la nueva configuración.

---

## Sprint 2 — Endurecimiento de entorno de producción (2-3 días)

**Objetivo:** Asegurar que las variables y headers de seguridad estén configurados correctamente en producción.

- [ ] **H-006**: Establecer `SECURE_SSL_REDIRECT=True` por defecto en producción, permitiendo override explícito.
- [ ] **H-011**: Definir `CORS_ALLOWED_ORIGINS` en `.env.production.example` y validar en deploy.
- [ ] **H-012**: Restringir `/metrics/` a red interna o añadir token de scraping.
- [ ] Configurar `GITLEAKS_LICENSE` y validar workflow de secret scanning.
- [ ] Revisar y aplicar secrets de deploy (`DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`).
- [ ] Ejecutar smoke tests post-deploy y validar monitoreo.

---

## Sprint 3 — Dependencias y deuda técnica (2-3 días)

**Objetivo:** Actualizar dependencias críticas y establecer métricas de calidad.

- [ ] **H-007**: Revisar y mergear PRs de Dependabot: Pillow (#13), google-genai (#35), gitleaks-action, upload-artifact.
- [ ] **H-009**: Instalar y configurar `radon`, `lizard`, `jscpd` en CI.
- [ ] Añadir thresholds de complejidad ciclomática (ej. `radon cc --average -nb`) al quality gate.
- [ ] Generar y publicar SBOM en cada release.
- [ ] Revisar y consolidar middlewares custom si es posible (H-013).

---

## Sprint 4 — Validación funcional y E2E (3-5 días)

**Objetivo:** Validar que los flujos críticos funcionen en staging y producción.

- [ ] Ejecutar suite de tests completa en CI y alcanzar cobertura objetivo (definir meta mínima).
- [ ] Validar flujos E2E críticos: recepción de orden, captura de resultados, generación de PDF, cobro, facturación, portal paciente.
- [ ] Pruebas de carga y validación de SLOs (latencia p95, error rate, uptime).
- [ ] Validar aislamiento tenant entre empresas en todos los endpoints críticos.
- [ ] Revisar accesibilidad y consistencia de UX/UI en flujos principales.

---

## Cambios críticos / bloqueantes

- Branch protection real sin bypass.
- `SECRET_KEY` y `DB_HOST` obligatorios en producción.
- Suite de tests ejecutable y verde en CI.
- Dependencias críticas actualizadas.

## Cambios recomendados

- Restringir `/metrics/`.
- Consolidar middlewares custom.
- Mejorar logs de auditoría de acceso a expedientes.
- Documentar todos los flujos E2E críticos.

## Cambios opcionales

- Añadir métricas de negocio a Prometheus.
- Implementar rate limiting también a nivel Nginx.
- Automatizar generación de ADRs para cambios futuros.

---

## Cronograma sugerido

| Semana | Sprint | Entregable |
|--------|--------|------------|
| 1 | Sprint 1 | Branch protection, SECRET_KEY, DB_HOST, tests en CI |
| 2 | Sprint 2 | SSL/CORS, métricas protegidas, deploy validado |
| 3 | Sprint 3 | Dependencias actualizadas, métricas de calidad |
| 4 | Sprint 4 | E2E validado, staging listo para go-live |

---

## Definición de terminado (DoD) de remediación

- [ ] Todos los hallazgos P1 cerrados con evidencia.
- [ ] CI verde en `release/v1.0-local`.
- [ ] Deploy a staging exitoso con smoke tests.
- [ ] Monitoreo consume métricas sin errores.
- [ ] Ningún secreto expuesto en el repositorio (validado por gitleaks).
- [ ] Roadmap actualizado y aprobado por stakeholders.
