# Plan de integración clínica e interfases

La arquitectura multi-tenant aplicable está definida en `docs/manual/ARQUITECTURA_INTERFASES_MULTI_TENANT.md`: los adaptadores son globales y reutilizables; los métodos, equipos, catálogos, lotes, rangos, resultados y secretos son privados de cada tenant.

## Objetivo

Convertir los manuales, insertos y configuraciones de equipos en reglas clínicas y operativas verificables para PRISLAB, sin inventar datos, sin mezclar equipos y sin activar una interfase en producción antes de probarla en cuarentena.

## Estado real de las fuentes

### Fuentes disponibles

- INCCA: manual operativo y protocolo de conectividad bidireccional LIS.
- INCCA: métodos actuales con nombres exactos del equipo y volúmenes de muestra, R1 y R2.
- INCCA: controles C1 y C2 con rangos `-2SD/+2SD` activos.
- Point Scientific: insertos técnicos de reactivos y calibrador HDL/LDL.
- Icon: manual del operador y protocolo HL7 Norma-3.
- Wondfo Finecare FS113: SOP de conectividad LIS.
- HB936: inserto de bilirrubina directa para Hitachi; no está confirmado como Wondfo.

La fuente estructurada de métodos está en `datos_lims/INCCA_metodos_fuente.csv`. El mapa contra el catálogo está en `datos_lims/INCCA_mapeo_catalogo.csv`; sus 16 códigos quedaron confirmados documentalmente, pero los métodos permanecen en `PENDIENTE_VALIDACION` e inactivos hasta la validación operativa en el equipo.

La asociación método-inserto está en `docs/manual/fuentes/incca/INCCA_METODOS_FUENTES_CLINICAS.csv`. Actualmente hay 15 insertos trazables y falta el inserto específico de hierro Point Scientific. El comando `python manage.py auditar_fuentes_clinicas_incca` verifica esta relación sin modificar la base de datos.

La implementación local ya contiene el modelo tenant-aware `MetodoEquipo`, su migración `laboratorio.0018_metodoequipo`, el comando de simulación/carga protegida `cargar_metodos_incca` y las auditorías de fuente. La carga real no activa métodos: todos quedan `PENDIENTE_VALIDACION` e inactivos hasta evidencia del equipo y aprobación responsable.

La capa reutilizable de interfaces ya está implementada en `laboratorio.InterfazEquipo` y `laboratorio.Equipo`: permite configurar por tenant los perfiles `INCCA_CSV`, `ICON_HL7` y `WONDFO_HL7`, además de ASTM y JSON. La recepción HL7/ASTM/JSON existente usa cuarentena, Decimal, idempotencia y validación de unidad; ahora resuelve el equipo dentro de la empresa solicitante y no por IP global. Todas las interfaces nuevas nacen en modo `SOMBRA` y estado `CONFIGURADA`.

### Datos que no deben considerarse todavía reglas activas

- Interferencias no asociadas al método exacto.
- Rangos clínicos no confirmados para población, edad, sexo y unidad del laboratorio.
- Parámetros extraídos de archivos binarios sin campo documentado.
- Configuración de red, puertos o credenciales incluidas en documentos operativos.
- Métodos que aparecen en insertos pero no están confirmados como montados en el equipo.

## Prioridad de implementación

### Fase 1 — Catálogo estructurado y trazabilidad documental

Crear una ficha estructurada por método con:

- Nombre exacto del equipo.
- Analito canónico del catálogo LIMS.
- Equipo y fabricante.
- Inserto fuente y versión.
- Tipo de muestra, tubo y volumen.
- Reactivo, lote, caducidad y presentación.
- Volúmenes de muestra, R1, R2 y otros reactivos.
- Calibrador y control aplicables.
- Unidad, linealidad y rangos documentados.
- Interferencias y limitaciones.
- Fecha y responsable de validación.

**Criterio de salida:** ningún método queda activo si no tiene fuente, equipo, analito y unidad identificados.

### Fase 2 — Motor clínico seguro

Las reglas se habilitarán por capas:

1. **Preanalítica:** muestra, tubo, volumen, estabilidad, almacenamiento y rechazo.
2. **Analítica:** método, equipo, reactivo, lote, calibración, control, linealidad e interferencias.
3. **Control de calidad:** C1/C2, media, desviación, reglas Westgard y estado del lote.
4. **Postanalítica:** unidad, rango de referencia, valor crítico, delta check, banderas y validación humana.
5. **Inventario:** descuento por analito y consumo real por prueba, repetición y equipo.

