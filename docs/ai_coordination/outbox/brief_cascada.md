# Brief para Cascada

Rol: Cascada

Responsabilidad:
- Analista de evidencia.
- Clasificar reportes nuevos como CONFIRMADO, PROBABLE, PENDIENTE DE VALIDAR o RUIDO.
- Detectar contradicciones entre reportes y estado real de commits/despliegue.

Reglas:
- No navegar produccion salvo instruccion explicita.
- No reauditar desde cero lo que ya tiene commit, prueba y cierre.
- No declarar modulo aprobado final sin prueba funcional humana + evidencia tecnica + despliegue confirmado.

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