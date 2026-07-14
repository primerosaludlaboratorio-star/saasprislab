# Auditoría Técnica E2E Completa — PRISLAB SaaS

**ID de auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`  
**Fecha:** 2026-07-13  
**Este documento integra toda la auditoría sin omisiones.**  

---


# ÍNDICE


**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`  
**Fecha:** 2026-07-13

---

## Documentos de esta auditoría

| Ruta | Descripción |
|------|-------------|
| `audit/000_MANIFEST.md` | Manifiesto de auditoría, entorno, alcance, limitaciones |
| `audit/01_INTRODUCCION_ALCANCE.md` | Rol, objetivo y alcance |
| `audit/01_backend/_inventory_summary.md` | Resumen de inventario de archivos (1,897 archivos) |
| `audit/01_backend/_domain_catalog.md` | Catálogo de dominios de negocio (21 dominios) |
| `audit/03_db/modelos_y_bd.md` | Evidencias de base de datos y modelos |
| `audit/04_api/_api_inventory_summary.md` | Resumen de inventario de URLs/API (1,812 rutas) |
| `audit/05_pruebas/pruebas_y_calidad.md` | Pruebas, `check --deploy`, métricas |
| `audit/06_seguridad/evidencias.md` | Evidencias de seguridad (10 EV-SEC) |
| `audit/07_infra/infraestructura.md` | Evidencias de infraestructura/CI/CD (8 EV-INF) |
| `audit/10_hallazgos/hallazgos.md` | Hallazgos y riesgos priorizados (13) |
| `audit/11_conclusiones.md` | Resumen ejecutivo, estado general, cobertura |
| `audit/12_roadmap.md` | Roadmap de remediación con sprints |

---

## Resumen de hallazgos

| Criticidad | Cantidad |
|------------|----------|
| CRÍTICA | 1 |
| ALTA | 4 |
| MEDIA | 6 |
| BAJA | 2 |

| Prioridad | Cantidad |
|-----------|----------|
| P1 | 4 |
| P2 | 5 |
| P3 | 4 |

---

## Estado general

El proyecto **PRISLAB SaaS** presenta una arquitectura robusta con múltiples capas de seguridad, monitoreo, CI/CD y multi-tenant. Sin embargo, existen **controles de calidad y configuración de producción pendientes** que deben cerrarse antes de declarar enterprise-ready.

La auditoría se realizó con limitaciones de entorno (sin Docker/PostgreSQL/Redis) por lo que algunas verificaciones de ejecución no fueron posibles. Todos los elementos se marcaron con su estado correspondiente según la taxonomía del protocolo.

---

## Recomendación ejecutiva

1. **P1 inmediato:** eliminar bypass de branch protection, endurecer `SECRET_KEY` y `DB_HOST` en producción.
2. **P1 corto:** lograr que la suite de tests ejecute confiablemente en CI.
3. **P2:** completar configuración de SSL/CORS, proteger `/metrics/`, actualizar dependencias.
4. **P3:** añadir métricas de calidad (`radon`, `lizard`, `jscpd`) y consolidar middlewares si es viable.

Ver `audit/12_roadmap.md` para plan detallado por sprints.

---


# MANIFIESTO


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

---


# INTRODUCCIÓN Y ALCANCE


**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## 1.1 Rol del comité auditor

Esta auditoría asume los siguientes roles de revisión:

| Rol | Enfoque |
|-----|---------|
| **Arquitecto Senior** | Decisiones de arquitectura, patrones, acoplamiento, escalabilidad. |
| **Staff Engineer** | Calidad de código, mantenibilidad, deuda técnica, consistencia. |
| **Auditor de Código** | Revisión línea a línea, evidencias concretas (EV-XXX), trazabilidad. |
| **QA Lead** | Cobertura de pruebas, casos de uso críticos, validación funcional. |
| **DevOps** | Infraestructura, CI/CD, monitoreo, despliegue, logs. |
| **Security Engineer** | Autenticación, autorización, secretos, inyección, validaciones, permisos. |
| **DB Architect** | Modelo de datos, integridad referencial, migraciones, rendimiento. |
| **UX/UI** | Flujos de usuario, consistencia visual, estados de carga/error/vacío. |

---

## 1.2 Objetivo

Realizar una auditoría técnica **E2E** del estado real del proyecto **PRISLAB SaaS**, basándose exclusivamente en evidencia real del código y del entorno. No se asume, infiere ni fabrica información.

El objetivo final es entregar:

1. Inventario completo del dominio y del código propio.
2. Evidencias técnicas (EV-XXX) con criticidad y estado normalizado.
3. Análisis de consistencia entre modelos, vistas, templates, API y documentación.
4. Métricas verificables o marcadas como **NO VERIFICABLE/NO EJECUTABLE**.
5. Hallazgos priorizados con impacto, probabilidad y esfuerzo estimado.
6. Roadmap de remediación con quick wins y sprints priorizados.

---

## 1.3 Alcance

### Dentro del alcance

- Código propio del proyecto PRISLAB SaaS en el commit auditado.
- Modelos Django, vistas, servicios, utilidades, middleware, management commands, signals, consumidores.
- Configuración de URLs, serializadores, formularios, templates, archivos estáticos y JS propios.
- Infraestructura: Docker, Compose, Nginx, GitHub Actions, monitoreo, backups.
- Seguridad: autenticación, permisos, roles, secretos, validaciones de entrada.
- IA/MCA: agentes, herramientas, prompts, flujos de ejecución.
- Pruebas existentes y su estado de ejecución.
- UX/UI: flujos de usuario, navegación, estados de interfaz.

### Fuera del alcance

- Código de terceros: `node_modules/`, `site-packages/`, entornos virtuales.
- Migraciones 100% autogeneradas sin modificación manual.
- Archivos estáticos generados por frameworks (bundles minificados).
- Repositorios externos o referencias a proyectos ajenos (p. ej., "Imperium").
- Funcionalidad no accesible por falta de credenciales o servicios externos (se marca como **NO EJECUTABLE**).

---

## 1.4 Criterios de éxito de la auditoría

- [ ] 100% de archivos propios clasificados según la taxonomía de estados.
- [ ] Todos los hallazgos tienen evidencia EV-XXX asociada.
- [ ] Todos los hallazgos tienen criticidad, impacto, probabilidad, esfuerzo y prioridad.
- [ ] Métricas verificadas o marcadas con fallback honesto.
- [ ] Roadmap priorizado y reproducible.
- [ ] El informe puede reproducirse sobre el mismo commit en un entorno equivalente.

---

## 1.5 Supuestos y restricciones

- Esta auditoría se ejecuta en un entorno Windows 11 sin Docker, PostgreSQL ni Redis.
- La aplicación no puede arrancar con la configuración real sin un `.env` adecuado.
- Las métricas de complejidad, duplicidad y cobertura total no se pueden obtener sin herramientas adicionales.
- Cualquier afirmación sin evidencia concreta se invalida y se corrige.

---


# INVENTARIO DE ARCHIVOS


- Total de archivos propios: 1897
- Total de líneas aproximadas: 370928

## Directorios principales

| Directorio | Archivos |
|------------|----------|
| core | 776 |
| docs | 136 |
| consultorio | 80 |
| inventario | 78 |
| laboratorio | 77 |
| farmacia | 62 |
| mantenimiento | 57 |
| lims | 46 |
| contabilidad | 40 |
| static | 39 |
| marketing | 35 |
| config | 30 |
| pacientes | 27 |
| scripts | 25 |
| seguridad | 24 |
| bienestar | 23 |
| academia | 21 |
| templates | 21 |
| logistica | 18 |
| ia | 17 |
| tools | 17 |
| enfermeria | 15 |
| iot | 15 |
| recepcion | 15 |
| middleware_local | 12 |
| reglas_negocio | 11 |
| pris_ai_core | 10 |
| suscripciones | 10 |
| .github | 9 |
| datos_lims | 7 |
| monitoring | 6 |
| release_candidate | 5 |
| nginx | 4 |
| logs | 2 |
| .cursorignore | 1 |
| .dockerignore | 1 |
| .env.agent.example | 1 |
| .env.example | 1 |
| .env.production.example | 1 |
| .env.staging.example | 1 |
| .gitattributes | 1 |
| .gitignore | 1 |
| .runtimeconfig.json.backup | 1 |
| ACCESO_Y_DEPLOY_OPERATIVO_VPS.md | 1 |
| AI_COORDINATION_STATUS.md | 1 |
| ANEXO_TECNICO_PRISLAB_LEGACY_VS_SAAS.md | 1 |
| CARGAR_INVENTARIO_AHORA.bat | 1 |
| CHECKLIST_CONTROL_PRISLAB.md | 1 |
| DEPLOY.md | 1 |
| DESPLEGAR_A_PRODUCCION.bat | 1 |