**Regla de seguridad:** una alerta clínica no debe bloquear automáticamente un resultado salvo que exista una regla validada y aprobada; en los demás casos debe poner el resultado en revisión y explicar la causa.

### Fase 3 — Interfases en laboratorio controlado

Implementar adaptadores separados, no una lógica genérica compartida sin configuración:

- INCCA: bidireccional LIS según protocolo del fabricante.
- Icon: HL7 para biometría de 3 partes, con mapeo de flags y lotes.
- Wondfo FS113: conectividad según `ReceiveFormTemp` y protocolo validado.

La configuración de cada equipo se registra en `InterfazEquipo`; los adaptadores son globales y la configuración de IP, carpetas, códigos, unidades y secretos es privada del tenant. No se guarda ninguna clave en el modelo: solo se registra el nombre de la variable de entorno que debe contenerla.

Cada adaptador debe tener:

- Modo simulación.
- Cola de cuarentena.
- Idempotencia por mensaje.
- Registro de trama original.
- Mapeo de código y unidad.
- Rechazo de analito desconocido.
- Rechazo de unidad incompatible.
- Auditoría de usuario/equipo/tenant.
- Reenvío controlado después de corregir un mapeo.

### Fase 4 — Pruebas funcionales y clínicas

Antes de producción se deben ejecutar, por equipo:

- Resultado normal.
- Resultado fuera de rango.
- Valor crítico.
- Unidad incorrecta.
- Analito desconocido.
- Orden inexistente.
- Mensaje duplicado.
- Mensaje incompleto.
- Reactivo/lote no vigente.
- Control fuera de Westgard.
- Interferencia documentada.
- Repetición de prueba.
- Desconexión y reenvío.
- Dos tenants aislados.
- Validación humana y rechazo humano.

**Criterio de salida:** cero mensajes huérfanos sin explicación, cero duplicados persistidos y 100% de las tramas de prueba con trazabilidad.

### Fase 5 — Despliegue progresivo

1. Validación local con fixtures y archivos reales anonimizados.
2. Staging con PostgreSQL y configuración equivalente a producción.
3. Producción en modo recepción controlada o sombra, sin publicar resultados automáticamente.
4. Comparación equipo → receptor → resultado LIMS.
5. Activación por equipo y método después de aprobación del químico responsable.
6. Monitoreo de cuarentena, unidades, analitos huérfanos, errores y latencia.

## Qué se puede hacer ahora

- Mantener los documentos en el repositorio canónico.
- Crear el catálogo estructurado de métodos, equipos, reactivos, controles e insertos.
- Asociar los 16 métodos actuales del INCCA y sus volúmenes documentados.
- Asociar C1 y C2 a sus rangos de control.
- Preparar mapeos de códigos sin activar recepción productiva.
- Crear fixtures y pruebas de cuarentena, duplicidad, unidad y tenant.
- Repetir la migración en PostgreSQL de staging y cargar los 16 métodos para el tenant PRISLAB con `--apply`, manteniéndolos inactivos.
- Registrar en PRISLAB los perfiles `INCCA_CSV`, `ICON_HL7` y `WONDFO_HL7` en estado `EN_PRUEBA/SOMBRA`, sin liberar resultados automáticamente.

## Qué requiere validación del laboratorio

- Rangos de referencia clínicos vigentes.
- Población, edad y sexo aplicables.
- Interferencias que deben generar alerta o solo advertencia.
- Métodos realmente montados en cada equipo.
- Reactivo y lote actualmente usados.
- Puerto, IP y formato real de cada interfase.
- Usuario responsable de aprobar resultados y cambios.
- Criterio de liberación ante alerta clínica.

## Qué no debe hacerse todavía

- No activar HL7/LIS directamente en producción.
- No convertir todos los insertos en reglas clínicas automáticas.
- No usar un inserto Hitachi como si fuera Wondfo.
- No importar rangos sin unidad y población definida.
- No descontar inventario solo por nombre parecido del reactivo.
- No publicar documentos que contengan credenciales o datos de red sin redacción.

## Criterio de cierre enterprise

Un equipo se considera integrado únicamente cuando existe evidencia de documento fuente, ficha estructurada, mapeo de código, validación de unidad, prueba normal, prueba de error, cuarentena, reenvío, auditoría, control de calidad y flujo humano de aprobación en staging y producción controlada.
