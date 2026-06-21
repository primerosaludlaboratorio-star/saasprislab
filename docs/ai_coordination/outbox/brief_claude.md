# Brief para Claude

Rol: Claude

Responsabilidad:
- Auditoria funcional humana en produccion cuando el navegador este estable.
- Probar flujos reales sin saltarse pasos.
- Reportar paso exacto, esperado, resultado real y si bloquea operacion.

Reglas:
- Si falla Chrome/extensiones, marcar LIMITACION DE HERRAMIENTA.
- No clasificar 500/login/timeouts como bug funcional sin logs.
- Antes de concluir, capturar URL, usuario, paso, mensaje visible y respuesta API si existe.

## Estado Compartido

Foco actual: Laboratorio: validacion funcional en produccion

## Cerrado

- Busqueda de pacientes devuelve JSON controlado
- Contrato LIMS crea orden con tokens analito/perfil
- LAB_VALIDATION_PIN falla cerrado sin configuracion

## Pendiente

- Auditoria funcional humana completa de Laboratorio
- Confirmar despliegue VPS de efa5c2f y b4f210c
- Validar cancelacion con devolucion financiera
- Definir/probar storage final: Vultr Object Storage, Drive o buffer local
- Monitorear conexiones idle PostgreSQL

## Evidencia Reciente


## Instruccion

Trabaja solo sobre esta evidencia y el codigo actual. Si necesitas clasificar, usa:
CONFIRMADO, PROBABLE, PENDIENTE_VALIDAR, OPERATIVO, LIMITACION_HERRAMIENTA, RUIDO.