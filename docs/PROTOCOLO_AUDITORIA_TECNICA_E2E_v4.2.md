# PROTOCOLO DE AUDITORÍA TÉCNICA E2E – PRISLAB SAAS (Django) v4.2 (10/10 INTEGRADO)

## IDENTIFICADOR GLOBAL DE AUDITORÍA  
**AUD-YYYYMMDD-HHMMSS** (se genera al iniciar y se incluye en todos los documentos)

---

## FASE 0 – MANIFIESTO Y PREPARACIÓN (OBLIGATORIO)

Genera `/audit/000_MANIFEST.md` con:

- **ID de auditoría** (AUD-...).
- Commit SHA exacto, rama, estado del repo, fecha/hora de inicio.
- Entorno: SO, Python, Node, Django, BD, dependencias instaladas.
- Variables de entorno detectadas (solo nombres, nunca valores).
- Herramientas disponibles/ausentes y limitaciones del entorno.
- **Idioma de salida: Español** en toda la auditoría.
- **Nomenclatura congelada:** todo módulo, dominio, componente o función mantendrá exactamente el mismo nombre en todas las secciones; prohibido renombrar entre fases.

**Reglas de alcance inalterables:**

- **Aislamiento de contexto:** Solo PRISLAB SAAS. Cualquier referencia a "Imperium" u otro proyecto se ignora; si se detecta mezcla, se reporta como hallazgo crítico.
- **Exclusión de vendor/boilerplate:** No se audita función por función: `node_modules`, `site-packages`, `vendor/`, migraciones 100% autogeneradas sin modificación manual, estáticos de frameworks. En inventario aparecen como `vendor/no auditado` con justificación.
- **Prioridad de troceo:**  
  1) Autenticación/permisos/seguridad → 2) BD y modelos → 3) API críticos (laboratorio, farmacia) → 4) Backend restante → 5) Frontend → 6) IA/MCA → 7) Infra/CI‑CD → 8) UX/UI y resto.
- **Sub-troceo de archivos grandes:** Si un archivo supera ~400 líneas o ~15 funciones, se divide en sub-lotes por bloque lógico. Se entregan como:
  ```
  /audit/01_backend/laboratorio_py/parte_01.md
  /audit/01_backend/laboratorio_py/parte_02.md
  ...
  ```
  Al terminar el último sub-lote se genera `_completo.md` con la lista de todas las funciones/clases cubiertas, confirmando cobertura 100% sin huecos. Aplica también a templates o componentes de frontend muy extensos.
- **Estructura de entrega:**
  ```
  /audit/000_MANIFEST.md
  /audit/00_INDICE.md
  /audit/01_backend/
  /audit/02_frontend/
  /audit/03_db/
  /audit/04_api/
  /audit/05_pruebas/
  /audit/06_seguridad/
  /audit/07_infra/
  /audit/08_ia/
  /audit/09_metricas/
  /audit/10_hallazgos/
  /audit/11_conclusiones.md
  /audit/12_roadmap.md
  ```

---

## DEFINICIONES Y ESTÁNDARES GLOBALES (aplican a toda la auditoría)

### Cobertura 100%
El 100% de cobertura significa que **todo elemento propio del proyecto** está clasificado en una de estas categorías:
- **Documentado completamente** (con evidencia EV-XXX)
- **No verificable** (con justificación)
- **No ejecutable en este entorno** (con evidencia de la limitación)
- **Excluido por regla** (vendor/boilerplate)
No puede quedar ningún elemento sin clasificación.

### Taxonomía única de estados
Todos los elementos deben etiquetarse con uno de los siguientes estados normalizados:

| Estado | Significado |
|--------|-------------|
| IMPLEMENTADO | Presente y completo en código |
| FUNCIONAL | Verificado por ejecución |
| FUNCIONAL PARCIAL | Funciona con limitaciones conocidas |
| INCOMPLETO | Desarrollo no finalizado |
| NO IMPLEMENTADO | Se esperaba pero no existe |
| NO VERIFICABLE | Existe pero no se pudo comprobar |
| NO EJECUTABLE | No se pudo ejecutar en el entorno actual |
| NO LOCALIZADO | No se encontró durante el análisis |
| DEPRECADO | Marcado como obsoleto |
| HUÉRFANO | Sin referencias ni llamadas |
| CÓDIGO MUERTO | Inaccesible o sin efecto |
| DUPLICADO | Código repetido en otra ubicación |
| VENDOR | Tercero, no auditado |
| PLACEHOLDER | Implementación simulada o vacía |

### Criticidad de las evidencias
Cada evidencia EV-XXX debe llevar un nivel de criticidad:

- **CRÍTICA** – Hallazgo que compromete seguridad, datos o disponibilidad.
- **ALTA** – Afecta funcionalidad core o a muchos usuarios.
- **MEDIA** – Impacto moderado en funcionalidad o mantenibilidad.
- **BAJA** – Mejora deseable pero no urgente.
- **INFORMATIVA** – Documentación sin riesgo asociado.

