# GAP Analysis — PRISLAB vs ISO 15189:2022

**Fecha:** 2026-06 (auditoría de código real, no documentación)
**Metodología:** Cada punto fue verificado contra el código fuente actual, no contra reportes previos (varios de los cuales resultaron desactualizados durante esta auditoría).

---

## 1. Requisitos de Gestión (Sección 4-5 de la norma)

| Requisito ISO 15189 | Estado en PRISLAB | Evidencia en código |
|---|---|---|
| Control de documentos | 🔴 No implementado | No se encontró versionado de SOPs/procedimientos |
| Acuerdos de servicio con clientes | 🟡 Parcial | Existe `ProveedorCompras` con trazabilidad, pero no hay gestión formal de acuerdos de servicio con médicos referentes |
| Gestión de proveedores (reactivos/IVD) | 🟢 Implementado | `inventario/models.py:ProveedorCompras` — comentario explícito: "cumple los requisitos de trazabilidad de la ISO 15189 para proveedores de reactivos y materiales analíticos" |
| No conformidades | 🟡 Parcial | Existe `IncidenciaSentinel` (consultorio) y War Room para anomalías, pero no hay flujo formal de "no conformidad → acción correctiva → verificación de cierre" |
| Acciones correctivas/preventivas | 🔴 No implementado | No se encontró módulo dedicado |
| Mejora continua | 🟡 Parcial | "Buzón de Quejas" (`core/views/buzon.py`) existe, pero es informal, no estructurado como ISO lo requiere |
| Auditorías internas | 🔴 No implementado | Existen scripts de auditoría técnica del *sistema* (`auditoria_*.py`), no auditorías de *calidad* del laboratorio |
| Revisión por la dirección | 🟡 Parcial | Dashboard Director (KPIs) existe, pero no como proceso formal documentado de revisión periódica |

## 2. Requisitos Técnicos (Sección 6-7 de la norma)

| Requisito ISO 15189 | Estado en PRISLAB | Evidencia en código |
|---|---|---|
| Competencia del personal | 🟡 Parcial | Roles definidos (`Usuario.rol`), `FirmaDigital.cedula_profesional`, flag `VERIFICACION_SEP_ACTIVA` (consulta SEP, solo informativa) — falta registro formal de capacitación/competencia evaluada |
| Instalaciones y condiciones ambientales | 🔴 No implementado en software | Es responsabilidad física, no de software — fuera de alcance del sistema |
| Equipos de laboratorio | 🟡 Parcial | `mantenimiento/check_certificados_metrologicos.py` existe (certificados de calibración) — falta gestión completa de mantenimiento preventivo/ciclo de vida de equipos |
| Trazabilidad metrológica | 🟢 Implementado parcialmente | Comando `check_certificados_metrologicos` confirma seguimiento de certificados |
| Materiales de referencia / reactivos | 🟢 Implementado | `CatalogoReactivoLab`, `LoteReactivoLab` con caducidad y trazabilidad de lote |
| **Control de calidad interno (Westgard)** | 🟢 Construido y probado, **desactivado por defecto** | Módulo completo en `laboratorio/services/westgard.py` (119 líneas) + `cci_models.py`/`cci_canal.py`/`cci_api.py` + suite de tests dedicada (`laboratorio/tests/test_westgard.py`). No es un stub: es un motor real con cobertura de pruebas. Solo el flag `QC_WESTGARD_ACTIVO` está en `False` por defecto — activarlo es trivial, el trabajo de ingeniería ya está hecho |
| Evaluación externa de calidad (EQA/PEEC) | 🔴 No implementado | No se encontró módulo de comparación interlaboratorial |
| Aseguramiento de calidad de resultados | 🟢 Implementado | `DELTA_CHECK_ACTIVO` (default `True`) — compara resultado actual vs. histórico del paciente, alerta si varía >30% |
| Valores de alerta/pánico | 🟢 Implementado | `ISO15189_CRITICOS_ACTIVO` (default `True`), War Room monitorea "valores de pánico sin validar >15 min" |
| Cadena de frío en transporte de muestras | 🟢 Implementado | `CADENA_FRIO_ACTIVO` — exige captura de temperatura 2-8°C al escanear QR de traslado, bloquea si está fuera de rango |
| Identificación inequívoca de muestras | 🟢 Implementado | Sistema de QR/etiquetas (`laboratorio/views/etiquetas.py`, `imprimir_zpl.py`) |
| Informes de resultados (formato, firma, validación) | 🟢 Implementado | PDF con firma digital, QR de validación, Triple Llave mencionada en auditorías previas |
| Trazabilidad completa de operaciones | 🟢 Implementado | `TrazabilidadOperacion`, `AuditLog`, `LogAccionSensible` con hash SHA-256 |
| Confidencialidad de datos del paciente | 🟡 Parcial — **con hallazgo de seguridad** | RBAC + 2FA existen, pero esta auditoría encontró y corrigió: (a) bypass de 2FA vía spoofing de IP, (b) sin rate-limit en 2FA, (c) fuga de tenant en búsqueda de médico — los 3 ya corregidos en esta sesión |

## 3. Hallazgos clave de esta auditoría

1. **El sistema ya tiene más cobertura de ISO 15189 de la que la documentación anterior sugería** — control de valores críticos, delta check, cadena de frío y trazabilidad de reactivos están construidos y en su mayoría activos por defecto.
2. **El control de calidad Westgard (QC) está construido pero apagado por defecto** (`QC_WESTGARD_ACTIVO=False`). Es el gap técnico más grande y más fácil de cerrar — solo requiere activación + validación con datos reales, no desarrollo desde cero.
3. **No existe evaluación externa de calidad (EQA/PEEC)** — es un requisito obligatorio de acreditación real ISO 15189 que no se puede resolver solo con software; requiere inscripción a un programa externo (ej. CAP Surveys, INDRE en México).
4. **Falta el ciclo formal de no conformidades y acciones correctivas** — existe detección de anomalías (War Room, Sentinel) pero no el flujo de cierre documentado que un auditor ISO exige ver.
5. **Auditorías internas de calidad no existen como proceso** — lo que hay son auditorías técnicas del código/sistema, no auditorías de calidad del servicio de laboratorio.

## 4. Recomendación de siguiente paso (no construir todo de golpe)

Dado el principio de "cumplimiento configurable, no obligatorio de golpe" ya establecido para el producto:

1. **Más barato/rápido:** activar y piloteaar `QC_WESTGARD_ACTIVO` con datos reales de control — ya está construido.
2. **Medio plazo:** construir el módulo de No Conformidades + Acciones Correctivas (no existe, es requisito duro de auditoría).
3. **Depende de decisión de negocio, no de código:** inscripción a un programa de Evaluación Externa de Calidad — esto es un trámite/costo externo, no una tarea de desarrollo.
4. **Para el producto multi-tenant:** cada uno de estos puntos debería exponerse como un flag más en el panel de Configuración de Cumplimiento (`/configuracion/flags/`) que ya existe y funciona — así otros laboratorios que compren PRISLAB pueden subir de nivel de cumplimiento de forma gradual, igual que tú.
