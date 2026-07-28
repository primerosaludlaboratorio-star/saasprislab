# Arquitectura multi-tenant de interfases de laboratorio

## Principio

Las interfases INCCA, Icon y Wondfo son capacidades reutilizables del producto PRISLAB. Cualquier tenant podrá activarlas si su equipo y configuración son compatibles.

La activación de una interfase no comparte datos clínicos, operativos ni credenciales entre tenants.

## Tres capas separadas

### 1. Plantilla técnica global

Se conserva como conocimiento del producto:

- Protocolo de comunicación.
- Formato de mensajes o archivos.
- Reglas de parseo y validación.
- Nombre/código del método del fabricante.
- Unidades permitidas.
- Manejo de duplicados, cuarentena y reenvío.
- Manuales e insertos públicos del fabricante.
- Versión del adaptador.

Esta capa no contiene pacientes, lotes, resultados, IP privadas, credenciales ni reglas clínicas exclusivas de un laboratorio.

### 2. Configuración privada del tenant

Cada empresa configura de forma aislada:

- Equipo, número de serie y sucursal.
- Métodos realmente montados.
- Mapeo método-equipo-analito de su catálogo.
- Reactivos, lotes, controles y calibradores.
- Volúmenes confirmados en su equipo.
- Unidades y factores de conversión aprobados.
- Rangos y valores críticos autorizados.
- IP, puerto, carpeta, API key y secretos.
- Responsables de validación y liberación.

### 3. Datos operativos del tenant

Nunca se comparten entre empresas:

- Pacientes y órdenes.
- Resultados y mensajes recibidos.
- Mediciones CCI/Westgard.
- Inventarios y consumos.
- Alertas, cuarentenas y auditoría.
- Evidencias de validación.

## Regla de activación

Un tenant puede activar una interfase global únicamente después de completar su configuración privada y validarla. La activación debe ser por equipo y método, no global para todos los tenants.

Estados recomendados:

1. `DISPONIBLE`: adaptador instalado y documentado.
2. `CONFIGURADA`: tenant registró equipo y parámetros privados.
3. `EN_PRUEBA`: recepción controlada sin liberar resultados automáticamente.
4. `VALIDADA`: responsable del tenant aprobó mapeos, unidades y pruebas.
5. `ACTIVA`: recepción operativa habilitada.
6. `SUSPENDIDA`: error, mantenimiento, calibración vencida o riesgo de integridad.

## Exportación y portabilidad

Cada tenant debe poder exportar sus datos sin llevarse secretos de otro tenant:

- Catálogo y mapeos propios.
- Configuración de equipos sin secretos o con secretos separados.
- Inventario y consumos.
- Resultados y trazabilidad.
- CCI/Westgard.
- Auditoría y evidencias.

Las plantillas globales se versionan por PRISLAB. Los datos del tenant se exportan mediante paquetes separados, con tenant, versión, fecha y hash.

## Aplicación a PRISLAB

PRISLAB es el tenant de trabajo actual. Sus nombres de métodos, equipos, reactivos, lotes, controles, calibradores, rangos y credenciales son datos privados de PRISLAB y no deben convertirse en valores por defecto de otros tenants.

El modelo `MetodoEquipo` conserva la relación privada `empresa + equipo + analito`; los adaptadores de comunicación y sus reglas de transporte permanecen reutilizables.

La configuración operativa se materializa en `laboratorio.InterfazEquipo`. Sus perfiles actuales son `INCCA_CSV`, `ICON_HL7` y `WONDFO_HL7`, con estados de activación y modo sombra. El receptor de resultados exige resolver empresa y equipo antes de aplicar mapeos, cuarentena o integración clínica. Una interfaz recién creada no puede publicar resultados porque inicia en `CONFIGURADA/SOMBRA`.
