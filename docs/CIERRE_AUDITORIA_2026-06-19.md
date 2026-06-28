# Cierre de Auditoría - 19 de junio de 2026

## Alcance
Continuación de la corrección de hallazgos críticos, altos, medios y bajos del informe de auditoría estricta del 2026-06-19. No se agregaron nuevas funcionalidades; solo correcciones verificables y tests de regresión.

## Estado de los fixes cerrados

### Críticos
- **A1 - `import os` faltante en PDF de laboratorio**
  - Archivo: `core/views/laboratorio.py`
  - Se agregó `import os` en la ruta alterna de generación de PDF.

- **A2 - Reporte guardado en storage retorna `success` ficticio**
  - Archivo: `core/views/laboratorio_reportes.py`
  - `api_generar_y_guardar_reporte` ahora devuelve `STORAGE_ERROR` con HTTP 503 cuando `guardar_reporte_en_storage` retorna `None`.

- **A3 - Catálogo médico con unicidad global**
  - Archivo: `core/models/catalogos.py`
  - `Medico.cedula_profesional` ahora es único por `(empresa, cedula_profesional)`.
  - Migración generada: `core/migrations/0077_alter_medico_cedula_profesional_and_more.py`.

- **A4 - API de búsqueda de venta para devolución no sincronizada**
  - Archivo: `core/views/farmacia.py`
  - `buscar_venta_devolucion` acepta `busqueda` y `folio`, y devuelve `cliente`, `cajero_original` y `detalles`.
  - Archivo: `core/templates/core/devoluciones.html`
  - URL corregida a `/farmacia/devoluciones/buscar/?busqueda=`.

- **A5 - Tests con credenciales hardcodeadas**
  - Archivos: `test_final_verification.py`, `test_laboratorio_full_e2e.py`, `test_farmacia_pdv_e2e.py`, `test_farmacia_full_user_flow.py`
  - Contraseñas eliminadas; ahora usan `PRISLAB_TEST_PASSWORD` y validan existencia en runtime.

### Medios
- **M1 - Worklist PDF no filtra perfiles/paquetes por departamento**
  - Archivo: `core/views/laboratorio.py`
  - Filtro ampliado con `Q` para incluir `detalles__perfil_lims__analitos__departamento` y `detalles__paquete_lims__analitos__departamento`.

- **M2 - Permisos partidos entre grupo y campo `rol`**
  - Estado: **PENDIENTE de revisión arquitectónica por Claude/Codex**. No se aplicó parche mínimo para evitar romper flujos existentes.

### Bajos
- **B1 - `agendar_cita` no conserva el nombre del paciente al fallar validación**
  - Archivo: `consultorio/templates/consultorio/agendar_cita.html`
  - Campo de búsqueda ahora tiene `name="paciente_nombre"`.
  - Archivo: `consultorio/views.py`
  - `_rerender_form` incluye `paciente_nombre` en `form_data`.

- **B2 - Rol `RECEPCION` redirige a laboratorio**
  - Archivo: `core/views/general.py`
  - Redirección cambiada de `recepcion_lab` a `consultorio:tablero_recepcion`.

- **B3 - Devoluciones no persisten auditoría granular por producto**
  - Archivo: `core/services/ventas/venta_farmacia_service.py`
  - `registrar_devolucion_resultado` ahora acepta `productos`, valida que los `detalle_id` pertenezcan a la venta y los guarda en `observaciones` de `SalesReturn`.
  - Archivo: `core/tests/test_devoluciones_farmacia_api.py`
  - Nuevo test `test_procesar_devolucion_con_productos_auditoria`.

### Otros fixes de seguridad/integridad ya presentes
- Verificación WebAuthn bloqueada (`core/views/voice.py`).
- Endpoints Sentinel restringidos a POST y token explícito (`core/views/sentinel_api.py`).
- `resetear_password` ya no eleva a `is_staff`/`is_superuser` (`reset_password.py`).
- `provision_usuarios_base` requiere variables de entorno (`core/management/commands/provision_usuarios_base.py`).
- `api_test_github_sentinel` ya no expone token parcial (`consultorio/views.py`).
- Ordenes de laboratorio se crean con `estado='PENDIENTE_PAGO'`.
- Kiosko público no muta estado operativo a `EN_PROCESO`.
- Impresión de etiquetas de farmacia retorna `501` si no puede generar PDF real.
- Agenda de consultorio filtrada por médico asociado al usuario.
- Formulario `agendar_cita` no exige médico cuando no hay médicos configurados.

## Riesgo arquitectónico pendiente
- **A6 - Doble árbol funcional de farmacia**
  - `core/views/farmacia.py` y `core/templates/core/devoluciones.html` forman el PDV/punto de venta.
  - La app `farmacia/` es el ERP administrativo con modelos propios (`DevolucionVenta`, `AperturaCaja`, etc.).
  - Existen URLs solapadas (ej. `/farmacia/devoluciones/buscar/` resuelta por ambos árboles).
  - Decisión: **Pendiente de revisión de Claude/Codex** para unificar en un solo módulo o separar prefijos claramente.

## Regresiones ejecutadas

```powershell
.venv\Scripts\python manage.py check
.venv\Scripts\python manage.py makemigrations --check --dry-run
.venv\Scripts\python manage.py test core.tests --verbosity=2
.venv\Scripts\python manage.py test consultorio.tests --verbosity=2
```

| Suite | Resultado |
|-------|-----------|
| `manage.py check` | OK (0 silenced) |
| `makemigrations --check --dry-run` | No changes detected |
| `core.tests` | OK (128 tests, 2 skipped) |
| `consultorio.tests` | OK (26 tests, 4 skipped) |

## Archivos de referencia
- `CHECKLIST_CONTROL_PRISLAB.md` contiene el checklist detallado con todos los cierres.
- `INFORME_AUDITORIA_ESTRICTA_2026-06-19.md` contiene el informe base de auditoría.
- `REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md` contiene el reporte previo del sistema.

## Fecha de cierre del documento
2026-06-19

## Preparado para revisión
Codex / Claude