### Diferenciación precisa de conceptos
- **NO EXISTE** – No se encontró implementación alguna.
- **NO VERIFICABLE** – Existe pero no pudo comprobarse (falta de acceso, herramientas, etc.).
- **NO EJECUTABLE** – No fue posible ejecutarlo por limitaciones del entorno.
- **NO LOCALIZADO** – No se pudo encontrar durante el análisis (p. ej., referencias circulares o dinámicas).
Estos términos se usarán con precisión, sin mezclarlos.

---

## FASE 1 – ROL, OBJETIVO Y ALCANCE

**Rol:** Comité auditor multidisciplinario (Arquitecto Senior, Staff Engineer, Auditor de Código, QA Lead, DevOps, Security Engineer, DB Architect, UX/UI).  
**Misión:** Inspeccionar el 100% del código propio de PRISLAB, basándose **exclusivamente** en evidencia real. Prohibido inferir, asumir o fabricar.  
**Objetivo:** Auditoría integral E2E del estado real actual, incluyendo seguridad, infraestructura e IA (MCA si aplica).

---

## FASE 2 – INVENTARIO Y CATÁLOGO DEL DOMINIO

### 2.1 Inventario total de archivos
Listar todos los archivos y carpetas con: ruta, propósito, líneas de código, última modificación, **estado según taxonomía única**.

### 2.2 Catálogo del dominio
Reconstruir los dominios de negocio detectados (Laboratorio, Farmacia, Caja, Compras, Inventario, Pacientes, Médicos, Resultados, Facturación, Usuarios, Roles, Permisos, IA, Configuración, etc.). Para cada uno: propósito, actores, reglas de negocio, entidades, flujos principales, dependencias con otros dominios. **Usar los nombres exactos que aparecen en el código, sin renombrar.**

---

## FASE 3 – AUDITORÍA TÉCNICA (ANÁLISIS EVIDENCIAL)

### Formato único de evidencia (obligatorio)
```
EV-XXX
Criticidad: CRÍTICA / ALTA / MEDIA / BAJA / INFORMATIVA
Archivo: ruta/al/archivo.py
Línea: inicio-fin
Clase/Función: nombre
Fragmento: (código real)
Explicación: (basada estrictamente en el fragmento)
Confianza: ★★★★★ (verificado por ejecución) / ★★★★☆ (código) / ★★★☆☆ (parcial) / ★★☆☆☆ (hipótesis) / ★☆☆☆☆ (no verificable)
Riesgos: (si aplica)
Estado: (según taxonomía única)
```

**Ejemplo concreto:**
```
EV-001
Criticidad: BAJA
Archivo: core/models.py
Línea: 45-52
Clase/Función: Paciente.crear_historial
Fragmento: 
    def crear_historial(self, resultado):
        return Historial.objects.create(paciente=self, resultado=resultado)
Explicación: Crea un registro de historial clínico al recibir un resultado de laboratorio.
Confianza: ★★★★★
Riesgos: Ninguno detectado
Estado: FUNCIONAL
```

**Regla anti-duplicación:** La primera vez se asigna EV-XXX único. En secciones posteriores se referencia como "Ver EV-001". Solo el compendio final (sección 17) contiene el fragmento completo.

### 3.1 Backend
Cada archivo, clase, función/método, endpoint, middleware, servicio, modelo, serializador, comando de management, signal, migración propia, scheduler, worker. Aplica el formato EV, estado y criticidad.

### 3.2 Base de datos
Esquema real, migraciones aplicadas vs pendientes, integridad referencial, discrepancias modelo vs BD. Documentar cada tabla, columna, constraint. Estado real.

### 3.3 API
Todos los endpoints con: URL, método, parámetros, body, response, errores, auth, permisos, middlewares, flujo hasta capa de datos. Criticidad y estado.

### 3.4 Frontend / UI
Cada template, componente, hook, contexto, store, ruta, layout, formulario, modal. Incluir estructura real del árbol DOM/JSX (jerarquía, clases, condicionales), nunca descripción visual imaginada. Criticidad y estado.

### 3.5 Seguridad
JWT, sesiones, cookies, CORS, CSRF, XSS, SQLi, permisos, roles, encriptación, secretos. Si se detectan credenciales expuestas: reportar ubicación y tipo, **valor siempre enmascarado** (`[REDACTED]`).

### 3.6 Infraestructura
Docker, Compose, Nginx, configuraciones, CI/CD, logs, monitoreo, dependencias externas.

### 3.7 IA / MCA (si existe)
Modelos, prompts, herramientas, flujo de ejecución, memoria, indexación.

### 3.8 UX/UI y experiencia de usuario
Pantallas reales, navegación, consistencia, accesibilidad, estados (carga, error, vacío). Flujo: qué hace el usuario → qué ocurre internamente → módulos y eventos.

### 3.9 Flujos E2E completos
Para cada proceso de negocio (laboratorio, farmacia, usuarios, permisos, auth, reportes, IA, configuración, logs) mapear:
Usuario → Frontend → Estado → API → Backend → Servicios → BD → Respuesta → Frontend → Usuario.
Usar referencias a EV-XXX, no repetir fragmentos.

