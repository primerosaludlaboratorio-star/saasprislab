# MANIFIESTO DE AUDITORÍA

## Identificador global de auditoría

**AUD-20260713-210000**

---

## Estado del repositorio

| Campo | Valor |
|-------|-------|
| Proyecto | PRISLAB SaaS (Django) |
| Rama auditada | `release/v1.0-local` |
| Commit SHA | `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5` |
| Fecha/hora inicio | 2026-07-13 21:00:00 UTC-06:00 |
| Duración estimada | En progreso |
| Idioma de salida | Español |

---

## Entorno de auditoría

| Componente | Valor detectado |
|------------|-----------------|
| Sistema operativo | Microsoft Windows 11 Home Single Language (Build 10.0.26200) |
| Procesador | AMD Ryzen 7 7735HS with Radeon Graphics |
| Python | 3.14.0 |
| Django | 5.1.15 |
| Node.js | v22.21.1 |
| npm | 10.9.4 |
| Git | 2.53.0.windows.1 |
| Docker | **No disponible** en este entorno |
| pytest | 7.4.3 |
| Base de datos local | **No configurada** — sin PostgreSQL accesible localmente |
| Redis | **No verificado** — no hay servidor local |

---

## Variables de entorno detectadas (solo nombres)

Ninguna variable relacionada con PRISLAB/DJANGO/DATABASE/SECRET/REDIS fue detectada en el entorno de ejecución de esta auditoría.
Esto implica que la aplicación no puede arrancar con la configuración real sin cargar un archivo `.env`.

> **Impacto:** Funciones que requieren base de datos, Redis, servicios externos (facturación, IA, correo) se marcarán como **NO EJECUTABLE EN ESTE ENTORNO**.

---

## Herramientas disponibles/ausentes

| Herramienta | Estado | Notas |
|-------------|--------|-------|
| Python + pip | Disponible | Versión 3.14.0 |
| pytest | Disponible | 7.4.3 |
| git | Disponible | 2.53.0.windows.1 |
| Node + npm | Disponible | v22.21.1 / 10.9.4 |
| Docker | Ausente | No se puede levantar stack local |
| PostgreSQL client/server | Ausente | No se puede ejecutar BD real |
| Redis server | Ausente | No se puede validar caché |
| radon | Ausente | Métricas de complejidad NO VERIFICABLES |
| lizard | Ausente | Métricas de complejidad NO VERIFICABLES |
| jscpd | Ausente | Detección de duplicidad NO VERIFICABLE |
| pip-audit | No verificado | Requiere ejecución manual |
| gitleaks CLI | No verificado | Workflow validado en CI |

---

## Limitaciones del entorno

1. **Sin Docker:** No se puede levantar el stack completo (app, PostgreSQL, Redis, Nginx, monitoreo).
2. **Sin base de datos:** No se pueden ejecutar migraciones, tests que requieran BD, ni validar integridad referencial.
3. **Sin variables reales:** No se puede probar autenticación con proveedores externos ni envío de correos.
4. **Herramientas de métricas ausentes:** Complejidad ciclomática, duplicidad y deuda técnica quedan como **NO VERIFICABLES** por este entorno; se documentarán como tales.
5. **Solo lectura/análisis estático:** La auditoría se basa en revisión de código y ejecución limitada de comandos que no requieran servicios externos.

---

## Reglas de alcance aplicadas

- **Contexto aislado:** Solo PRISLAB SaaS. Cualquier referencia a "Imperium" u otro proyecto se reportará como hallazgo crítico.
- **Exclusiones:**
  - `node_modules/`
  - `site-packages/` / entornos virtuales
  - `vendor/`
  - Migraciones 100% autogeneradas sin modificación manual
  - Archivos estáticos generados por frameworks
  - Estos aparecerán en inventario como `vendor/no auditado` con justificación.
- **Nomenclatura congelada:** Se usan exactamente los nombres de módulos, clases, funciones y modelos que aparecen en el código. No se renombra.
- **Prioridad de troceo:**
  1. Autenticación/permisos/seguridad
  2. Base de datos y modelos
  3. API críticos (laboratorio, farmacia)
  4. Backend restante
  5. Frontend
  6. IA/MCA
  7. Infra/CI-CD
  8. UX/UI y resto

---

## Estructura de entrega

```
audit/
├── 000_MANIFEST.md
├── 00_INDICE.md
├── 01_backend/
├── 02_frontend/
├── 03_db/
├── 04_api/
├── 05_pruebas/
├── 06_seguridad/
├── 07_infra/
├── 08_ia/
├── 09_metricas/
├── 10_hallazgos/
├── 11_conclusiones.md
└── 12_roadmap.md
```

---

## Responsables simulados

| Rol | Responsabilidad |
|-----|-----------------|
| Arquitecto Senior | Validación de patrones y decisiones de diseño |
| Staff Engineer | Revisión de calidad de código y escalabilidad |
| Auditor de Código | Revisión línea a línea y evidencias |
| QA Lead | Pruebas, cobertura y criterios de aceptación |
| DevOps | Infraestructura, CI/CD, monitoreo y despliegue |
| Security Engineer | Autenticación, autorización, secretos y vulnerabilidades |
| DB Architect | Modelo de datos, integridad y migraciones |
| UX/UI | Experiencia de usuario, navegación y consistencia visual |

---

## Notas iniciales

- Esta auditoría se realiza sobre el commit `2b6e983` de la rama `release/v1.0-local`.
- El proyecto se encuentra en fase de cierre de migración SaaS con trabajo reciente de:
  - **Editor 1 (Cascade):** infraestructura, CI/CD, monitoreo, seguridad/SDLC, ADRs.
  - **Editor 2 (Antigravity):** migración funcional P0, governance, RBAC, load testing.
- Se espera que esta auditoría produzca un listado completo de hallazgos priorizados y un roadmap de remediación.
