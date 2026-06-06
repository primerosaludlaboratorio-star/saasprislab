# Plan de cierre bloque por bloque - PRISLAB

Fecha de corte: 2026-06-06

Este documento descompone la migración del sistema legado de laboratorio hacia PRISLAB SaaS en bloques ejecutables.
La idea es cerrar cada bloque con evidencia, no solo con código “parecido”.

## Bloque 0 - Base de control

### Objetivo
Tener una fuente única de verdad para comparar sistema legado vs SaaS.

### Entregables
- Matriz de migración
- Anexo técnico
- Plan de cierre por prioridades

### Evidencia requerida
- Documento comparativo firmado como referencia de trabajo
- Lista de módulos con estado y brecha

### Estado actual
- Hecho

---

## Bloque 1 - Catálogo LIMS base

### Objetivo
Igualar la estructura clínica mínima del laboratorio.

### Incluye
- Analitos
- Valores de referencia
- Perfiles
- Paquetes
- Tarifas

### Tareas concretas
1. Comparar el catálogo legado contra `Analito`.
2. Verificar rangos por sexo y edad en `ValorReferenciaAnalito`.
3. Confirmar que `PerfilLims` respete el orden técnico del legacy.
4. Confirmar que `PaqueteLims` respete la composición comercial.
5. Sincronizar `PrecioItem` con la tarifa activa.

### Archivos clave
- `lims/models.py`
- `lims/management/commands/ensamblar_lims_v75.py`
- `datos_lims/`

### Criterio de cierre
- El catálogo importa sin pérdida funcional.
- Los conteos y relaciones coinciden con el sistema actual.

### Estado actual
- Parcialmente hecho

---

## Bloque 2 - Valores de referencia y resultados

### Objetivo
Mostrar resultados con rangos correctos en captura, impresión y PDF.

### Incluye
- ref_min
- ref_max
- texto de referencia
- referencia por sexo
- referencia por edad
- referencias críticas

### Tareas concretas
1. Validar que cada analito tenga su rango correcto.
2. Probar casos pediátricos.
3. Probar casos por sexo.
4. Probar referencias textuales.
5. Confirmar que el PDF imprime el mismo criterio que la captura.

### Archivos clave
- `core/services/resultados_impresion_presentacion.py`
- `core/templates/core/resultados_print.html`
- `core/templates/core/laboratorio/captura_resultados.html`

### Criterio de cierre
- El usuario ve el mismo rango en pantalla y en PDF.
- No hay resultados “vacíos” cuando existe catálogo.

### Estado actual
- Parcialmente hecho

---

## Bloque 3 - Recepción y órdenes

### Objetivo
Crear, editar, cobrar y confirmar órdenes sin errores de payload o validación.

### Incluye
- paciente
- médico
- cliente
- tarifa
- estudios
- perfiles
- paquetes
- hora de toma
- hora de entrega
- diagnóstico
- notas
- factura
- cobro mixto

### Tareas concretas
1. Verificar selección de estudios.
2. Verificar que frontend y backend hablen el mismo idioma.
3. Probar cobro exacto.
4. Probar cobro mixto.
5. Probar CxC y cortesía.
6. Probar confirmación final de orden.

### Archivos clave
- `core/templates/core/recepcion_lab.html`
- `core/views/laboratorio.py`

### Criterio de cierre
- No aparece el error de “Debes agregar al menos un estudio” cuando sí hay estudios.
- La orden queda confirmada y cobrada.

### Estado actual
- Parcialmente hecho

---

## Bloque 4 - Pacientes

### Objetivo
Reproducir la ficha del paciente y sus extras clave.

### Incluye
- datos de identificación
- fecha de nacimiento o edad
- contacto
- vínculo a cliente
- campos extra
- membresía
- comparativo histórico
- fotografía
- QR por email
- consentimientos

### Tareas concretas
1. Comparar campos obligatorios.
2. Comparar edición de nombre con confirmación.
3. Comparar buscador y autocompletado.
4. Validar extras configurables.
5. Validar pestañas del expediente.

### Criterio de cierre
- La captura y edición del paciente se comportan como el legado en los campos críticos.

### Estado actual
- Pendiente de paridad fina

---

## Bloque 5 - Clientes

### Objetivo
Igualar la lógica comercial y de catálogo institucional.

### Incluye
- clave
- nombre
- emails
- teléfonos
- tarifa base
- bloqueo
- sucursales permitidas
- estudios por cliente
- reglas de facturación
- sucursales del cliente
- exclusión de TuLab

### Tareas concretas
1. Comparar clientes activos del legado.
2. Validar relación con tarifa.
3. Validar bloqueo/desbloqueo.
4. Validar catálogos por cliente.
5. Validar facturación especial.

### Criterio de cierre
- Un cliente del legado puede operarse igual en SaaS.

### Estado actual
- Pendiente de paridad fina

---

## Bloque 6 - Médicos

### Objetivo
Reproducir la ficha médica y su relación con órdenes y reportes.

### Incluye
- nombre
- especialidad
- teléfono
- email
- médico que refiere
- entregas físicas
- comisiones

### Tareas concretas
1. Validar alta y edición.
2. Validar búsqueda y asignación.
3. Validar reportes por médico.
4. Validar médico que refiere.
5. Validar estructura de comisiones.

### Criterio de cierre
- La orden puede usar médico exactamente como el flujo real lo requiere.

### Estado actual
- Pendiente de paridad fina

---

## Bloque 7 - Cotización

### Objetivo
Reproducir presupuestos y conversión a orden.