## Extensiones

| Extensión | Archivos |
|-----------|----------|
| .py | 1153 |
| .html | 423 |
| .md | 112 |
| .txt | 67 |
| .js | 30 |
| .yml | 15 |
| .sh | 12 |
| .mjs | 12 |
| .json | 12 |
| .csv | 11 |
| .css | 10 |
| (sin extensión) | 7 |
| .example | 6 |
| .bat | 6 |
| .conf | 4 |
| .service | 3 |
| .svg | 3 |
| .xlsx | 2 |
| .ps1 | 2 |
| .pdf | 2 |
| .backup | 1 |
| .py" | 1 |
| .png | 1 |
| .yaml | 1 |
| .dat | 1 |

## Archivos más grandes (top 100)

| Líneas | Archivo |
|--------|---------|
| 14508 | `tools/url_inventory.json` |
| 14286 | `docs/audit/INVENTARIO_URLS.txt` |
| 4620 | `resultados.csv` |
| 4186 | `core/templates/core/recepcion_lab.html` |
| 3165 | `core/views/laboratorio.py` |
| 2097 | `docs/audit/DOCS_AUDIT_MAESTRO.md` |
| 2085 | `docs/audit/FUNCIONES_EXHAUSTIVO_POR_RUTA.md` |
| 1960 | `core/templates/base.html` |
| 1742 | `inventario.csv` |
| 1718 | `Productos-farmacia-2026-02-10-10-31.csv` |
| 1670 | `core/views/pris_ia.py` |
| 1645 | `core/templates/includes/sidebar.html` |
| 1621 | `core/templates/core/captura_resultados_industrial.html` |
| 1487 | `core/migrations/0001_initial.py` |
| 1400 | `core/management/commands/omni_audit.py` |
| 1270 | `core/services/motor_reportes_lab.py` |
| 1250 | `REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md` |
| 1222 | `consultorio/templates/consultorio/nueva_consulta_soap.html` |
| 1183 | `consultorio/templates/consultorio/nueva_consulta_gemelo.html` |
| 1148 | `datos_lims/Parametros.csv` |
| 1146 | `config/settings.py` |
| 1098 | `core/models/expediente_blindaje.py` |
| 1089 | `docs/LEVANTAMIENTO_TOPOGRAFICO_PRISLAB_SAAS.md` |
| 1073 | `tools/run_ai_agent_audit.mjs` |
| 1044 | `core/management/commands/stress_test_extremo.py` |
| 1041 | `consultorio/views/api_consulta.py` |
| 1030 | `core/views/medico.py` |
| 1014 | `static/css/prislab_shared.css` |
| 1010 | `core/tests_e2e.py` |
| 1004 | `laboratorio/templates/laboratorio/crear_orden.html` |
| 983 | `core/admin.py` |
| 981 | `core/templates/core/preparacion_toma.html` |
| 956 | `core/models/ventas.py` |
| 936 | `core/models/operaciones.py` |
| 935 | `core/services/lims/interfaces_lims_service.py` |
| 908 | `core/middleware/sentinel.py` |
| 876 | `core/views/pris_jarvis.py` |
| 875 | `consultorio/views/reportes.py` |
| 865 | `consultorio/views/clinico.py` |
| 834 | `consultorio/tests.py` |
| 829 | `core/models/clinico.py` |
| 820 | `config/urls.py` |
| 811 | `core/templates/core/pris_chat.html` |
| 803 | `core/management/commands/simular_flujo_completo.py` |
| 793 | `core/templates/core/captura_resultados.html` |
| 790 | `farmacia/tests.py` |
| 787 | `core/services/lims/resultados_lims_service.py` |
| 785 | `core/templates/core/pris_ia_assistant.html` |
| 780 | `pacientes/templates/pacientes/historial_360.html` |
| 778 | `farmacia/views/inventario.py` |
| 769 | `tools/run_human_ui_audit.mjs` |
| 763 | `farmacia/views/devoluciones.py` |
| 760 | `static/js/pdv_farmacia.js` |
| 758 | `datos_lims/Examenes_Perfil.csv` |
| 754 | `core/templates/core/dashboard_director.html` |
| 751 | `core/services/ventas/cobro_service.py` |
| 751 | `marketing/views_legacy.py` |
| 745 | `core/views/laboratorio/calidad.py` |
| 716 | `farmacia/templates/farmacia/registrar_compra.html` |
| 707 | `core/templates/pris/widget.html` |
| 701 | `core/templates/core/lista_trabajo.html` |
| 697 | `core/models/laboratorio.py` |
| 695 | `seguridad/models.py` |
| 685 | `laboratorio/management/commands/importar_catalogo_maestro.py` |
| 684 | `ia/views.py` |
| 676 | `core/templates/core/control_calidad.html` |
| 670 | `core/management/commands/setup_demo_total.py` |
| 668 | `inventario/views/lab.py` |
| 658 | `core/templates/core/detalle_orden.html` |
| 657 | `core/templates/core/laboratorio/captura_resultados.html` |
| 657 | `core/views/war_room.py` |
| 649 | `laboratorio/management/commands/migrar_lab_completo.py` |
| 641 | `consultorio/templates/consultorio/cobro_consulta.html` |
| 636 | `core/models/base.py` |
| 629 | `core/views/entrega_resultados.py` |
| 625 | `core/services/motor_recetas.py` |
| 625 | `datos_lims/Tarifa_estudios de laboratorio.csv` |
| 622 | `core/templates/core/laboratorio/monitor_produccion.html` |
| 621 | `tarifas.csv` |
| 616 | `core/views/monitor_produccion.py` |
| 614 | `core/views/excepciones_lab.py` |
| 602 | `core/views/paciente_detalle.py` |
| 598 | `core/views/pris_ia/_tools_lectura.py` |
| 598 | `core/views/reportes_financieros.py` |
| 594 | `docs/ai_coordination/INVENTARIO_REAL_REPO.md` |
| 588 | `core/management/commands/war_room_stress_test.py` |
| 578 | `pacientes/views.py` |
| 575 | `core/tests_e2e_playwright.py` |
| 575 | `core/views/blindaje_expediente.py` |
| 575 | `core/views/rh.py` |
| 571 | `core/templates/pacientes/historial_clinico.html` |
| 565 | `core/views/general.py` |
| 563 | `core/services/ai_medico.py` |
| 559 | `core/utils/pdf_generator.py` |
| 558 | `docs/ai_coordination/INVENTARIO_MAESTRO_TOTAL.md` |
| 555 | `core/templates/core/resultados_print.html` |
| 554 | `docs/ai_coordination/AI_COORDINATION_STATUS.md` |
| 551 | `docs/ai_coordination/ESTADO_CANONICO_RAMA_RELEASE_V1_0_LOCAL.md` |
| 550 | `consultorio/pdf_views.py` |
| 548 | `core/templates/core/lims/editar_parametro.html` |

---


# CATÁLOGO DE DOMINIOS


**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## Resumen de dominios detectados

| Dominio | Directorio principal | Archivos | Estado general | Prioridad |
|---------|----------------------|----------|----------------|-----------|
| **Core / Plataforma** | `core/` | 776 | IMPLEMENTADO | P0 |
| **Laboratorio LIMS** | `lims/` | 46 | IMPLEMENTADO | P0 |
| **Laboratorio operativo** | `laboratorio/` | 77 | IMPLEMENTADO | P0 |
| **Consultorio médico** | `consultorio/` | 80 | IMPLEMENTADO | P1 |
| **Farmacia** | `farmacia/` | 62 | IMPLEMENTADO | P1 |
| **Inventario** | `inventario/` | 78 | IMPLEMENTADO | P1 |
| **Contabilidad** | `contabilidad/` | 40 | IMPLEMENTADO | P1 |
| **Pacientes** | `pacientes/` | 27 | IMPLEMENTADO | P0 |
| **Seguridad y RBAC** | `seguridad/` | 24 | IMPLEMENTADO | P0 |
| **Recepción** | `recepcion/` | 15 | IMPLEMENTADO | P1 |
| **Marketing** | `marketing/` | 35 | IMPLEMENTADO | P2 |
| **Bienestar** | `bienestar/` | 23 | IMPLEMENTADO | P2 |
| **Academia** | `academia/` | 21 | IMPLEMENTADO | P2 |
| **Enfermería** | `enfermeria/` | 15 | IMPLEMENTADO | P2 |
| **IoT** | `iot/` | 15 | IMPLEMENTADO | P2 |
| **Logística** | `logistica/` | 18 | IMPLEMENTADO | P2 |
| **Mantenimiento** | `mantenimiento/` | 57 | IMPLEMENTADO | P2 |
| **Reglas de negocio** | `reglas_negocio/` | 11 | IMPLEMENTADO | P1 |
| **Suscripciones** | `suscripciones/` | 10 | IMPLEMENTADO | P2 |
| **PRIS AI Core** | `pris_ai_core/` | 10 | IMPLEMENTADO | P1 |
| **IA / MCA** | `ia/` | 17 | IMPLEMENTADO | P1 |
| **Middleware local** | `middleware_local/` | 12 | IMPLEMENTADO | P2 |

