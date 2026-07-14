# Hallazgos y Riesgos — PRISLAB SaaS

**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## H-001 — Branch protection bypass en `release/v1.0-local`

| Atributo | Valor |
|------------|-------|
| **Hecho** | Los pushes directos a `release/v1.0-local` muestran `Bypassed rule violations ... Changes must be made through a pull request.` |
| **Evidencia** | EV-SEC-006 |
| **Impacto** | Crítico |
| **Probabilidad** | Alta |
| **Esfuerzo** | Bajo |
| **Riesgo resultante** | Cambios pueden llegar a la rama release sin revisión ni status checks, introduciendo regresiones o fallos de seguridad. |
| **Prioridad** | P1 |
| **Recomendación** | Configurar branch protection real sin bypass para usuarios automatizados; usar PRs con required status checks. Si se requiere deploy automático, usar un bot dedicado sin permisos de bypass. |

---

## H-002 — Fallback de SECRET_KEY hardcodeado

| Atributo | Valor |
|------------|-------|
| **Hecho** | `config/settings.py` contiene una clave fallback literal para desarrollo. |
| **Evidencia** | EV-SEC-001 |
| **Impacto** | Alto |
| **Probabilidad** | Media |
| **Esfuerzo** | Bajo |
| **Riesgo resultante** | Si por error se desactivan las validaciones de producción o se usa `DEBUG=True`, la clave queda expuesta. Además, cualquier clave en el repo es visible para todos los colaboradores. |
| **Prioridad** | P1 |
| **Recomendación** | Rechazar el arranque en cualquier entorno si `SECRET_KEY` no está definida, eliminando el fallback. Documentar el comando para generarla en `README.md` y `.env.example`. |

---

## H-003 — Fallback silencioso a SQLite si falta DB_HOST

| Atributo | Valor |
|------------|-------|
| **Hecho** | Si `DB_HOST` no está definido, el sistema usa SQLite sin advertencia. |
| **Evidencia** | EV-DB-003 |
| **Impacto** | Alto |
| **Probabilidad** | Media |
| **Esfuerzo** | Bajo |
| **Riesgo resultante** | En producción sin `DB_HOST` configurado se usaría SQLite, causando corrupción de datos y pérdida de integridad. |
| **Prioridad** | P1 |
| **Recomendación** | En producción (`IS_PRODUCTION=True`), lanzar `RuntimeError` si `DB_HOST` no está configurado. Mantener SQLite solo para `development`/`test`. |

---

## H-004 — Tokens de servicio solo generan warning al arrancar

| Atributo | Valor |
|------------|-------|
| **Hecho** | `PRISLAB_API_TOKEN`, `PRISLAB_FRONTEND_LOG_TOKEN`, `CRON_SECRET` faltantes emiten warning pero no bloquean el arranque. |
| **Evidencia** | EV-SEC-002 |
| **Impacto** | Alto |
| **Probabilidad** | Media |
| **Esfuerzo** | Bajo |
| **Riesgo resultante** | Endpoints que dependen de estos tokens retornarán 503 sin que el administrador se entere si no revisa logs. |
| **Prioridad** | P2 |
| **Recomendación** | Convertir en error crítico en producción o, al menos, documentar claramente en checklists de deploy. |

---

## H-005 — Suite de tests no ejecutable en entorno de auditoría

| Atributo | Valor |
|------------|-------|
| **Hecho** | `python manage.py test core lims` no finalizó en tiempo razonable (terminado tras ~90s). |
| **Evidencia** | EV-TEST-002 |
| **Impacto** | Alto |
| **Probabilidad** | Alta |
| **Esfuerzo** | Medio |
| **Riesgo resultante** | No se pudo validar regresión funcional localmente. Bugs pueden pasar a staging/producción sin detección. |
| **Prioridad** | P1 |
| **Recomendación** | Configurar base de datos de prueba PostgreSQL o SQLite en memoria; asegurar que la suite corra en < 5 min en CI. |

---

## H-006 — `SECURE_SSL_REDIRECT` desactivado por defecto

| Atributo | Valor |
|------------|-------|
| **Hecho** | `SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', False)`. |
| **Evidencia** | EV-SEC-005, EV-TEST-001 |
| **Impacto** | Medio |
| **Probabilidad** | Media |
| **Esfuerzo** | Bajo |
| **Riesgo resultante** | Si Nginx no fuerza HTTPS, las peticiones HTTP pueden ser atendidas por Django. |
| **Prioridad** | P2 |
| **Recomendación** | Usar `True` por defecto en producción, permitiendo override explícito. |

---

## H-007 — Dependencias desactualizadas (Dependabot)

