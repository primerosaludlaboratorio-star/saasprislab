# Plan de cierre de migración PRISLAB

Fecha de corte: 2026-06-06

Este plan nace de la matriz comparativa entre el sistema legado del laboratorio y PRISLAB SaaS.
Su objetivo es cerrar la migración sin perder operación real, priorizando primero lo que bloquea el reemplazo funcional y después lo que solo pule paridad visual o documental.

## 1) Criterio de priorización

Se usa esta escala:

- P0: bloquea el reemplazo operativo o la validación real en producción.
- P1: no bloquea la operación, pero sí evita declarar paridad completa.
- P2: mejora de consistencia, UX o trazabilidad.

## 2) Orden de ejecución recomendado

1. Cerrar catálogo LIMS y paridad de resultados.
2. Cerrar laboratorio operativo end-to-end.
3. Cerrar reportes y exportaciones críticas.
4. Cerrar módulos laterales con impacto diario: pacientes, clientes, médicos.
5. Cerrar módulos complementarios: auditoría, seguridad fina, microbiología, lealtad.
6. Validar visualmente que PRISLAB SaaS reproduce el flujo real del sistema legado.

## 3) Bloques de cierre por prioridad

### P0 - Bloquea la sustitución real

#### 3.1 Catálogo LIMS completo y exacto

Objetivo:
- igualar la cardinalidad y composición del catálogo del sistema actual
- asegurar que pruebas, perfiles, paquetes y tarifas coincidan con producción

Tareas:
- comparar el catálogo legado contra `Analito`
- verificar que `ValorReferenciaAnalito` tenga todos los rangos
- validar que `PerfilLims` respete el orden exacto de analitos
- validar que `PaqueteLims` respete la composición comercial
- asegurar que `PrecioItem` coincida con la tarifa vigente

Dependencias:
- `lims/models.py`
- `lims/management/commands/ensamblar_lims_v75.py`
- `datos_lims/`

#### 3.2 Resultados y PDF de laboratorio

Objetivo:
- que el resultado impreso muestre exactamente los rangos y textos de referencia
- que el PDF y la captura coincidan con la práctica actual

Tareas:
- comparar plantillas de impresión contra el laboratorio actual
- validar casos con rango numérico
- validar casos con texto de referencia
- validar casos pediátricos y por sexo
- validar estados normal / alto / bajo / crítico

Dependencias:
- `core/services/resultados_impresion_presentacion.py`
- `core/templates/core/resultados_print.html`
- `core/templates/core/laboratorio/captura_resultados.html`

#### 3.3 Recepción y cobro de órdenes

Objetivo:
- garantizar que la orden se cree, se cobre y se confirme sin errores en flujo real

Tareas:
- validar alta de orden con estudios simples
- validar alta de orden con perfiles
- validar cobro exacto y cobro mixto
- validar cortesía / beca / CxC
- validar que el frontend y backend usen el mismo payload

Dependencias:
- `core/templates/core/recepcion_lab.html`
- `core/views/laboratorio.py`

### P1 - Necesario para paridad funcional completa

#### 3.4 Pacientes

Objetivo:
- que el alta, edición y búsqueda reproduzcan el comportamiento esperado del sistema actual

Tareas:
- validar campos obligatorios
- validar buscador
- validar duplicados
- validar relación con órdenes y consultas

#### 3.5 Clientes

Objetivo:
- replicar el catálogo de clientes, su tarifa y su relación comercial

Tareas:
- comparar claves, nombres y tarifas base
- validar búsqueda y edición
- validar uso en cotización y facturación

#### 3.6 Médicos

Objetivo:
- que la relación médico-orden funcione igual que en el legado

Tareas:
- validar alta / búsqueda / edición
- validar asignación en recepción
- validar filtros y reportes por médico

#### 3.7 Cotización

Objetivo:
- igualar cálculo comercial y filtros de cotización

Tareas:
- validar tarifa por defecto
- validar facturación
- validar catálogo de perfiles y estudios
- comparar totales con sistema actual

#### 3.8 Reportes críticos

Objetivo:
- igualar los reportes de operación diaria que sí usan el negocio

Tareas:
- cortes por sucursal
- ventas por cliente
- caja
- cobranza pendiente
- exámenes realizados
- resultados detallados
- tiempos de proceso

### P2 - Complementario, pero importante para cierre fino

#### 3.9 Programa de lealtad

Objetivo:
- reproducir monedero, saldo y redención

Tareas:
- validar acumulación
- validar redención
- validar saldo en tickets y reportes

#### 3.10 Microbiología

Objetivo:
- igualar catálogo y comportamiento operativo del área microbiológica

Tareas:
- validar bacterias
- validar antibióticos
- validar grupos de antibióticos
- validar reportes y captura

#### 3.11 Auditoría

Objetivo:
- igualar filtros, trazabilidad y exportación de actividad

Tareas:
- validar filtros por usuario, fecha y tipo
- validar exportaciones
- validar consulta histórica

#### 3.12 Seguridad fina

Objetivo:
- asegurar que los permisos por rol no rompan la operación diaria

Tareas:
- validar usuarios
- validar perfiles
- validar read-only / excepciones
- validar operación de superusuarios

## 4) Entregables por fase

### Fase 1: cierre de catálogo y laboratorio

Entregables:
- catálogo LIMS equivalente
- resultados con referencias correctas
- órdenes y cobro estables

### Fase 2: cierre comercial y operativo

Entregables:
- pacientes
- clientes
- médicos
- cotización
- reportes críticos

### Fase 3: cierre extendido

Entregables:
- lealtad
- microbiología
- auditoría
- permisos finos

## 5) Validación de salida

PRISLAB SaaS se puede considerar reemplazo real cuando cumpla todo esto:

- el catálogo LIMS coincide con el legado
- los rangos de referencia se imprimen igual
- la orden se crea y cobra sin intervención manual
- los reportes críticos están disponibles
- pacientes, clientes y médicos funcionan con el mismo criterio comercial
- la operación diaria no depende de parches de emergencia

## 6) Recomendación operativa

No avanzar a cambio definitivo de producción hasta completar al menos:

1. P0 completo
2. al menos 80% de P1
3. validación visual final sobre el flujo real en producción