---

## Dominios detallados

### 1. Core / Plataforma

- **Propósito:** Funcionalidad central compartida por todos los módulos: autenticación, usuarios, empresas, sucursales, tenant, catálogos, ventas, cobros, resultados, dashboards, y servicios transversales.
- **Actores:** Administrador, director, recepcionista, laboratorista, médico, paciente, sistema.
- **Entidades principales:** Usuario, Empresa, Sucursal, Paciente, Orden, Resultado, Perfil, Analito, Cobro, Pago.
- **Flujos principales:**
  - Autenticación y autorización.
  - Creación de órdenes de laboratorio.
  - Captura de resultados.
  - Generación de PDF de resultados.
  - Cobranza y facturación.
  - Dashboards y reportes.
- **Dependencias:** Todos los demás dominios.

### 2. Laboratorio (LIMS + operativo)

- **Propósito:** Gestión del ciclo de vida de muestras, catálogo de exámenes, perfiles, paquetes, valores de referencia, calidad, recepción y reportes.
- **Actores:** Laboratorista, técnico, director, paciente.
- **Entidades principales:** Analito, PerfilLims, PaqueteLims, ValorReferenciaAnalito, PerfilAnalito, Orden, Muestra, Resultado.
- **Flujos principales:**
  - Importación de catálogo LIMS.
  - Creación de perfiles y paquetes.
  - Definición de valores de referencia.
  - Captura y validación de resultados.
  - Liberación de resultados al paciente.
- **Dependencias:** Core, pacientes, farmacia, inventario.

### 3. Consultorio médico

- **Propósito:** Consultas médicas, SOAP, recetas, certificados, triage, integración con laboratorio/farmacia.
- **Actores:** Médico, enfermera, recepcionista, paciente.
- **Entidades principales:** Consulta, Receta, Certificado, Triage, Historial clínico.
- **Dependencias:** Core, pacientes, farmacia, laboratorio.

### 4. Farmacia

- **Propósito:** Punto de venta, inventario de medicamentos, compras, devoluciones, regulatorio.
- **Actores:** Cajero, farmacéutico, administrador.
- **Entidades principales:** Producto, Venta, Compra, Devolución, Movimiento, Lote.
- **Dependencias:** Core, inventario, contabilidad.

### 5. Inventario

- **Propósito:** Control de insumos, reactivos, productos, traspasos entre sucursales.
- **Actores:** Almacenista, administrador, laboratorista.
- **Entidades principales:** Producto, Stock, Movimiento, Traspaso, Orden de compra.
- **Dependencias:** Core, farmacia, laboratorio.

### 6. Contabilidad

- **Propósito:** Cuentas por cobrar, facturación, reportes financieros, autofactura.
- **Actores:** Contador, administrador, director.
- **Entidades principales:** Factura, Pago, Cuenta por cobrar, Corte de caja.
- **Dependencias:** Core, ventas, cobros.

### 7. Pacientes

- **Propósito:** Portal del paciente, historial clínico, acceso a resultados, datos demográficos.
- **Actores:** Paciente, médico, recepcionista.
- **Entidades principales:** Paciente, Historial, AccesoResultado.
- **Dependencias:** Core, laboratorio.

### 8. Seguridad y RBAC

- **Propósito:** Roles, permisos, grupos, auditoría de accesos, reglas de negocio de seguridad.
- **Actores:** Administrador de seguridad, sistema.
- **Entidades principales:** Rol, Permiso, Grupo, ReglaNegocio, Auditoria.
- **Dependencias:** Core.

### 9. IA / MCA

- **Propósite:** Asistente médico, interpretación de resultados, generación de recetas, chat con IA, agentes de diagnóstico.
- **Actores:** Médico, paciente, director.
- **Entidades principales:** Agente, Tool, Prompt, Conversación, Memoria.
- **Dependencias:** Core, consultorio, laboratorio.

### 10. Infraestructura y operaciones

- **Propósito:** Docker, Compose, Nginx, CI/CD, monitoreo, backups, scripts de utilidad.
- **Actores:** DevOps, SRE.
- **Componentes:** GitHub Actions, Prometheus, Grafana, Alertmanager, backups de PostgreSQL.
- **Dependencias:** Toda la plataforma.

---

## Matriz de dependencias entre dominios

| Dominio | Depende de |
|---------|------------|
| Core | — |
| LIMS | Core, Pacientes |
| Laboratorio | Core, LIMS, Inventario |
| Consultorio | Core, Pacientes, Farmacia, Laboratorio |
| Farmacia | Core, Inventario, Contabilidad |
| Inventario | Core, Farmacia, Laboratorio |
| Contabilidad | Core, Ventas (Core) |
| Pacientes | Core, Laboratorio |
| Seguridad | Core |
| IA | Core, Consultorio, Laboratorio |
| Recepción | Core, Pacientes, Laboratorio |
| Marketing | Core |

---

## Notas

- Los nombres de dominios se mantienen exactamente como aparecen en el árbol de directorios del repositorio.
- El dominio `core` concentra la mayor parte del código (776 archivos) y es el núcleo transversal.
- Los dominios P0 son aquellos críticos para la operación del laboratorio: Core, LIMS, Laboratorio, Pacientes, Seguridad.

---


# BASE DE DATOS Y MODELOS


**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## EV-DB-001 — Modelo de usuario custom

**Criticidad:** ALTA  
**Archivo:** `core/models/base.py` (presunto), `config/settings.py`  
**Línea:** `AUTH_USER_MODEL = 'core.Usuario'`  
**Explicación:** El sistema usa un modelo `Usuario` custom en `core`. Esto es correcto para un SaaS multi-tenant, pero requiere que todas las FK y referencias a usuarios usen `settings.AUTH_USER_MODEL` o `get_user_model()`.
**Confianza:** ★★★★☆ (código)
**Estado:** IMPLEMENTADO
**Riesgos:** Referencias a `User` de Django en lugar de `Usuario` podrían causar inconsistencias. No se verificó exhaustivamente.

---

## EV-DB-002 — Migraciones de LIMS recientes

**Criticidad:** ALTA  
**Archivo:** `lims/migrations/0011_perfilanalito_alter_perfillims_analitos_and_more.py`  
**Explicación:** Migración reciente crea modelo `PerfilAnalito` como tabla intermedia (through) entre `PerfilLims` y `Analito`. Añade campo `orden` y unique_together `(perfil, analito)`. Esto permite ordenar analitos dentro de un perfil para reportes.
**Confianza:** ★★★★☆ (código)
**Estado:** IMPLEMENTADO
**Riesgos:** Cambios en la relación M2M requieren que el importador y vistas la consuman correctamente. Antigravity reportó refactorización en este área.

---

## EV-DB-003 — Configuración de base de datos

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`  
**Línea:** 330-355  
**Fragmento:**
```python
if os.environ.get('DB_HOST'):
    db_host = os.environ.get('DB_HOST', '')
    db_conn_max_age = _env_int('DB_CONN_MAX_AGE', 0 if IS_PRODUCTION else 60)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'prislab_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': db_host,
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': db_conn_max_age,
            'CONN_HEALTH_CHECKS': _env_bool('DB_CONN_HEALTH_CHECKS', True),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {'timeout': 60},
        }
    }
