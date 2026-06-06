# Matriz de Migración: Sistema Actual PRISLAB vs PRISLAB SaaS

Fecha de corte: 2026-06-06

Este documento compara el sistema legado actualmente en uso en el laboratorio con el reemplazo que estamos construyendo en PRISLAB SaaS.

La idea no es solo “que exista la pantalla”, sino que la operación real quede equivalente en:
- datos
- reglas
- reportes
- permisos
- flujos clínicos
- catálogo LIMS
- impresión y captura

## 1) Resumen Ejecutivo

PRISLAB SaaS ya reproduce la arquitectura base del sistema actual:
- pruebas / analitos
- valores de referencia
- perfiles
- paquetes
- tarifas
- órdenes de laboratorio
- captura de resultados
- impresión de resultados

El reemplazo todavía requiere paridad total en:
- catálogo cargado
- rangos de referencia exactos
- orden de composición de perfiles/paquetes
- reportes y exportaciones
- módulos operativos laterales
- validación final en producción

## 2) Mapeo General de Arquitectura

| Sistema actual | PRISLAB SaaS | Estado |
|---|---|---|
| Prueba / Analito | `lims.Analito` | Implementado |
| Valores de referencia | `lims.ValorReferenciaAnalito` | Implementado |
| Perfil | `lims.PerfilLims` | Implementado |
| Paquete | `lims.PaqueteLims` | Implementado |
| Tarifas | `lims.PrecioItem` | Implementado |
| Orden de laboratorio | `core.OrdenDeServicio` + `OrdenDetalle` | Implementado |
| Captura / validación de resultados | `core.views.laboratorio` + `core.services.resultados_impresion_presentacion` | Implementado |
| PDF / impresión de resultados | `core/templates/core/resultados_print.html` | Implementado |
| Recepción de estudios | `core/templates/core/recepcion_lab.html` | Implementado |

## 3) Comparación por Módulo

### 3.1 Dashboard

**Sistema actual**
- Indicadores principales del mes.
- Pacientes nuevos, pacientes frecuentes, órdenes.

**PRISLAB SaaS**
- Dashboard unificado operativo en `core/views/dashboard_unificado.py`.

**Estado**
- Base equivalente ya existe.
- Falta comparar visualmente los mismos KPIs y colores del sistema actual.

**Riesgo pendiente**
- Que algún KPI clave del sistema actual no esté calculándose con la misma lógica.

---

### 3.2 Órdenes

**Sistema actual**
- Registro completo de orden.
- Búsqueda de paciente.
- Selección de médico.
- Tarifa.
- Tipo de orden.
- Hora de toma/entrega.
- Diagnóstico.
- Factura.
- Notas.
- Consulta de órdenes del día.
- Resultados del día.
- Cobranza pendiente.
- Estatus de entrega.
- Muestras pendientes.

**PRISLAB SaaS**
- Recepción y cobro en `core/templates/core/recepcion_lab.html`.
- Creación de orden en `core/views/laboratorio.py`.
- Soporte de cortesía, CxC y cobro múltiple.

**Estado**
- Funcionalmente muy avanzado.
- Ya se corrigieron mismatches entre frontend y backend.

**Faltante / por igualar**
- Verificar que los filtros, exportaciones e impresiones reproduzcan exactamente el comportamiento del sistema actual.
- Verificar si el flujo actual requiere los mismos submódulos visibles o si algunos se consolidan en una sola pantalla.

---

### 3.3 Cotización

**Sistema actual**
- Cotización por cliente / tarifa.
- Tarifa por defecto.
- Opción de factura.

**PRISLAB SaaS**
- `core/views/cotizacion.py`

**Estado**
- Implementado.
- Ya se corrigió una consulta inválida a `PerfilLaboratorio`.

**Faltante / por igualar**
- Comparar el cálculo exacto de cotización contra el sistema actual.
- Revisar si la pantalla actual exige mismos filtros y mismas reglas comerciales.

---

### 3.4 Pacientes

**Sistema actual**
- Alta y consulta de pacientes.
- Buscador y filtros.

**PRISLAB SaaS**
- Módulos y modelos de pacientes en `core`.

**Estado**
- Base funcional existente.

**Faltante / por igualar**
- Confirmar que los campos obligatorios y el comportamiento del buscador coinciden con el sistema actual.

---

### 3.5 Clientes

**Sistema actual**
- 26 clientes registrados.
- Clave, nombre, email, teléfono, tarifa base, fecha de alta.

**PRISLAB SaaS**
- Existen modelos y vistas de negocio, pero esta comparación requiere cotejo visual final.

**Estado**
- Parcialmente equivalente.

**Faltante / por igualar**
- Verificar que el catálogo de clientes y su relación con tarifas quede idéntico.

---

### 3.6 Médicos

**Sistema actual**
- Base extensa de médicos.
- Perfil / especialidad capturada.

**PRISLAB SaaS**
- `core.views.laboratorio` y modelos relacionados usan `Medico`.

