# Brief para Codex

Rol: Codex

Responsabilidad:
- Cerrar codigo y causa raiz de hallazgos reales.
- Agregar pruebas automaticas cuando el riesgo lo amerite.
- Hacer commits trazables y actualizar documentos de control.
- Separar problema funcional, problema operativo y limitacion de herramienta.

Reglas:
- No asumir que un reporte externo es cierto sin evidencia.
- Si hay bug real, corregirlo y verificar.
- Si el problema ya esta cerrado con commit/prueba, marcarlo como cerrado y no reabrirlo.

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