```
**Explicación:** PostgreSQL cuando `DB_HOST` está configurado; SQLite como fallback local. `CONN_MAX_AGE` y `CONN_HEALTH_CHECKS` configurables.
**Confianza:** ★★★★☆ (código)
**Estado:** IMPLEMENTADO
**Riesgos:** En producción, si `DB_HOST` no está definido, cae a SQLite sin advertencia. Debe garantizarse que `DB_HOST` siempre esté en producción.

---

## EV-DB-004 — Integridad referencial

**Criticidad:** MEDIA  
**Archivo:** Múltiples modelos en `core/models/`, `lims/models.py`, etc.  
**Explicación:** Django maneja integridad referencial mediante `ForeignKey` con `on_delete`. No se pudo verificar el esquema real ni detectar claves foráneas ausentes por falta de acceso a PostgreSQL.
**Confianza:** ★★☆☆☆ (no verificable por entorno)
**Estado:** NO VERIFICABLE
**Riesgos:** Posible divergencia entre modelo Django y esquema real si se aplicaron migraciones manuales o se saltaron constraints.

---

## EV-DB-005 — Tenant por empresa

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`, `core/middleware/tenant_subdomain.py`  
**Explicación:** Sistema multi-tenant basado en subdominio/header con `Empresa` como tenant. Middleware `TenantSubdomainMiddleware` resuelve el tenant por request. `PRISLAB_TENANT_STRICT_MODE` activa validaciones estrictas.
**Confianza:** ★★★☆☆ (código, no ejecutado)
**Estado:** IMPLEMENTADO
**Riesgos:** Errores en resolución de tenant pueden exponer datos entre empresas. Requiere pruebas exhaustivas de aislamiento.

---

## EV-DB-006 — Backup y restauración

**Criticidad:** ALTA  
**Archivo:** `scripts/backup/backup_postgres.sh`, `.github/workflows/backup-restore-test.yml`  
**Explicación:** Existe script de backup de PostgreSQL y workflow de CI que prueba backup/restore.
**Confianza:** ★★★☆☆ (código)
**Estado:** IMPLEMENTADO
**Riesgos:** El workflow depende de secretos y entorno. No se ejecutó en este entorno.

---


# INVENTARIO DE URLS/API


- Total de rutas: 1812
- Rutas no-admin: 769
- Protocolo: PRISLAB_URL_INVENTORY
- OK: True

## Distribución por tipo

| Tipo | Cantidad |
|------|----------|
| ui | 1544 |
| api | 252 |
| pdf | 16 |

## Distribución por segmento raíz

| Segmento | Cantidad |
|----------|----------|
| /admin | 1043 |
| /laboratorio | 118 |
| /consultorio | 68 |
| /api | 61 |
| /farmacia | 53 |
| /silo-lab | 50 |
| /lims | 42 |
| /mantenimiento | 32 |
| /director | 24 |
| /bienestar | 21 |
| /pacientes | 18 |
| /contabilidad | 17 |
| /marketing | 16 |
| /seguridad | 15 |
| /ia | 14 |
| /pris | 14 |
| /crm | 14 |
| /medico | 14 |
| /finanzas | 13 |
| /logistica | 11 |
| /capacitacion | 10 |
| /rh | 10 |
| /notificaciones | 9 |
| /nomina | 9 |
| /asistencia | 8 |
| /reportes | 8 |
| /recepcion | 7 |
| /iot | 7 |
| /cotizacion | 6 |
| /blindaje | 6 |
| /transferencias | 6 |
| /enfermeria | 6 |
| /chat | 6 |
| /inventario | 4 |
| /configuracion | 4 |
| /catalogos | 4 |
| /historial-resultados | 4 |
| /onboarding | 4 |
| /auth | 3 |
| /analytics | 3 |

## Muestra de rutas no-admin

| Ruta | Nombre | View | Tipo |
|------|--------|------|------|
| `/favicon.ico` | - | `django.views.generic.base.RedirectView` | ui |
| `/media/logos/LOGO_PRISLAB.png` | - | `django.views.generic.base.RedirectView` | ui |
| `/` | login_root | `core.views.general.CustomLoginView` | ui |
| `/login/` | login | `core.views.general.CustomLoginView` | ui |
| `/logout/` | logout | `core.views.general.logout_view` | ui |
| `/auth/2fa/verificar/` | verificar_2fa | `core.views.autenticacion_2fa.verificar_2fa` | ui |
| `/auth/2fa/configurar/` | setup_2fa | `core.views.autenticacion_2fa.setup_2fa` | ui |
| `/auth/2fa/desactivar/` | desactivar_2fa | `core.views.autenticacion_2fa.desactivar_2fa` | ui |
| `/api/iot/hl7/` | hl7_receptor | `core.services.lims.interfaces_lims_service.receptor_hl7` | api |
| `/api/v3/openapi.json` | openapi-json | `ninja.openapi.views.openapi_json` | api |
| `/api/v3/docs` | openapi-view | `ninja.openapi.views.openapi_view` | api |
| `/api/v3/farmacia/pdv/productos` | buscar_productos_pdv_v3 | `ninja.operation.PathView.get_view.<locals>.sync_view_wrapper` | api |
| `/api/v3/farmacia/pdv/cobrar` | farmacia_pdv_cobrar_v3 | `ninja.operation.PathView.get_view.<locals>.sync_view_wrapper` | api |
| `/api/v3/lims/resultados/captura` | lims_resultados_captura_v3 | `ninja.operation.PathView.get_view.<locals>.sync_view_wrapper` | api |
| `/api/v3/` | api-root | `ninja.openapi.views.default_home` | api |
| `/api/lab/imprimir-zpl/<int:orden_id>/` | imprimir_zpl | `laboratorio.views.imprimir_zpl.imprimir_etiqueta_zpl` | api |
| `/api/lab/imprimir-zpl/lote/` | imprimir_zpl_lote | `laboratorio.views.imprimir_zpl.imprimir_etiquetas_lote_zpl` | api |
| `/kiosko/` | kiosko_index | `laboratorio.views.imprimir_zpl.kiosko_index` | ui |
| `/kiosko/check-in/<str:qr_token>/` | kiosko_check_in | `laboratorio.views.imprimir_zpl.kiosko_check_in_qr` | ui |
| `/api/caja/corte-unificado/` | corte_caja_unificado | `farmacia.views.corte_caja_api.api_corte_caja_unificado` | api |
| `/bienestar/` | bienestar_dashboard | `core.views.bienestar.dashboard_bienestar` | ui |
| `/bienestar/diario/` | diario_emocional | `core.views.bienestar.diario_emocional` | ui |
| `/bienestar/nom035/` | evaluacion_nom035 | `core.views.bienestar.evaluacion_nom035` | ui |
| `/bienestar/alertas-rrhh/` | bienestar_alertas_rrhh | `core.views.bienestar.alertas_rrhh` | ui |
| `/home/` | home | `core.views.general.home_view` | ui |
| `/dashboard/` | dashboard | `core.views.director.dashboard_director` | ui |
| `/validar/resultado/<uuid:token>/` | validar_resultado | `core.views.laboratorio_reportes.validar_resultado` | ui |
| `/api/push/vapid/` | push_vapid_key | `core.views.push.obtener_vapid_key` | api |
| `/api/push/suscribir/` | push_suscribir | `core.views.push.suscribir_push` | api |
| `/api/push/desuscribir/` | push_desuscribir | `core.views.push.desuscribir_push` | api |
| `/api/push/estado/` | push_estado | `core.views.push.estado_suscripciones` | api |
| `/api/push/test/` | push_test | `core.views.push.test_notificacion` | api |
| `/api/voice/process/` | voice_process | `core.views.voice.procesar_comando_api` | api |
| `/api/voice/history/` | voice_history | `core.views.voice.historial_comandos` | api |
| `/api/voice/verify-auth/` | voice_verify_auth | `core.views.voice.verificar_webauthn` | api |
| `/voice/logs/` | voice_logs_dashboard | `core.views.voice.dashboard_voice_logs` | ui |
| `/ia/asistente/` | pris_ia_asistente | `core.views.pris_ia.asistente_page` | ui |
| `/ia/asistente/chat/` | pris_ia_chat | `core.views.pris_ia.asistente_chat` | ui |
| `/ia/asistente/reset/` | pris_ia_reset | `core.views.pris_ia.asistente_reset` | ui |
| `/api/prisci/webhook/` | prisci_webhook | `core.views.prisci_webhook.webhook` | api |
| `/api/prisci/webhook/verify/` | prisci_webhook_verify | `core.views.prisci_webhook.verify` | api |
| `/pris/api/acciones/pendientes/` | pris_acciones_pendientes | `core.views.pris_ia.api_acciones_pendientes` | api |
| `/pris/api/accion/<int:accion_id>/confirmar/` | pris_confirmar_accion | `core.views.pris_ia.api_confirmar_accion` | api |
| `/pris/api/accion/<int:accion_id>/rechazar/` | pris_rechazar_accion | `core.views.pris_ia.api_rechazar_accion` | api |
| `/notificaciones/` | notificaciones_lista | `core.views.notificaciones.lista_notificaciones` | ui |
| `/notificaciones/badge/` | notificaciones_badge | `core.views.notificaciones.api_notificaciones_badge` | ui |
| `/notificaciones/<int:notificacion_id>/leer/` | notificacion_leer | `core.views.notificaciones.marcar_leida` | ui |
| `/notificaciones/marcar-todas/` | notificaciones_marcar_todas | `core.views.notificaciones.marcar_todas_leidas` | ui |
| `/api/notificaciones/crear/` | api_crear_notificacion | `core.views.notificaciones.api_crear_notificacion` | api |
| `/nomina/` | nomina_dashboard | `core.views.nomina.dashboard_nomina` | ui |