| Atributo | Valor |
|------------|-------|
| **Hecho** | PRs pendientes: Pillow (#13), google-genai (#35), gitleaks-action, upload-artifact. |
| **Evidencia** | EV-SEC-009 |
| **Impacto** | Medio |
| **Probabilidad** | Media |
| **Esfuerzo** | Medio |
| **Riesgo resultante** | Vulnerabilidades conocidas en librerías de procesamiento de imágenes (PDFs) e integración IA. |
| **Prioridad** | P2 |
| **Recomendación** | Revisar y mergear PRs de seguridad críticos después de validar tests. Mantener SBOM actualizado. |

---

## H-008 — Docker no disponible en entorno local de auditoría

| Atributo | Valor |
|------------|-------|
| **Hecho** | Docker no está instalado en la máquina de auditoría. |
| **Evidencia** | EV-INF-008, EV-TEST-005 |
| **Impacto** | Medio |
| **Probabilidad** | Alta |
| **Esfuerzo** | Bajo |
| **Riesgo resultante** | No se puede levantar el stack completo ni validar monitoreo, despliegue y health checks localmente. |
| **Prioridad** | P2 |
| **Recomendación** | Instalar Docker Desktop o usar una VM/remoto para auditorías futuras. Documentar requisitos en `docs/ENTORNOS_PRISLAB.md`. |

---

## H-009 — Métricas de complejidad no verificables

| Atributo | Valor |
|------------|-------|
| **Hecho** | `radon`, `lizard`, `jscpd` no están instalados. |
| **Evidencia** | EV-TEST-005 |
| **Impacto** | Medio |
| **Probabilidad** | Alta |
| **Esfuerzo** | Bajo |
| **Riesgo resultante** | No se identifican hotspots de complejidad ni duplicidad de código. |
| **Prioridad** | P3 |
| **Recomendación** | Añadir herramientas al entorno de CI y ejecutar periódicamente. Incluir thresholds de radon cc en quality gate. |

---

## H-010 — Validador de SECRET_KEY puede evadirse si `DEBUG=True`

| Atributo | Valor |
|------------|-------|
| **Hecho** | Las validaciones de SECRET_KEY solo se ejecutan si `IS_PRODUCTION=True`. |
| **Evidencia** | EV-SEC-001 |
| **Impacto** | Medio |
| **Probabilidad** | Baja |
| **Esfuerzo** | Bajo |
| **Riesgo resultante** | Un deploy con `DEBUG=True` en producción no alertaría sobre SECRET_KEY inseguro. |
| **Prioridad** | P2 |
| **Recomendación** | Considerar advertencia también cuando `DEBUG=True`, o usar un validador de arranque independiente del modo. |

---

## H-011 — CORS sin orígenes en producción

| Atributo | Valor |
|------------|-------|
| **Hecho** | Si `CORS_ALLOWED_ORIGINS` no está configurado en producción, solo se emite warning. |
| **Evidencia** | EV-SEC-003 |
| **Impacto** | Medio |
| **Probabilidad** | Media |
| **Esfuerzo** | Bajo |
| **Riesgo resultante** | Peticiones cross-origin legítimas fallarán. No es un riesgo de seguridad directo, pero afecta funcionalidad. |
| **Prioridad** | P3 |
| **Recomendación** | Documentar dominios permitidos en `.env.production.example` y validar en deploy. |

---

## H-012 — Posible riesgo en exposición de `/metrics/`

| Atributo | Valor |
|------------|-------|
| **Hecho** | El endpoint `/metrics/` está expuesto sin autenticación aparente. |
| **Evidencia** | EV-INF-004 |
| **Impacto** | Bajo |
| **Probabilidad** | Baja |
| **Esfuerzo** | Bajo |
| **Riesgo resultante** | Fuga de métricas internas (latencias, contadores) si la URL es accesible desde internet. |
| **Prioridad** | P3 |
| **Recomendación** | Restringir `/metrics/` a redes internas o añadir token de scraping en middleware. |

---

## H-013 — Gran cantidad de middleware custom

| Atributo | Valor |
|------------|-------|
| **Hecho** | `MIDDLEWARE` incluye ~15 middlewares propios. |
| **Evidencia** | EV-SEC-004 |
| **Impacto** | Medio |
| **Probabilidad** | Media |
| **Esfuerzo** | Medio |
| **Riesgo resultante** | Cada middleware es un punto de fallo, latencia y potencial bypass de seguridad. Difícil de auditar completamente. |
| **Prioridad** | P3 |
| **Recomendación** | Documentar responsabilidad de cada middleware, medir impacto en latencia, y considerar consolidar funciones similares. |

---

## Resumen por criticidad

| Criticidad | Cantidad | Hallazgos |
|------------|----------|-----------|
| CRÍTICA | 1 | H-001 |
| ALTA | 4 | H-002, H-003, H-004, H-005 |
| MEDIA | 6 | H-006, H-007, H-008, H-009, H-010, H-011 |
| BAJA | 2 | H-012, H-013 |

---

## Resumen por prioridad

| Prioridad | Cantidad | Hallazgos |
|-----------|----------|-----------|
| P1 | 3 | H-001, H-002, H-003, H-005 |
| P2 | 4 | H-004, H-006, H-007, H-008, H-010 |
| P3 | 4 | H-009, H-011, H-012, H-013 |

> Nota: H-005 se mantiene como P1 porque bloquea la validación funcional.