### 3.10 Pruebas
- Listar todos los archivos de test.
- Ejecutar `pytest --cov` (o comando configurado) y pegar output real.
- Indicar tests que pasan/fallan, cobertura real por módulo.
- Si no es ejecutable: **"NO EJECUTABLE EN ESTE ENTORNO — falta X"**. No fabricar.

---

## FASE 4 – MÉTRICAS, CONSISTENCIA Y TRAZABILIDAD

### 4.1 Métricas (solo con herramienta verificable)
Totales: archivos, líneas, clases, funciones, endpoints, componentes, tablas, migraciones, modelos, servicios, hooks, rutas.
- Complejidad → `radon cc` o `lizard` (output real).
- Cobertura → `pytest --cov` (output real).
- Duplicidad → `jscpd` o `pylint --enable=duplicate-code`.
- Deuda técnica → si no hay herramienta → **"NO VERIFICABLE — sin herramienta configurada"**.

**Fallback:** Si falta BD, runner o herramientas → **"NO EJECUTABLE EN ESTE ENTORNO"**.

### 4.2 Análisis de consistencia (obligatorio)
Comparar y listar discrepancias:
- Modelo Django ↔ BD real
- URL ↔ View
- View ↔ Template
- Template ↔ JavaScript
- Serializer ↔ Modelo
- Permisos declarados ↔ aplicados
- Documentación existente ↔ implementación real

### 4.3 Trazabilidad bidireccional (para elementos críticos)
Para funciones/endpoints clave:
- Quién la llama
- A quién llama
- Qué rompe si cambia
- Qué rompe si desaparece

---

## FASE 5 – HALLAZGOS, IMPACTO, ROADMAP Y CIERRE

### 5.1 Hallazgos y riesgos
Cada hallazgo debe presentar:
- **Hecho** (evidencia EV-XXX)
- **Interpretación**
- **Impacto** (Crítico/Alto/Medio/Bajo)
- **Probabilidad** (Alta/Media/Baja)
- **Esfuerzo estimado** (Alto/Medio/Bajo)
- **Riesgo resultante**
- **Prioridad** (P1/P2/P3/P4)
- **Recomendación**

### 5.2 Resumen ejecutivo cuantitativo (incluir en `/audit/11_conclusiones.md` y en el inicio del informe)
Debe contener:
- Proyecto, ID de auditoría, versión/commit auditado
- Tiempo total de auditoría
- Archivos auditados, funciones, endpoints
- Cobertura alcanzada
- Hallazgos críticos, altos, medios, bajos
- Estado general del sistema (tabla resumen)

### 5.3 Roadmap automático (`/audit/12_roadmap.md`)
- Quick Wins (bajo esfuerzo, alto impacto)
- Sprints 1-4 priorizados por riesgo
- Cambios críticos / bloqueantes / recomendados / opcionales
- Esfuerzo estimado por cada elemento

### 5.4 Gate de calidad final (OBLIGATORIO ANTES DE CERRAR)
No se finaliza mientras exista alguno de estos pendientes:
- ☐ Evidencia sin referencia EV-XXX
- ☐ Archivo propio sin documentar
- ☐ Endpoint sin analizar
- ☐ Modelo sin documentar
- ☐ Función sin estado (según taxonomía única)
- ☐ Hallazgo sin criticidad, impacto o prioridad
- ☐ Recomendación sin prioridad
- ☐ Diagrama faltante
- ☐ Archivo grande sin sub-troceo y consolidación completa
- ☐ Cobertura total PRISLAB < 100% (excluyendo vendor/Imperium)

**Pasada de autoverificación:** Buscar afirmaciones de "funcional/correcto/implementado" sin EV-XXX adjunta → marcar **"⚠️ AFIRMACIÓN SIN EVIDENCIA — INVALIDADA"** y corregir o eliminar. Reportar cuántas correcciones se hicieron.

### 5.5 Checklist de cobertura final (obligatorio)

| Sección | Estado (Sí/No) | Notas |
|---------|----------------|-------|
| 00 Índice y Manifiesto | | |
| 2.1 Inventario total | | |
| 2.2 Catálogo del dominio | | |
| 3.1 Backend (archivo por archivo) | | |
| 3.2 Base de datos | | |
| 3.3 API | | |
| 3.4 Frontend/UI | | |
| 3.5 Seguridad | | |
| 3.6 Infraestructura | | |
| 3.7 IA/MCA | | |
| 3.8 UX/UI | | |
| 3.9 Flujos E2E | | |
| 3.10 Pruebas | | |
| 4.1 Métricas (o fallback) | | |
| 4.2 Consistencia | | |
| 4.3 Trazabilidad bidireccional | | |
| 5.1 Hallazgos con criticidad e impacto | | |
| 5.2 Resumen ejecutivo cuantitativo | | |
| 5.3 Roadmap | | |
| 17. Compendio de evidencias | | |
| Archivos grandes: sub-troceados y consolidados sin huecos | | |
| Cobertura total PRISLAB (excluyendo vendor/Imperium) | | |

### 5.6 Cláusula de reproducibilidad
> “Esta auditoría debe poder reproducirse sobre el mismo commit obteniendo los mismos resultados, salvo cambios en el entorno de ejecución o en herramientas externas.”

---
