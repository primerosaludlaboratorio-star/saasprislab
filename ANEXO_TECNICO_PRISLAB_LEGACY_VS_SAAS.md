# Anexo técnico: PRISLAB legado vs PRISLAB SaaS

Fecha de corte: 2026-06-06

Este anexo integra el reporte técnico del sistema legado de laboratorio con el estado actual de PRISLAB SaaS, para convertirlo en una guía de cierre funcional y técnico.

El objetivo no es solo migrar pantallas, sino reproducir la operación real del laboratorio con la misma profundidad funcional.

## 1) Diferencias de plataforma

### Sistema legado
- ASP.NET MVC
- IIS 10
- Bootstrap + jQuery 2.1.1
- AJAX para modales y altas rápidas
- AWS S3 para adjuntos
- CKEditor para textos enriquecidos
- DataTables con soporte a acentos

### PRISLAB SaaS
- Django / Python
- Nginx + Gunicorn
- PostgreSQL
- Redis + Celery
- Catálogo LIMS normalizado
- Renderizado server-side + flujos JS modernos

### Implicación
PRISLAB SaaS no debe copiar la tecnología anterior, sino igualar:
- comportamiento
- datos
- reglas
- permisos
- exportaciones
- experiencia operativa

## 2) Capa de pacientes

### Lo que hace el legado
- nombre, apellidos, apellido materno
- clave automática
- sexo
- fecha de nacimiento o edad
- teléfono, dirección, email múltiple, comentario
- vínculo a cliente
- hasta 6 campos extra configurables
- módulo extendido COVID / epidemiológico
- cambio de nombre con confirmación explícita
- carga dinámica de estados/ciudades por AJAX
- pestañas de membresía, comparativo histórico, fotografía, QR por email, consentimientos

### Equivalente en PRISLAB SaaS
- existe base de pacientes y expediente
- existe soporte para flujo clínico
- existe estructura para integración con historial y órdenes

### Brecha
- validar que los campos de captura y los extras opcionales existan o estén parametrizados
- confirmar que los componentes de expediente equivalgan en visibilidad y flujo
- validar si la lógica COVID/legacy debe migrarse como módulo documental o solo como compatibilidad

## 3) Capa de clientes

### Lo que hace el legado
- clave, nombre, emails, teléfonos
- tarifa base
- bloqueo / activación
- sucursales permitidas
- estudios por cliente
- facturación con reglas específicas
- sucursales del cliente
- exclusión de TuLab
- 26 clientes activos con mezcla de maquila, instituciones y asistenciales

### Equivalente en PRISLAB SaaS
- existe estructura comercial y multitenant
- existe relación con tarifas y órdenes

### Brecha
- confirmar la paridad de:
  - bloqueo de cliente
  - catálogos por cliente
  - reglas de facturación
  - sucursales permitidas
  - exclusión de portal de resultados

## 4) Capa de médicos

### Lo que hace el legado
- nombre, especialidad, teléfono, email
- médico que refiere
- entrega de solicitudes físicas
- comisión por médico
- catálogo grande de más de mil médicos

### Equivalente en PRISLAB SaaS
- el flujo de médico existe y participa en órdenes

### Brecha
- validar:
  - campo médico que refiere
  - especialidad visible en búsquedas
  - reportes por médico
  - entrega de solicitudes físicas
  - comisiones

## 5) Capa de órdenes

### Lo que hace el legado
- paciente, médico, cliente, tarifa, sucursal
- tipo de orden
- diagnóstico
- folio de cliente
- hora de toma y entrega
- factura
- notas
- campos extra
- agente de ventas
- carga y edición de estudios en línea
- detección de duplicados
- promociones
- carga masiva
- integración con facturación electrónica

### Equivalente en PRISLAB SaaS
- recepción / cobro de órdenes
- laboratorio operativo
- soporte de perfiles, paquetes y cobro mixto

### Brecha
- validar que el formulario final de órdenes tenga la misma cobertura de campos
- confirmar que los campos extra y los flujos de edición en vivo coinciden
- revisar si la importación masiva de órdenes debe migrarse o replantearse

