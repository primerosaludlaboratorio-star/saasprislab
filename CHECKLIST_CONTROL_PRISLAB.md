# Checklist de control PRISLAB

Fecha de corte: 2026-06-18

Este checklist consolida el estado de la migración entre el sistema legado y PRISLAB SaaS.
La intención es tener un tablero único para avanzar sin perder contexto.

## Protocolo obligatorio de actualización

Toda IA, desarrollador o revisor que haga cambios en código, despliegue, pruebas, variables, infraestructura o datos debe actualizar este archivo en el mismo movimiento.

También debe actualizar:

- [REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md)
- [PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md](C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master\PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md) si cambia el enfoque de auditoría o la forma oficial de revisión

Si este checklist no se actualiza, el cambio no cuenta como cerrado.

## Estado técnico de corte

- [x] `manage.py check` OK
- [x] `makemigrations --check --dry-run` OK
- [x] `manage.py test` global OK (`251 tests`, `23 skipped`, `0 failures`, `0 errors`)
- [x] Endurecimiento post-auditoría aplicado en `settings.py`, `docker-compose.yml` y `nginx/conf.d/prislab.conf`
- [x] Regresión focalizada post-endurecimiento OK (`16 tests`, `0 failures`)
- [x] Hallazgos reales de auditoría cerrados en código: rate limit con IP final de `X-Forwarded-For` y bloqueo de cantidades no válidas en `registrar_venta_farmacia`
- [x] Regresión de auditoría adicional OK (`4 tests`, `0 failures`) en `core.tests.test_rate_limit_middleware` y `core.tests.test_pris_tools_operativos_security`
- [x] Endurecimiento adicional aplicado: `PRISLAB_TENANT_STRICT_MODE`, `buscar_o_crear_paciente` ya no crea sin confirmación, y `OMNI_BYPASS_TOKEN` queda bloqueado por defecto en producción salvo habilitación explícita
- [x] Regresión de endurecimiento final OK (`4 tests`, `0 failures`) en `core.tests.test_tenant_strict_mode` y `core.tests.test_buscar_o_crear_paciente_confirmation`
- [x] `PRIS IA` desbloqueado del stub y flujo real activo
- [x] `Academia` cubierta con pruebas y blindaje tenant
- [x] Integración Google Drive unificada a Service Account centralizada (`GOOGLE_APPLICATION_CREDENTIALS` / `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`) con scope único `https://www.googleapis.com/auth/drive`
- [~] Verificación real contra VPS ejecutada: la cuenta de servicio carga, pero el `GOOGLE_DRIVE_FOLDER_ID` actual en producción responde `404 notFound`; falta corregir el ID real de carpeta o compartir exactamente esa carpeta con la cuenta de servicio
- [~] Producción funcional localmente validada; falta seguir la verificación manual módulo por módulo en el entorno real

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
- [x] Google Drive centralizado por Service Account
- [x] Manejo explícito de errores `403` / `404` en capa Drive
- [~] Carpeta maestra de Google Drive validada en producción
- [ ] Subida real de archivo a carpeta maestra confirmada en producción
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

1. Ejecutar revisión externa de Claude y Cascada usando como fuente inicial este checklist y el reporte maestro.
2. Continuar pruebas funcionales reales en producción módulo por módulo.
3. Terminar Bloque 1 al 3 al nivel de paridad exacta contra el legacy.
4. Cerrar Bloques 4, 5 y 6.
5. Cerrar Bloque 13 porque impacta operación diaria.
6. Cerrar Bloques 11, 12 y 14.
7. Ejecutar Bloque 15 como auditoría final de reemplazo total.