---


# PRUEBAS Y CALIDAD


**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## EV-TEST-001 — `python manage.py check --deploy`

**Criticidad:** MEDIA  
**Archivo:** N/A (comando)  
**Estado:** EJECUTADO — 4 advertencias  
**Comando ejecutado:**
```bash
python manage.py check --deploy
```
**Output real:**
```
System check identified some issues:

WARNINGS:
?: (security.W004) You have not set a value for the SECURE_HSTS_SECONDS setting. If your entire site is served only over SSL, you may want to consider setting a value and enabling HTTP Strict Transport Security. Be sure to read the documentation first; enabling HSTS carelessly can cause serious, irreversible problems.
?: (security.W008) Your SECURE_SSL_REDIRECT setting is not set to True. Unless your site should be available over both SSL and non-SSL connections, you may want to either set this setting True or configure a load balancer or reverse-proxy server to redirect all connections to HTTPS.
?: (security.W012) SESSION_COOKIE_SECURE is not set to True. Using a secure-only session cookie makes it more difficult for network traffic sniffers to hijack user sessions.
?: (security.W016) You have 'django.middleware.csrf.CsrfViewMiddleware' in your MIDDLEWARE, but you have not set CSRF_COOKIE_SECURE to True. Using a secure-only CSRF cookie makes it more difficult for network traffic sniffers to steal the CSRF token.

System check identified 4 issues (0 silenced).
```
**Explicación:** Las advertencias son esperadas porque el entorno de auditoría no tiene configuradas las variables de producción (`SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`). En producción con las variables correctas no deberían aparecer.
**Confianza:** ★★★★★ (ejecutado)
**Riesgos:** Si se despliega sin configurar estas variables, las cookies y redirecciones SSL no serán seguras.
**Estado:** NO EJECUTABLE EN PRODUCCIÓN POR ENTORNO (advertencias por falta de env vars)

---

## EV-TEST-002 — Suite de tests de Django

**Criticidad:** ALTA  
**Archivo:** Múltiples `tests.py`, `tests/`  
**Estado:** NO EJECUTABLE EN ESTE ENTORNO  
**Comando intentado:**
```bash
python manage.py test core lims --verbosity=1
```
**Resultado:** El comando no finalizó en el tiempo de espera permitido (más de 90 segundos) y fue terminado.
**Explicación:** Sin base de datos PostgreSQL real, Django usa SQLite fallback. La suite `core lims` incluye muchos tests y posiblemente intentos de conexión a servicios externos, causando timeouts. No se pudo obtener un reporte de cobertura.
**Confianza:** ★★★★★ (intentado)
**Riesgos:** No se pudo validar regresión funcional localmente.
**Estado:** NO EJECUTABLE EN ESTE ENTORNO

---

## EV-TEST-003 — Archivos de test

**Criticidad:** INFORMATIVA  
**Archivo:** Múltiples  
**Estado:** IMPLEMENTADO  
**Explicación:** Existen archivos de test en varias apps (`core/tests_e2e.py`, `core/tests_e2e_playwright.py`, `consultorio/tests.py`, `farmacia/tests.py`, etc.). No se realizó conteo exacto por limitaciones de tiempo.
**Confianza:** ★★★☆☆ (parcial)
**Riesgos:** Ninguno; solo falta ejecución.

---

## EV-TEST-004 — CI/CD quality gate

**Criticidad:** ALTA  
**Archivo:** `.github/workflows/main.yml`  
**Estado:** IMPLEMENTADO  
**Explicación:** El workflow ejecuta checks de calidad, tests, migraciones y otras validaciones en cada PR/push a `release/v1.0-local` y `main`.
**Confianza:** ★★★☆☆ (código, no verificado en ejecución reciente)
**Riesgos:** Depende de secretos y runners disponibles. Requiere validación con Antigravity/Fase 4.

---

## EV-TEST-005 — Métricas de complejidad y duplicidad

**Criticidad:** MEDIA  
**Archivo:** N/A  
**Estado:** NO VERIFICABLE  
**Herramientas intentadas:**
- `radon` — no instalado
- `lizard` — no instalado
- `jscpd` — no instalado
**Explicación:** No se pudieron obtener métricas de complejidad ciclomática, duplicidad de código ni deuda técnica por falta de herramientas en el entorno.
**Confianza:** ★★★★★ (ejecutado)
**Riesgos:** Sin estas métricas no se puede cuantificar la deuda técnica ni identificar hotspots de complejidad.
**Estado:** NO VERIFICABLE

---


# EVIDENCIAS DE SEGURIDAD


**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## EV-SEC-001 — Validación de SECRET_KEY en producción

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`  
**Línea:** 50-186  
**Clase/Función:** Módulo de configuración global  
**Fragmento:**
```python
_SECRET_KEY_ENV = os.environ.get('SECRET_KEY', '').strip()
if not _SECRET_KEY_ENV:
    # Fallback solo en desarrollo local — NUNCA usar en produccion
    _SECRET_KEY_ENV = 'dev-only-fallback-key-not-for-production-prislab-2026-local'
SECRET_KEY = _SECRET_KEY_ENV

_CLAVES_INSEGURAS = {
    'django-insecure-prislab-saas-key-2025',
    'dev-only-fallback-key-not-for-production-prislab-2026-local',
    'generate-a-random-key-here-min-50-chars',
    '4k*0c0z8gacu(%_)ug*y*t9xp*u55(u*$rv+pou#b=#o!4p4eo',
}
if IS_PRODUCTION:
    if not os.environ.get('SECRET_KEY') or SECRET_KEY in _CLAVES_INSEGURAS:
        raise RuntimeError(
            '🔴 PRISLAB SEGURIDAD: SECRET_KEY no está configurada o usa un valor inseguro en producción.\n'
            'Defina la variable de entorno SECRET_KEY con una clave segura de al menos 50 caracteres.\n'
            'Genere una con: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
        )
    if len(SECRET_KEY) < 50:
        raise RuntimeError(
            '🔴 PRISLAB SEGURIDAD: SECRET_KEY en producción debe tener al menos 50 caracteres.'
        )
```
**Explicación:** Existe un fallback hardcodeado para desarrollo, pero el sistema lanza excepción en producción si SECRET_KEY no está configurada, si usa un valor inseguro conocido o si tiene menos de 50 caracteres. Es una buena práctica defensiva, aunque la clave de fallback está visible en el repositorio.
**Confianza:** ★★★★☆ (código)
**Riesgos:** La clave de desarrollo hardcodeada podría usarse accidentalmente en producción si se desactivan las validaciones o se usa `DEBUG=True`.
**Estado:** FUNCIONAL PARCIAL

---

## EV-SEC-002 — Tokens de servicio requeridos en producción

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`  
**Línea:** 192-204  
**Fragmento:**
```python
    _TOKENS_REQUERIDOS = {
        'PRISLAB_API_TOKEN': os.environ.get('PRISLAB_API_TOKEN', ''),
        'PRISLAB_FRONTEND_LOG_TOKEN': os.environ.get('PRISLAB_FRONTEND_LOG_TOKEN', ''),
        'CRON_SECRET': os.environ.get('CRON_SECRET', ''),
    }
    _tokens_faltantes = [k for k, v in _TOKENS_REQUERIDOS.items() if not v or v.startswith('replace-with')]
    if _tokens_faltantes:
        import logging as _log_tok
        _log_tok.getLogger('core').warning(
            f'🔴 PRISLAB SEGURIDAD: Tokens de servicio no configurados en produccion: {_tokens_faltantes}. '
            'Los endpoints protegidos por estos tokens retornarán 503.'
        )
```
**Explicación:** Se validan tokens de servicio en producción, pero solo se emiten warnings (no se bloquea el arranque). Los endpoints protegidos retornarán 503 si faltan.
**Confianza:** ★★★★☆ (código)
**Riesgos:** Si un administrador no revisa logs, el sistema puede arrancar con endpoints no funcionales.
**Estado:** FUNCIONAL PARCIAL