### Incluye
- cliente
- tarifa
- factura
- médico opcional
- promociones
- PDF de cotización
- conversión a orden

### Tareas concretas
1. Comparar cálculo de totales.
2. Comparar promociones.
3. Comparar impresión PDF.
4. Comparar conversión a orden.

### Criterio de cierre
- El cotizador produce los mismos importes y reglas que el legacy.

### Estado actual
- Parcialmente hecho

---

## Bloque 8 - Cobranza

### Objetivo
Igualar todos los métodos de pago y reglas financieras de la orden.

### Incluye
- efectivo
- tarjeta crédito
- tarjeta débito
- transferencia
- cheque
- bono
- monedero
- banco
- certificado
- pagos mixtos
- anticipo
- cancelación

### Tareas concretas
1. Verificar cada forma de pago.
2. Verificar pago mixto.
3. Verificar cancelación con motivo.
4. Verificar anticipo.
5. Verificar validación de saldo.

### Criterio de cierre
- La orden se paga igual que en el sistema actual.

### Estado actual
- Parcialmente hecho

---

## Bloque 9 - Auditoría

### Objetivo
Registrar y consultar la actividad con la misma trazabilidad del legacy.

### Incluye
- órdenes
- pacientes
- médicos
- clientes
- pre-órdenes
- agenda
- pruebas
- perfiles
- paquetes
- login
- muestras
- cotización
- tarifas
- interfaz
- usuarios

### Tareas concretas
1. Validar filtros.
2. Validar exportación.
3. Validar eventos críticos.
4. Validar cambios de precios y resultados.

### Criterio de cierre
- La bitácora permite investigar la operación igual o mejor que el legacy.

### Estado actual
- Parcialmente hecho

---

## Bloque 10 - Seguridad y permisos

### Objetivo
Igualar la operación real por roles sin romper el día a día.

### Incluye
- usuarios
- perfiles
- permisos por módulo
- read-only
- superusuarios

### Tareas concretas
1. Comparar perfiles del legacy.
2. Validar permisos críticos.
3. Validar bloqueo de escritura en modos especiales.
4. Validar que admin y recepción operen según corresponda.

### Criterio de cierre
- Ningún rol queda con permisos peligrosos o faltantes para la operación diaria.

### Estado actual
- Base robusta, paridad fina pendiente

---

## Bloque 11 - Programa de lealtad

### Objetivo
Reproducir monedero, excepciones y reportes.

### Incluye
- saldo
- vencimiento
- acumulación
- redención
- clientes excluidos
- saldo por paciente
- monederos redimidos

### Tareas concretas
1. Validar reglas de acumulación.
2. Validar excepciones.
3. Validar redención.
4. Validar reportes.

### Criterio de cierre
- El sistema maneja el monedero con la misma lógica comercial del legacy.

### Estado actual
- Pendiente

---

## Bloque 12 - Microbiología

### Objetivo
Reproducir el catálogo y despliegue automático de antibiograma.

### Incluye
- bacterias
- antibióticos
- grupos
- sensibilidad
- despliegue automático por prueba

### Tareas concretas
1. Validar catálogo completo.
2. Validar grupos.
3. Validar despliegue automático.
4. Validar captura de sensibilidad.

### Criterio de cierre
- El antibiograma funciona de forma equivalente al legacy.

### Estado actual
- Pendiente

---

## Bloque 13 - Reportes

### Objetivo
Reproducir los reportes críticos del laboratorio.

### Incluye
- corte por sucursal
- ventas por cliente
- caja
- cobranza pendiente
- exámenes realizados
- hoja de trabajo
- exámenes por médico
- tiempos de proceso
- detalle de resultados
- inventario y matriz
- comisiones

### Tareas concretas
1. Comparar exportaciones.
2. Comparar filtros.
3. Comparar formatos.
4. Comparar contenido de totales.

### Criterio de cierre
- Los reportes operativos clave coinciden con el legado.

### Estado actual
- Parcialmente hecho

---

## Bloque 14 - Integraciones externas

### Objetivo
Cerrar dependencias externas que son parte de la operación real.

### Incluye
- TuLab
- WhatsApp
- CFDI / WeeCompany
- interfaces a analizadores
- DICOM PACs
- EvaPacs
- S3

### Tareas concretas
1. Separar integraciones críticas de integraciones diferibles.
2. Validar cada una por flujo real.
3. Confirmar credenciales y secretos.
4. Documentar su estado de activación.

### Criterio de cierre
- Las integraciones usadas en operación real están vivas o correctamente planificadas.

### Estado actual
- Mixto

---

## Bloque 15 - Validación final de reemplazo

### Objetivo
Decidir si PRISLAB SaaS ya puede reemplazar al sistema legado.

### Checklist final
- catálogo LIMS completo
- referencias correctas
- órdenes estables
- cobro estable
- pacientes iguales en operación
- clientes equivalentes
- médicos equivalentes
- cotización equivalente
- auditoría suficiente
- seguridad razonable
- reportes críticos disponibles
- microbiología y lealtad resueltas o formalmente pospuestas

### Criterio de salida
PRISLAB SaaS puede declararse reemplazo operativo cuando:
- los bloques P0 están cerrados
- la mayoría de P1 está cerrada
- no quedan huecos funcionales en laboratorio, recepción y cobro

---

## 16) Prioridad inmediata sugerida

1. Bloque 1: Catálogo LIMS base
2. Bloque 2: Resultados y referencias
3. Bloque 3: Recepción y órdenes
4. Bloque 13: Reportes críticos
5. Bloques 4, 5, 6, 7 y 8
6. Bloques 9, 10, 11, 12 y 14

