# REVISION CODEX - SEGURIDAD DE SCRIPTS PRISLAB 2026-06-21

## Decision ejecutiva

La matriz "auditorias *_full.py = seguras / solo lectura" queda **RECHAZADA**.

Motivo: varias auditorias management crean o modifican datos reales mediante ORM. No deben ejecutarse en produccion sin refactor a modo read-only, backup y/o sandbox.

## Evidencia clave

### stress_test_extremo.py

Clasificacion: **DEPRECATED / NO EJECUTAR**

Evidencia:
- `core/management/commands/stress_test_extremo.py` lanza `CommandError` al inicio de `handle()`.
- Mensaje: opera sobre catalogo legacy y pide usar LIMS v7.5.

### auditoria_farmacia_full.py

Clasificacion: **ESCRITURA PELIGROSA / SANDBOX**

Evidencia:
- Linea 175: `Empresa.objects.get_or_create(...)`
- Linea 180: `User.objects.get_or_create(...)`
- Linea 230: `Producto.objects.get_or_create(...)`
- Linea 251: `Lote.objects.get_or_create(...)`
- Linea 356: `Venta.objects.create(...)`
- Linea 368: `DetalleVenta.objects.create(...)`
- Linea 377: `Pago.objects.create(...)`

Conclusion: no es solo lectura. Crea datos operativos, venta, detalle y pago.

### auditoria_lab_full.py

Clasificacion: **DEPRECATED / NO EJECUTAR**

Evidencia:
- Linea 105: `raise CommandError(...)`
- Linea 106: mensaje de catalogo legacy.
- Codigo posterior tambien crearia empresa, usuario, paciente, estudio, orden y detalle si se removiera el bloqueo.

### auditoria_medico_full.py

Clasificacion: **ESCRITURA CONTROLADA/PERIGROSA / SANDBOX**

Evidencia:
- Linea 132: `Empresa.objects.get_or_create(...)`
- Linea 138: `User.objects.get_or_create(...)`
- Linea 154: `User.objects.get_or_create(...)`
- Linea 178: `Paciente.objects.get_or_create(...)`
- Linea 191: `Medico.objects.get_or_create(...)`

Conclusion: no es solo lectura.

### auditoria_core_full.py

Clasificacion: **ESCRITURA CONTROLADA / LOCAL O SANDBOX**

Evidencia:
- Linea 261: `Empresa.objects.get_or_create(...)`
- Linea 266: `User.objects.get_or_create(...)`

Nota adicional:
- En la lectura se observo posible bug de nombre de metodo: se define `extraer_enlaces` pero se invoca `extract_enlaces` en una rama del flujo. Validar antes de ejecutar.

## Matriz corregida

### Permitido ahora

Solo:
- `manage.py check`
- tests unitarios/focalizados en BD de test
- Playwright/API smoke que no hagan POST destructivo ni creen ventas reales
- scripts que se demuestre por codigo que no usan `create`, `update`, `delete`, `get_or_create`, `update_or_create`, `bulk_create`, `save`, `call_command` destructivo ni APIs POST operativas

### No aprobado en produccion

- `auditoria_core_full`
- `auditoria_farmacia_full`
- `auditoria_lab_full`
- `auditoria_medico_full`
- `stress_test_extremo`
- `war_room_stress_test`
- `generar_data_operativa_v150`
- `simular_ventas_farmacia`
- `simular_ventas_farmacia_completo`
- cualquier script que cree ventas, pacientes, ordenes, pagos, productos, lotes, PDFs o archivos storage

### Permitido solo si se refactoriza

Los management `auditoria_*_full.py` pueden ser utiles, pero necesitan:
- flag `--read-only`
- flag `--empresa-id`
- no crear datos por defecto
- no usar empresas ficticias
- no crear usuarios con passwords hardcodeados
- no crear ventas/pagos reales
- reporte JSON/MD sin mutar BD

## Instruccion para Claude/Cascada

No ejecutar Fase 1 como estaba planteada.

Nueva tarea:
1. Revisar solo scripts candidatos Playwright/API.
2. Confirmar si hacen POST o si solo hacen GET.
3. Si hacen POST, clasificar como "requiere sandbox".
4. Proponer lista final de scripts verdaderamente read-only.
5. No ejecutar management commands `auditoria_*_full.py` en produccion.

## Estado operativo separado

Codex ya corrigio y desplego:
- busqueda pacientes laboratorio sin `curp`
- validacion fecha agenda
- importador farmacia con `empresa_id` en lotes
- catalogo farmacia cargado en produccion

Produccion:
- productos: 693
- productos con stock: 265
- lotes: 715
- lotes activos: 287