**Estado**
- Implementado.

**Faltante / por igualar**
- Confirmar que búsqueda, alta y relación con órdenes reproduce el mismo flujo.

---

### 3.7 Configuración

**Sistema actual**
- Correos.
- Catálogo de pruebas.
- Perfiles.
- Paquetes.
- Tarifas.
- Promociones.
- Tipo de muestra.
- Método.
- Departamentos.

**PRISLAB SaaS**
- LIMS jerárquico en `lims.models`.
- Pipeline de ensamblado en `lims.management.commands.ensamblar_lims_v75`.

**Estado**
- Muy alineado en estructura.

**Faltante / por igualar**
- Verificar que cada catálogo tenga la misma cardinalidad y nombres que el sistema actual.
- Validar que el default de tarifa coincida con producción.

---

### 3.8 Reportes

**Sistema actual**
- Cortes por sucursal.
- Ventas por cliente.
- Consulta de caja.
- Cobranza pendiente.
- Exámenes realizados.
- Hojas de trabajo.
- Exámenes por médico.
- Tiempos de proceso.
- Detallado de resultados.

**PRISLAB SaaS**
- Existen vistas y servicios para resultados, auditoría, entrega y laboratorio.

**Estado**
- Parcialmente alineado.

**Faltante / por igualar**
- Verificar que cada exportación PDF / Excel / ZIP exista y coincida en campos.
- Comparar el formato exacto de cada reporte con el legado.

---

### 3.9 Programa de lealtad

**Sistema actual**
- Monedero.
- Saldo de monedero.
- Monederos redimidos.

**PRISLAB SaaS**
- No se ha cerrado completamente la equivalencia funcional en esta revisión.

**Estado**
- Pendiente de paridad completa.

---

### 3.10 Microbiología

**Sistema actual**
- Bacterias.
- Antibióticos.
- Grupos de antibióticos.

**PRISLAB SaaS**
- Existe infraestructura de laboratorio y microbiología, pero requiere validación catálogo por catálogo.

**Estado**
- Parcial.

**Faltante / por igualar**
- Reproducir catálogo y comportamiento operativo al 100%.

---

### 3.11 Auditoría

**Sistema actual**
- Consulta de actividad por fecha, usuario y tipo de auditoría.

**PRISLAB SaaS**
- Existen componentes de auditoría y forense.

**Estado**
- Implementado en gran parte.

**Faltante / por igualar**
- Confirmar que los filtros y exportaciones sean idénticos al legado.

---

### 3.12 Seguridad

**Sistema actual**
- Usuarios.
- Perfiles de acceso.

**PRISLAB SaaS**
- `TenantModel`, `read_only`, middleware, roles y superusuarios.

**Estado**
- Más robusto que el legado en arquitectura.

**Faltante / por igualar**
- Validar permisos exactos por rol para no romper operación diaria.

## 4) Construcción del Catálogo LIMS en PRISLAB SaaS

La estructura real del reemplazo está montada así:

1. `Analito`
   - prueba mínima
   - código, abreviatura, nombre, departamento, muestra, método, tipo de resultado, unidades, fórmula, indicaciones

2. `ValorReferenciaAnalito`
   - rangos por sexo y edad
   - ref mínimo / ref máximo
   - texto de referencia
   - umbrales críticos

3. `PerfilLims`
   - agrupa analitos
   - define composición técnica del reporte

4. `PaqueteLims`
   - agrupa perfiles y/o analitos
   - define la oferta comercial

5. `PrecioItem`
   - separa la gestión financiera del catálogo clínico

## 5) Cómo se carga el reemplazo

El orden correcto del sistema nuevo es:

1. Cargar `Parametros.csv` + `Valores_normalidad.csv`
2. Construir `Analito` + `ValorReferenciaAnalito`
3. Cargar `Examenes.csv` + `Examenes_Perfil.csv`
4. Construir `PerfilLims`
5. Cargar `Paquetes.csv` + `Paquetes_Perfil.csv`
6. Construir `PaqueteLims`
7. Sincronizar `PrecioItem`

Pipeline:
- `lims.management.commands.ensamblar_lims_v75`

## 6) Diferencias Reales que todavía hay que cerrar

Estas son las diferencias que todavía se deben comparar uno a uno contra el sistema actual:

- cardinalidad exacta de estudios
- nombres exactos de perfiles y paquetes
- orden exacto de analitos en perfiles
- reglas exactas de texto de referencia
- impresión y formato final de PDF
- exportaciones de reportes
- módulos de lealtad
- módulos microbiológicos
- permisos por perfil

## 7) Conclusión

PRISLAB SaaS ya tiene la base correcta para reemplazar el sistema actual.
No es solo una idea similar: ya existe la arquitectura clínica y comercial necesaria.

Lo que falta para considerarlo reemplazo total es cerrar la paridad exacta de:
- datos
- pantallas
- reportes
- catálogos
- comportamiento por rol

Este documento se debe usar como checklist de migración.
