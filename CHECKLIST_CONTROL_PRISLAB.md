# Checklist de control PRISLAB

Fecha de corte: 2026-06-06

Este checklist consolida el estado de la migración entre el sistema legado y PRISLAB SaaS.
La intención es tener un tablero único para avanzar sin perder contexto.

## Estado general

- [x] Bloque 0 - Base de control
- [~] Bloque 1 - Catálogo LIMS base
- [~] Bloque 2 - Valores de referencia y resultados
- [~] Bloque 3 - Recepción y órdenes
- [ ] Bloque 4 - Pacientes
- [ ] Bloque 5 - Clientes
- [ ] Bloque 6 - Médicos
- [~] Bloque 7 - Cotización
- [~] Bloque 8 - Cobranza
- [~] Bloque 9 - Auditoría
- [~] Bloque 10 - Seguridad y permisos
- [ ] Bloque 11 - Programa de lealtad
- [ ] Bloque 12 - Microbiología
- [~] Bloque 13 - Reportes
- [~] Bloque 14 - Integraciones externas
- [ ] Bloque 15 - Validación final de reemplazo

Leyenda:
- `[x]` cerrado
- `[~]` parcialmente cerrado
- `[ ]` pendiente

## Bloque 0 - Base de control

- [x] Matriz de migración creada
- [x] Anexo técnico creado
- [x] Plan de cierre por prioridades creado
- [x] Plan de cierre por bloques creado

## Bloque 1 - Catálogo LIMS base

- [x] `Analito` definido
- [x] `ValorReferenciaAnalito` definido
- [x] `PerfilLims` definido
- [x] `PaqueteLims` definido
- [x] `PrecioItem` definido
- [x] `ensamblar_lims_v75` definido
- [~] Catálogo final 1:1 contra legado
- [~] Cardinalidad exacta validada
- [~] Nombres exactos validados

## Bloque 2 - Valores de referencia y resultados

- [x] Captura y PDF ya muestran referencias
- [x] Soporte de rangos numéricos y textuales
- [x] Compatibilidad con captura vieja y nueva
- [~] Validación final por sexo / edad
- [~] Casos pediátricos revisados con evidencia final
- [~] Impresión igual al legacy al 100%

## Bloque 3 - Recepción y órdenes

- [x] Selección de estudios robustecida
- [x] Backend acepta `estudios` y `estudio_ids`
- [x] Validación de orden vacía endurecida
- [~] Cobro completo validado en producción con todos los casos
- [~] Matching exacto de formulario vs sistema legado
- [~] Flujo de edición en vivo completamente cerrado

## Bloque 4 - Pacientes

- [ ] Campos de ficha comparados uno a uno
- [ ] Campos extra configurables revisados
- [ ] Expediente con pestañas equivalentes
- [ ] Validación de cambio de nombre comparada
- [ ] Geografía dinámica comparada

## Bloque 5 - Clientes

- [ ] Catálogo de clientes replicado
- [ ] Tarifa base validada
- [ ] Bloqueo / activación validado
- [ ] Sucursales permitidas validadas
- [ ] Estudios por cliente validados
- [ ] Facturación especial validada

## Bloque 6 - Médicos

- [ ] Catálogo médico comparado
- [ ] Médico que refiere validado
- [ ] Entrega de solicitudes físicas validada
- [ ] Comisión por médico validada
- [ ] Reportes por médico comparados

## Bloque 7 - Cotización

- [x] Consulta inválida corregida
- [~] Cálculo comercial comparado
- [~] PDF de cotización comparado
- [~] Conversión a orden comparada

## Bloque 8 - Cobranza

- [~] Pago mixto validado de forma funcional
- [~] Efectivo, tarjeta y transferencia soportados
- [~] Anticipo y cancelación revisados
- [~] Monedero y bonos comparados con legado

## Bloque 9 - Auditoría

- [~] Base de auditoría funcional
- [~] Eventos críticos registrados
- [ ] Exportaciones y filtros idénticos al legacy
- [ ] Cobertura completa de actividades comparada

## Bloque 10 - Seguridad y permisos

- [x] Arquitectura multitenant y roles ya existe
- [x] Read-only / modo de contingencia existe
- [~] Paridad exacta de permisos por rol
- [~] Mapa de permisos del legacy replicado

## Bloque 11 - Programa de lealtad

- [ ] Monedero equivalente al legacy
- [ ] Reglas de acumulación equivalentes
- [ ] Excepciones de clientes equivalentes
- [ ] Reportes equivalentes

## Bloque 12 - Microbiología

- [ ] Catálogo de bacterias validado
- [ ] Catálogo de antibióticos validado
- [ ] Grupos de antibiograma validados
- [ ] Despliegue automático por prueba validado

## Bloque 13 - Reportes

- [~] Resultados y laboratorio ya soportan parte del flujo
- [ ] Corte por sucursal replicado
- [ ] Ventas por cliente replicado
- [ ] Caja replicada
- [ ] Cobranza pendiente replicada
- [ ] Exámenes realizados replicado
- [ ] Tiempos de proceso replicado
- [ ] Inventario / matriz replicados

## Bloque 14 - Integraciones externas

- [~] TuLab soportado parcialmente
- [~] CFDI / facturación soportado parcialmente
- [~] Interfaces de analizadores soportadas parcialmente
- [ ] WhatsApp validado como en legacy
- [ ] DICOM PACs validado
- [ ] EvaPacs validado
- [ ] S3 / adjuntos comparados

## Bloque 15 - Validación final

- [ ] P0 completo
- [ ] P1 mayormente completo
- [ ] Operación diaria sin parches
- [ ] Validación visual final aprobada
- [ ] Aceptación como reemplazo total

## Próximo orden de trabajo recomendado

1. Terminar Bloque 1 al 3 al nivel de paridad exacta.
2. Cerrar Bloques 4, 5 y 6.
3. Cerrar Bloque 13 porque impacta operación diaria.
4. Cerrar Bloques 11, 12 y 14.
5. Ejecutar Bloque 15 como auditoría final.

