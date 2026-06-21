# RESPUESTA CODEX - AUDITORIA 3 BLOQUES 2026-06-21

## Estado

Recibido y procesado el reporte `AUDITORIA_COMPLETA_3BLOQUES_2026-06-21.md`.

## H1 - Farmacia PDV sin productos

**Clasificacion Codex:** CONFIRMADO COMO OPERATIVO, no bug de PDV.

Evidencia:
- El endpoint PDV devuelve productos correctamente cuando existen registros `Producto` para la empresa.
- Existe Excel versionado: `Productos-farmacia-2026-02-10-10-31.xlsx`.
- Dry-run local del comando:
  - `python manage.py importar_excel_inventario Productos-farmacia-2026-02-10-10-31.xlsx --empresa-id 1 --dry-run`
  - Encabezado detectado: fila 3
  - Filas de datos: 716
  - Productos unicos: 674
  - Lotes: 716
  - Errores: 0

Accion pendiente en VPS:

```bash
cd /opt/prislab/app
sudo -u prislab .venv/bin/python manage.py importar_excel_inventario Productos-farmacia-2026-02-10-10-31.xlsx --empresa-id 1 --reset-stock
sudo systemctl restart prislab-gunicorn prislab-celery prislab-celerybeat
```

## H2 - PRIS Sentinel en busqueda de pacientes laboratorio

**Clasificacion Codex:** CONFIRMADO Y CORREGIDO.

Causa raiz:
- `/laboratorio/pacientes/?q=...` filtraba por `curp__icontains`.
- El modelo canonico `core.Paciente` no tiene campo `curp`.
- Django lanza `FieldError`; Sentinel lo enmascara como pantalla de reparacion.

Fix:
- `core/views/laboratorio.py`: se reemplazo `curp__icontains` por filtros existentes:
  - `nombres__icontains`
  - `apellido_paterno__icontains`
  - `apellido_materno__icontains`
- `core/templates/core/lab_pacientes/lista.html`: placeholder actualizado.

## H3 - Fecha de agendamiento acepta entrada ambigua

**Clasificacion Codex:** CONFIRMADO Y CORREGIDO EN UI.

Fix:
- `consultorio/views.py`: agrega `fecha_min` y `fecha_max` al contexto.
- `consultorio/templates/consultorio/agendar_cita.html`: input fecha con `min`, `max`, ayuda visual y `setCustomValidity`.
- Backend ya rechazaba fechas pasadas y mayores a 365 dias; se mantiene.

## Pruebas

Nuevo archivo:
- `core/tests/test_auditoria_funcional_20260621.py`

Pruebas incluidas:
- `/laboratorio/pacientes/?q=Prueba` renderiza sin Sentinel y muestra paciente.
- Agendamiento expone `type=date`, `min`, `max` y ayuda.
- PDV devuelve producto cuando el catalogo tiene datos.

Resultado:

```text
python manage.py test core.tests.test_auditoria_funcional_20260621 --keepdb -v 1
Ran 3 tests in 5.398s
OK
```

## Verificacion adicional

```text
python manage.py check
System check identified no issues (0 silenced).
```

## Pendiente real

1. Commit/push de este fix.
2. Deploy en VPS.
3. Ejecutar importacion de farmacia en VPS con empresa 1.
4. Reintentar auditoria funcional:
   - Farmacia PDV: buscar `paracetamol`.
   - Pacientes laboratorio: buscar `Prueba`.
   - Consultorio agenda: intentar fecha fuera de rango y fecha valida.
