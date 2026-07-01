PRISLAB — scripts_cursor_e2e (Cursor)
====================================
Suite de fiabilidad / regresión HTTP+templates para doble validación frente a otras herramientas (p. ej. Cascade).

Ejecutar desde la raíz del repo:
  python scripts_cursor_e2e/run_cursor_reliability_suite.py

Equivale a etiquetar los módulos bajo scripts_cursor_e2e/tests/ en manage.py test.

Notas técnicas (v1.49):
- Modo inventario lab: **`test_09`** cubre **`/director/sucursales/modo-inventario-lab/`** (roles director/admin vía **`is_staff`** + empresa).

Notas técnicas (v1.48):
- Migración core 0069: elimina columna legada estudio_id en core_detalleorden si existe (SQLite/Postgres), alineada con ORM LIMS sin ese campo.
- Tests que validan PDF tras «validar» (test_01, test_02) sustituyen temporalmente el storage del FileField archivo_resultado por FileSystemStorage en un directorio temporal, porque credenciales Drive en máquinas de desarrollo no aplican al CI ni a runners locales sin scope.