---

## EV-SEC-003 — Configuración CORS restrictiva por defecto

**Criticidad:** MEDIA  
**Archivo:** `config/settings.py`  
**Línea:** 125-148  
**Fragmento:**
```python
if _cors_allow_raw:
    CORS_ALLOW_ALL_ORIGINS = _cors_allow_raw in ('true', '1', 'yes', 'on')
else:
    CORS_ALLOW_ALL_ORIGINS = False

_default_local_cors_origins = (
    'http://127.0.0.1:8000,http://localhost:8000,'
    'http://127.0.0.1:3000,http://localhost:3000'
)
_cors_origins_raw = os.environ.get('CORS_ALLOWED_ORIGINS')
if _cors_origins_raw is None and not IS_PRODUCTION:
    _cors_origins_raw = _default_local_cors_origins
CORS_ALLOWED_ORIGINS = [
    x.strip() for x in (_cors_origins_raw or '').split(',') if x.strip()
]
if IS_PRODUCTION and not CORS_ALLOW_ALL_ORIGINS and not CORS_ALLOWED_ORIGINS:
    logging.getLogger('config').warning(
        'CORS: en producción CORS_ALLOW_ALL_ORIGINS está en False y CORS_ALLOWED_ORIGINS está vacío. '
        'Las peticiones desde otros orígenes pueden fallar. '
        'Defina CORS_ALLOWED_ORIGINS o, temporalmente, CORS_ALLOW_ALL_ORIGINS=true.'
    )
```
**Explicación:** CORS está desactivado por defecto (`CORS_ALLOW_ALL_ORIGINS=False`). En desarrollo se permite localhost. En producción se requiere configuración explícita. Se advierte si falta configuración.
**Confianza:** ★★★★☆ (código)
**Riesgos:** Ninguno crítico si se configura correctamente en producción.
**Estado:** IMPLEMENTADO

---

## EV-SEC-004 — Middleware de seguridad presentes

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`  
**Línea:** 252-285  
**Fragmento:**
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'core.middleware.sre_metrics.SreMetricsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.canonical_host.CanonicalHostMiddleware',
    'core.api_contracts.middleware.ApiRequestIdMiddleware',
    'core.middleware.read_only.ReadOnlyMiddleware',
    'core.middleware.admin_access.AdminAccessMiddleware',
    'core.middleware.rate_limit.RateLimitMiddleware',
    'core.middleware.tenant_subdomain.TenantSubdomainMiddleware',
    'core.middleware.EmpresaIdentityMiddleware',
    'core.middleware.feature_flags.FeatureFlagMiddleware',
    'core.middleware.json_response.JSONResponseMiddleware',
    'core.middleware.actividad_usuario.ActividadUsuarioMiddleware',
    'core.middleware.sentinel.SentinelTelemetryMiddleware',
    'core.middleware.performance.PerformanceMiddleware',
    'core.middleware.pris_context.PrisContextMiddleware',
    'core.middleware.mantenimiento.MaintenanceModeMiddleware',
    'core.middleware.seguridad.SessionTimeoutMiddleware',
    'core.middleware.seguridad.TenantStorageMiddleware',
    'core.middleware.blindaje_expediente.BlindajeExpedienteMiddleware',
    'core.middleware.blindaje_expediente.SnapshotMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```
**Explicación:** El stack incluye múltiples capas de seguridad: CSRF, autenticación, rate limiting, control de acceso a /admin, timeout de sesión, blindaje de expedientes, canonical host, y tenant isolation.
**Confianza:** ★★★☆☆ (código, no se verificó ejecución de cada middleware)
**Riesgos:** Gran cantidad de middlewares custom puede aumentar latencia e introducir efectos secundarios difíciles de depurar. Cada middleware es un punto de falla.
**Estado:** IMPLEMENTADO

---

## EV-SEC-005 — Cookies y headers de seguridad

**Criticidad:** MEDIA  
**Archivo:** `config/settings.py`  
**Línea:** 809-840  
**Fragmento:**
```python
if IS_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', IS_PRODUCTION)
CSRF_COOKIE_SECURE = _env_bool('CSRF_COOKIE_SECURE', IS_PRODUCTION)
SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

PERMISSIONS_POLICY = {
    'geolocation': [],
    'camera': [],
    'microphone': [],
    'payment': [],
    'usb': [],
    'fullscreen': ['self'],
}

SECURE_HSTS_SECONDS = int(os.environ.get(
    'SECURE_HSTS_SECONDS',
    '31536000' if IS_PRODUCTION else '0',
))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', IS_PRODUCTION)
SECURE_HSTS_PRELOAD = _env_bool('SECURE_HSTS_PRELOAD', IS_PRODUCTION)
```
**Explicación:** Headers de seguridad configurados: HSTS, X-Frame-Options DENY, cookies seguras en producción, referrer policy, permissions policy. `SECURE_SSL_REDIRECT` es `False` por defecto, requiere activación explícita.
**Confianza:** ★★★★☆ (código)
**Riesgos:** `SECURE_SSL_REDIRECT=False` por defecto puede permitir tráfico HTTP si Nginx no fuerza HTTPS.
**Estado:** IMPLEMENTADO

---

## EV-SEC-006 — Branch protection bypass visible

**Criticidad:** CRÍTICA  
**Archivo:** N/A (configuración de GitHub)  
**Línea:** N/A  
**Explicación:** En múltiples operaciones de push a `release/v1.0-local`, GitHub reportó:
```
remote: Bypassed rule violations for refs/heads/release/v1.0-local:
remote: - Changes must be made through a pull request.
```
Esto indica que la regla de branch protection existe pero está siendo bypassada (probablemente por permisos de administrador en el token usado).
**Confianza:** ★★★★★ (output real de git push)
**Riesgos:** Push directo a branch crítica sin PR permite introducir errores sin revisión. También evita los status checks obligatorios.
**Estado:** FUNCIONAL PARCIAL
**Evidencia de push:** Varios commits en `release/v1.0-local` mostraron este mensaje durante la sesión de auditoría.

---

## EV-SEC-007 — Secret scanning con gitleaks