## 6) Capa de cobranza

### Lo que hace el legado
- efectivo
- tarjeta crédito
- tarjeta débito
- transferencia
- cheque
- bono
- monedero electrónico
- banco / depósito
- certificado
- pagos mixtos
- anticipo
- cancelación con motivo

### Equivalente en PRISLAB SaaS
- existe cobro de órdenes y soporte de abonos / CxC

### Brecha
- validar cada forma de pago
- validar el comportamiento de monedero
- validar cancelaciones, anticipo y cierre de orden

## 7) Capa de resultados

### Lo que hace el legado
- muestra código, abreviatura, resultado, rango de referencia, último resultado, unidades
- estados: pendiente, capturado, validado, impreso, publicado
- validación con permiso específico
- publicación en portal
- último resultado e histórico
- adjuntos en resultados
- integración con analizador

### Equivalente en PRISLAB SaaS
- ya existe construcción de resultados e impresión
- ya se corrigió el manejo de rangos de referencia

### Brecha
- validar visualmente:
  - rangos por sexo/edad
  - marcas de fuera de rango
  - estados y validación
  - publicación o exportación final
  - adjuntos embebidos

## 8) Capa de cotización

### Lo que hace el legado
- cotizador independiente
- cliente / tarifa / factura
- médico opcional
- PDF con detalle de lo incluido
- promociones
- conversión a orden

### Equivalente en PRISLAB SaaS
- existe cotización

### Brecha
- validar que el cálculo comercial sea idéntico
- validar impresión y conversión

## 9) Capa de auditoría

### Lo que hace el legado
- 15 entidades auditadas
- 31 actividades en órdenes
- filtros por fecha, usuario, tipo, actividad, referencia
- exportación a Excel

### Equivalente en PRISLAB SaaS
- existe auditoría y logging

### Brecha
- igualar filtros, nomenclatura y exportación
- validar que se registren las mismas clases de eventos críticos

## 10) Seguridad y permisos

### Lo que hace el legado
- 20 secciones de permisos
- 80+ permisos funcionales
- 4 perfiles base

### Equivalente en PRISLAB SaaS
- existe arquitectura multitenant + roles + read-only + superusers

### Brecha
- replicar el mapa de permisos del negocio
- validar que la operación diaria no dependa de permisos inexistentes o demasiado amplios

## 11) Programa de lealtad

### Lo que hace el legado
- monedero por paciente
- saldo
- vencimiento
- excepciones por cliente
- uso como descuento

### Equivalente en PRISLAB SaaS
- existe base para módulos financieros, pero no se ha cerrado paridad total

### Brecha
- implementar o igualar el monedero funcional
- validar reglas de acumulación y redención

## 12) Microbiología

### Lo que hace el legado
- catálogo de bacterias
- catálogo de antibióticos
- grupos de antibiograma
- despliegue automático según prueba

### Equivalente en PRISLAB SaaS
- existe infraestructura de laboratorio, pero requiere paridad fina

### Brecha
- migrar catálogo completo
- validar comportamiento automático al capturar resultados

## 13) Integraciones externas

### Legado
- TuLab
- WhatsApp
- CFDI / WeeCompany
- interfaces a analizadores
- DICOM PACs
- EvaPacs
- S3

### PRISLAB SaaS
- ya contiene varias integraciones o infraestructura para ellas

### Brecha
- validar una por una
- decidir cuáles quedan en el reemplazo inmediato y cuáles pasan a fase 2

## 14) Conclusión técnica

PRISLAB SaaS ya está alineado en la columna vertebral clínica:
- pruebas
- referencias
- perfiles
- paquetes
- tarifas
- órdenes
- resultados

Lo que falta para reemplazo total no es la idea, sino la equivalencia funcional exacta con el legado en:
- captura de pacientes
- clientes y médicos
- formas de pago
- auditoría detallada
- lealtad
- microbiología
- integraciones externas

Este anexo debe usarse junto con:
- `MATRIZ_MIGRACION_PRISLAB_VS_PRISLAB_SAAS.md`
- `PLAN_CIERRE_MIGRACION_PRISLAB.md`