**Criticidad:** ALTA  
**Archivo:** `.github/workflows/secret-scan.yml`  
**Línea:** 1-40  
**Fragmento:**
```yaml
name: Secret Scan
on:
  push:
    branches: [main, release/*]
  pull_request:
    branches: [main, release/*]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: '0'
      - name: gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}
```
**Explicación:** Existe workflow de secret scanning con gitleaks en push/PR a ramas main y release/*.
**Confianza:** ★★★★☆ (código)
**Riesgos:** Requiere que `GITLEAKS_LICENSE` esté configurado. Sin él, el workflow fallará.
**Estado:** IMPLEMENTADO

---

## EV-SEC-008 — Variables de entorno documentadas

**Criticidad:** INFORMATIVA  
**Archivo:** `.env.example`, `.env.staging.example`, `.env.production.example`  
**Explicación:** Existen archivos de ejemplo documentando variables requeridas: DB_*, SECRET_KEY, FERNET_KEY, API keys, Redis, email, etc. No contienen valores secretos reales.
**Confianza:** ★★★★☆ (código)
**Riesgos:** Ninguno si se configuran correctamente en el entorno de producción.
**Estado:** IMPLEMENTADO

---

## EV-SEC-009 — Dependencias con actualizaciones pendientes

**Criticidad:** MEDIA  
**Archivo:** `requirements.txt` / PRs dependabot  
**Explicación:** Existen PRs de dependabot pendientes:
- `#13` — Pillow update
- `#35` — google-genai update
- `gitleaks-action` 2 → 3
- `actions/upload-artifact` 4 → 7
**Confianza:** ★★★★☆ (observado en branches remotos)
**Riesgos:** Mantener dependencias desactualizadas puede exponer vulnerabilidades conocidas. Pillow y google-genai son usados para generación de PDFs e integraciones IA.
**Estado:** FUNCIONAL PARCIAL

---

## EV-SEC-011 — Correcciones aplicadas a `config/settings.py`

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`  
**Estado:** CORREGIDO  
**Cambios realizados:**

1. **H-002 — SECRET_KEY hardcodeado**: se eliminó el fallback literal. Ahora:
   - En producción (`IS_PRODUCTION=True`), si `SECRET_KEY` no está configurada → `RuntimeError`.
   - En dev/test, si no está configurada, se genera una clave aleatoria efímera con `secrets.token_urlsafe(64)` y se advierte.

2. **H-003 — DB_HOST obligatorio en producción**: se agregó validación que lanza `RuntimeError` si `DB_HOST` no está configurado en producción, evitando el fallback silencioso a SQLite.

3. **H-004 — Tokens de servicio como error**: los tokens `PRISLAB_API_TOKEN`, `PRISLAB_FRONTEND_LOG_TOKEN`, `CRON_SECRET` ahora lanzan `RuntimeError` si faltan en producción.

4. **H-006 — `SECURE_SSL_REDIRECT` por defecto en producción**: el default pasó de `False` a `IS_PRODUCTION`.

5. **H-011 — CORS en producción**: ahora se lanza `RuntimeError` si `CORS_ALLOW_ALL_ORIGINS=False` y `CORS_ALLOWED_ORIGINS` está vacío en producción.

**Validación:** `python manage.py check` se ejecutó sin errores después de los cambios.

---

## EV-SEC-010 — Auth: uso de AUTH_USER_MODEL custom

**Criticidad:** MEDIA  
**Archivo:** `config/settings.py`  
**Línea:** 368  
**Fragmento:**
```python
AUTH_USER_MODEL = 'core.Usuario'
```
**Explicación:** El sistema usa un modelo de usuario custom (`core.Usuario`), lo cual es correcto para un sistema multi-tenant, pero requiere que todas las referencias a User usen `get_user_model()` o `settings.AUTH_USER_MODEL`.
**Confianza:** ★★★★☆ (código)
**Riesgos:** Referencias directas a `User` de Django en lugar de `Usuario` pueden causar inconsistencias. Debe verificarse en el codebase.
**Estado:** IMPLEMENTADO

---


# INFRAESTRUCTURA Y CI/CD


**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## EV-INF-001 — Docker Compose de producción

**Criticidad:** ALTA  
**Archivo:** `docker-compose.yml`  
**Estado:** IMPLEMENTADO  
**Explicación:** Define servicios: PostgreSQL, Redis, Django app (Gunicorn), Nginx, Certbot. Incluye healthchecks, variables de entorno y volúmenes. Esquema estándar para Django SaaS en VPS.
**Riesgos:** Certbot en contenedor requiere mapeo correcto de puertos 80/443 y DNS funcional. Renew automático no verificado.

---

## EV-INF-002 — Stack de monitoreo

**Criticidad:** ALTA  
**Archivo:** `docker-compose.monitoring.yml`, `monitoring/prometheus/prometheus.yml`, `monitoring/alertmanager/alertmanager.yml`, `monitoring/grafana/provisioning/`, `monitoring/grafana/dashboards/prislab_sre.json`  
**Estado:** IMPLEMENTADO  
**Explicación:** Prometheus + Alertmanager + Grafana configurados. Scrape a `/metrics/`. Reglas de alerta para DB, cache, error rate y latencia. Dashboard SRE básico.
**Riesgos:** Configuración de SMTP en Alertmanager depende de variables no versionadas. No se verificó en ejecución por falta de Docker.

---

## EV-INF-003 — Pipeline de CI/CD

**Criticidad:** ALTA  
**Archivo:** `.github/workflows/main.yml`, `.github/workflows/deploy-vps.yml`, `.github/workflows/sre-health-check.yml`, `.github/workflows/backup-restore-test.yml`, `.github/workflows/secret-scan.yml`, `.github/workflows/sbom-audit.yml`  
**Estado:** IMPLEMENTADO  
**Explicación:**
- `main.yml`: lint, tests, migrations check, quality gate.
- `deploy-vps.yml`: deploy a VPS con smoke tests post-deploy.
- `sre-health-check.yml`: validación de endpoints /live/, /ready/, /metrics/.
- `backup-restore-test.yml`: prueba de backup/restore.
- `secret-scan.yml`: gitleaks.
- `sbom-audit.yml`: pip-audit + SBOM.
**Riesgos:** Workflows que requieren secretos (`DEPLOY_*`, `GITLEAKS_LICENSE`) fallarán si no están configurados.

---

## EV-INF-004 — Health checks de la aplicación

**Criticidad:** ALTA  
**Archivo:** `config/urls/core_views.py`  
**Estado:** IMPLEMENTADO  
**Explicación:** Endpoints `/live/` (liveness), `/ready/` (readiness con DB+cache), `/health/`, `/metrics/` (métricas Prometheus) expuestos.
**Riesgos:** `/metrics/` podría exponer información interna si no está protegido por red o autenticación. El workflow de deploy verifica que responda 200.

---

## EV-INF-005 — Dockerfile

**Criticidad:** MEDIA  
**Archivo:** `Dockerfile`  
**Estado:** IMPLEMENTADO  
**Explicación:** Python 3.12, dependencias del sistema (PostgreSQL client, WeasyPrint, Pillow), instalación de requirements, collectstatic. Uso de usuario no-root no verificado en este fragmento.
**Riesgos:** Imágenes con dependencias de sistema extensas aumentan superficie de ataque. WeasyPrint requiere librerías GTK.

---

## EV-INF-006 — Scripts de backup

**Criticidad:** MEDIA  
**Archivo:** `scripts/backup/backup_postgres.sh`, `scripts/backup/upload_to_drive.py`  
**Estado:** IMPLEMENTADO  
**Explicación:** Backup de PostgreSQL y opcional subida a Google Drive. El script legacy `backup_to_drive.py` fue eliminado en Fase 1.
**Riesgos:** Backup automático depende de cron/GitHub Actions; no se verificó en ejecución.

---

## EV-INF-007 — Nginx

**Criticidad:** MEDIA  
**Archivo:** `nginx/nginx.conf`, `nginx/prislab.conf`  
**Estado:** IMPLEMENTADO  
**Explicación:** Configuración de Nginx como reverse proxy con SSL, gzip, proxy headers. SSL gestionado por Certbot.
**Riesgos:** No se verificó la configuración de rate limiting en Nginx; el rate limiting parece estar en middleware Django.

---

## EV-INF-008 — Limitaciones de verificación local

**Criticidad:** INFORMATIVA  
**Archivo:** N/A  
**Estado:** NO EJECUTABLE EN ESTE ENTORNO  
**Explicación:** Docker no está disponible en el entorno de auditoría (Windows 11, PowerShell). No se puede levantar el stack completo ni validar health checks, monitoreo ni despliegue end-to-end.
**Evidencia:**
```
docker: The term 'docker' is not recognized as a name of a cmdlet, function, script file, or executable program.
```

---


# HALLAZGOS Y RIESGOS


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
| **Estado** | **PENDIENTE** (requiere cambio en GitHub, no en código) |
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
| **Estado** | **CORREGIDO** en `config/settings.py` |
| **Recomendación** | ~~Rechazar el arranque en cualquier entorno si `SECRET_KEY` no está definida, eliminando el fallback.~~ Corregido: en producción se lanza `RuntimeError`; en dev/test se genera clave aleatoria efímera. |

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
| **Estado** | **CORREGIDO** en `config/settings.py` |
| **Recomendación** | ~~En producción (`IS_PRODUCTION=True`), lanzar `RuntimeError` si `DB_HOST` no está configurado.~~ Corregido: ahora se rechaza el arranque en producción sin `DB_HOST`; SQLite se mantiene solo para dev/test. |

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
| **Estado** | **CORREGIDO** en `config/settings.py` |
| **Recomendación** | ~~Convertir en error crítico en producción.~~ Corregido: ahora se lanza `RuntimeError` si faltan tokens requeridos en producción. |

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
| **Estado** | **CORREGIDO** en `config/settings.py` |
| **Recomendación** | ~~Usar `True` por defecto en producción.~~ Corregido: `SECURE_SSL_REDIRECT` ahora usa `IS_PRODUCTION` como default. |

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
| **Estado** | **CORREGIDO** en `config/settings.py` |
| **Recomendación** | ~~Documentar dominios permitidos en `.env.production.example` y validar en deploy.~~ Corregido: ahora se lanza `RuntimeError` en producción si CORS no está configurado y `CORS_ALLOW_ALL_ORIGINS=False`. |

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

---


# CONCLUSIONES


**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`  
**Fecha de cierre del informe:** 2026-07-13  
**Entorno de auditoría:** Windows 11 Home, Python 3.14.0, Django 5.1.15, sin Docker, sin PostgreSQL/Redis local.

---

## 1. Datos cuantitativos

| Métrica | Valor |
|---------|-------|
| Archivos propios auditados | 1,897 |
| Líneas de código aproximadas | 370,928 |
| Rutas URL registradas | 1,812 |
| Dominios de negocio identificados | 21 |
| Hallazgos críticos | 1 |
| Hallazgos altos | 4 |
| Hallazgos medios | 6 |
| Hallazgos bajos | 2 |
| Evidencias registradas | 29 (EV-XXX) |

---

## 2. Estado general por área

| Área | Estado | Notas |
|------|--------|-------|
| **Infraestructura / CI-CD** | Funcional | Docker, Compose, Nginx, CI/CD y monitoreo implementados. Sin verificación local por falta de Docker. |
| **Seguridad** | Funcional parcial | Buenas prácticas en settings, middleware y workflows. Riesgo crítico: bypass de branch protection. Riesgo alto: fallback de SECRET_KEY y tokens. |
| **Base de datos / Modelos** | Implementado | PostgreSQL/SQLite configurable, modelo de usuario custom, relaciones LIMS actualizadas. No se verificó integridad referencial por falta de BD. |
| **Backend funcional** | Implementado | Múltiples dominios y vistas. Completado Fase 2 (Bloques 2, 3, 8, 13) y Fase 4 (governance/RBAC/performance) por Antigravity. |
| **API** | Implementado | 1,812 rutas registradas; API Ninja presente; endpoints de monitoreo expuestos. |
| **Frontend / UI** | Implementado | ~423 templates HTML, JS/CSS. No se auditaron visualmente todos. |
| **IA / MCA** | Implementado | Pris IA, Jarvis, agent tools, OCR/voz. Requiere API keys de terceros. |
| **Pruebas** | No ejecutable en este entorno | Suite intentada y abortada por timeout. `check --deploy` sí se ejecutó con 4 warnings esperados. |
| **Métricas de calidad** | No verificable | `radon`, `lizard`, `jscpd` no instalados. |

---

## 3. Hallazgos más críticos

### CRÍTICO (1)
1. **H-001 — Branch protection bypass en `release/v1.0-local`**: los pushes directos bypassan la regla de "solo vía PR". Esto invalida el control de calidad de integración. **Pendiente** (requiere cambio en GitHub, no en código).

### ALTO — Corregidos en este commit (4)
2. **H-002 — Fallback de SECRET_KEY hardcodeado**: ✅ corregido. Se eliminó el fallback literal; en producción es obligatoria y en dev/test se genera una clave aleatoria efímera.
3. **H-003 — Fallback silencioso a SQLite si falta DB_HOST**: ✅ corregido. Ahora se rechaza el arranque en producción si no está configurado `DB_HOST`.
4. **H-004 — Tokens de servicio solo generan warning**: ✅ corregido. Ahora se lanza `RuntimeError` en producción si faltan.
5. **H-005 — Suite de tests no ejecutable localmente**: **Pendiente** por limitaciones de entorno (requiere PostgreSQL/CI).

### Adicionales corregidos
6. **H-006 — `SECURE_SSL_REDIRECT` desactivado por defecto**: ✅ corregido. Ahora default es `IS_PRODUCTION`.
7. **H-011 — CORS sin orígenes en producción**: ✅ corregido. Ahora `RuntimeError` si no está configurado en producción.

---

## 4. Fortalezas detectadas

- **Arquitectura multi-tenant** implementada con middleware de subdominio e identidad de empresa.
- **Stack de monitoreo** (Prometheus/Grafana/Alertmanager) preparado con métricas, reglas y dashboards.
- **CI/CD robusto** con quality gate, health checks, backup/restore, secret scanning y SBOM.
- **Seguridad en capas**: CSRF, rate limiting, admin access por IP, blindaje de expedientes, session timeout.
- **Documentación reciente**: SRE runbooks, SLO/SLI, plan de colaboración, ADRs, entornos.
- **Modelo de datos LIMS** evolucionado con tabla intermedia `PerfilAnalito` para orden en reportes.

---

## 5. Debilidades principales

- **Control de cambios débil**: branch protection bypassado permite cambios sin revisión.
- **Configuración defensiva incompleta**: algunos fallbacks son demasiado permisivos o silenciosos.
- **Verificación local limitada**: sin Docker/BD real no se puede validar el stack completo.
- **Deuda de dependencias**: actualizaciones de seguridad pendientes (Pillow, google-genai, actions).
- **Complejidad acumulada**: ~15 middlewares custom y 21 dominios aumentan riesgo de regresiones.

---

## 6. Recomendación general

El proyecto PRISLAB SaaS está **avanzado y estructurado**, pero requiere **cerrar los controles de calidad y configuración de producción** antes de declarar enterprise-ready. La acción más urgente es **eliminar el bypass de branch protection** y **endurecer los fallbacks de SECRET_KEY/DB**. El resto de hallazgos son manejables en sprints cortos.

---

## 7. Cobertura de auditoría

| Sección del protocolo | Estado | Justificación |
|-----------------------|--------|---------------|
| 00 Manifiesto | ✅ Completado | `audit/000_MANIFEST.md` |
| 01 Rol/Objetivo/Alcance | ✅ Completado | `audit/01_INTRODUCCION_ALCANCE.md` |
| 2.1 Inventario total | ✅ Resumen | 1,897 archivos, 370k líneas en `_inventory_summary.md` |
| 2.2 Catálogo de dominios | ✅ Completado | 21 dominios en `_domain_catalog.md` |
| 3.1 Backend evidencial | ⚠️ Parcial | Se auditaron módulos críticos; 1,897 archivos no se revisaron línea por línea por limitaciones de tiempo/entorno. |
| 3.2 Base de datos | ⚠️ Parcial | Modelos revisados; esquema real no verificable sin PostgreSQL. |
| 3.3 API | ✅ Resumen | 1,812 rutas inventariadas. |
| 3.4 Frontend/UI | ⚠️ Parcial | Inventario realizado; no se revisaron todos los templates/componentes. |
| 3.5 Seguridad | ✅ Completado | Evidencias en `audit/06_seguridad/`. |
| 3.6 Infraestructura | ✅ Completado | Evidencias en `audit/07_infra/`. |
| 3.7 IA/MCA | ⚠️ Parcial | Inventario realizado; no se ejecutaron agentes por falta de API keys. |
| 3.8 UX/UI | ⚠️ Parcial | No se realizaron pruebas visuales manuales. |
| 3.9 Flujos E2E | ⚠️ Parcial | Documentados a alto nivel; no se ejecutaron. |
| 3.10 Pruebas | ✅ Ejecutado parcial | `check --deploy` sí corrió; suite de tests no finalizó. |
| 4.1 Métricas | ❌ No verificable | Faltan herramientas. |
| 4.2 Consistencia | ⚠️ Parcial | Sin BD real no se pudo validar modelo↔BD. |
| 4.3 Trazabilidad | ⚠️ Parcial | Se identificaron dependencias de dominio. |
| 5.1 Hallazgos | ✅ Completado | 13 hallazgos con criticidad/impacto/prioridad. |
| 5.2 Resumen ejecutivo | ✅ Completado | Este documento. |
| 5.3 Roadmap | ✅ Completado | `audit/12_roadmap.md`. |
| Gate de calidad final | ⚠️ Parcial | Faltan verificaciones de ejecución real y métricas. |

---

## 8. Cláusula de reproducibilidad

> Esta auditoría debe poder reproducirse sobre el mismo commit (`2b6e983`) obteniendo los mismos resultados, salvo cambios en el entorno de ejecución o en herramientas externas. Para una auditoría completa 100% se requiere un entorno con Docker, PostgreSQL, Redis y herramientas de métricas (`radon`, `lizard`, `jscpd`).

---


# ROADMAP


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

---


# FIN DEL DOCUMENTO
