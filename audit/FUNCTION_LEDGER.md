# Ledger de funciones Python

Generado: `2026-08-24T20:52:40.434290Z`

## Resumen

- Archivos Python propios: **1299**
- Funciones/métodos descubiertos: **5140**
- Funciones productivas: **3652**
- Funciones productivas sin demostración conductual individual: **3652**
- Errores de sintaxis/lectura: **0**
- Señales estáticas sin disposición: **0**
- Grupos de redefiniciones sombreadas: **6**

> `static_review_passed` sólo significa que el AST se pudo inspeccionar y no activó las señales incluidas. No demuestra corrección funcional.

## Evidencia conductual

- No se proporcionó evidencia de cobertura instrumentada.

> La cobertura demuestra ejecución de sentencias/ramas, no corrección semántica ni suficiencia de las aserciones.

## Conteo por categoría

| Categoría | Funciones |
|---|---:|
| application | 896 |
| management_command | 822 |
| migration | 62 |
| model | 479 |
| service | 344 |
| test | 1318 |
| tooling | 108 |
| view | 1111 |

## Definiciones marcadas

| ID | Disposición | Señales | Evidencia |
|---|---|---|---|
| `completar_todo_funcional.py::run_cmd@19` | intentional_safe | process_execution | argv tokenized with shlex and executed without a shell |
| `config/admin_site.py::mark_safe_header@263` | requires_hardening | html_trust_boundary | unused helper trusts arbitrary text as safe HTML |
| `core/management/commands/backup_database.py::Command.handle@45` | intentional_safe | process_execution | pg_dump receives an argv list and credentials through the environment |
| `core/management/commands/backup_nocturno.py::Command._respaldo_base_datos@234` | intentional_safe | process_execution | pg_dump receives a settings-derived argv list |
| `core/management/commands/restaurar_backup.py::Command._pg_restore@122` | intentional_safe | process_execution | pg_restore receives an argv list and a validated dump path |
| `core/management/commands/restaurar_backup.py::Command._psql_restore@161` | intentional_safe | process_execution | psql receives an argv list and a validated SQL path |
| `core/management/commands/stress_test_extremo.py::Command._detener_procesos_huerfanos@167` | requires_hardening | process_execution | pkill uses a broad process-name pattern and is not portable |
| `core/migrations/0052_notificacionpanico_fk_ordendeservicio.py::_noop_reverse@46` | generated_migration_noop | empty_body | forward-only data repointing |
| `core/migrations/0053_repoint_ia_iot_fk_ordendeservicio.py::backwards@53` | generated_migration_noop | empty_body | forward-only foreign-key repointing |
| `core/migrations/0058_resultadoparametro_analito_lims.py::_noop_reverse@77` | generated_migration_noop | empty_body | forward-only LIMS data consolidation |
| `core/migrations/0063_tejido_blando_v75_marketing_academy.py::_noop_reverse@13` | generated_migration_noop | empty_body | forward-only data population |
| `core/migrations/0067_resultadoparametro_ia_ethics_p18.py::noop_reverse@11` | generated_migration_noop | empty_body | forward-only audit data population |
| `core/migrations/0069_detalleorden_drop_legacy_estudio_id.py::_noop_reverse@32` | generated_migration_noop | empty_body | destructive legacy-column removal cannot restore data |
| `core/migrations/0070_repair_client_mutation_columns.py::_noop_reverse@45` | generated_migration_noop | empty_body | idempotent schema repair has no meaningful reverse |
| `core/migrations/0073_conveniopreciolims_and_legacy_lab_drop.py::_noop_reverse@45` | generated_migration_noop | empty_body | destructive legacy-catalog consolidation |
| `core/migrations/0078_remove_default_pin_and_disable_emergency_bypass.py::noop_reverse@9` | generated_migration_noop | empty_body | security cleanup must not restore insecure defaults |
| `core/migrations/0092_configuracionmodulos_pin_precio_neto_4_digitos.py::noop_reverse@15` | generated_migration_noop | empty_body | data validation cleanup is forward-only |
| `diagnose_and_fix_tests.py::run_tests_capture_failures@16` | intentional_safe | process_execution | test runner receives a fixed argv list |
| `e2e_test_prod.py::curl@8` | intentional_safe | process_execution | curl receives caller arguments as an argv list with timeouts |
| `generar_migraciones_consolidacion.py::main@12` | intentional_safe | process_execution | Django command receives a controlled argv list |
| `inventario/migrations/0003_salidaanaliticalab_idempotency_key.py::_noop@18` | generated_migration_noop | empty_body | generated idempotency keys are not safely reversible |
| `inventario/migrations/0004_consumoestudioreactivo_analito_lims.py::_noop@124` | generated_migration_noop | empty_body | forward-only LIMS mapping |
| `scripts/run_manage_with_env.py::main@36` | intentional_safe | process_execution | manage.py receives command-line arguments as an argv list |

## Colisiones de definición

| Nombre | Disposición | Definiciones |
|---|---|---|
| `core/models/base.py::Usuario.sucursal` | intentional_descriptor_pair | `core/models/base.py::Usuario.sucursal@467`<br>`core/models/base.py::Usuario.sucursal@476` |
| `core/models/base.py::Usuario.sucursal_id` | intentional_descriptor_pair | `core/models/base.py::Usuario.sucursal_id@493`<br>`core/models/base.py::Usuario.sucursal_id@499` |
| `mantenimiento/views/helpers.py::_empresa` | shadowed_redefinition | `mantenimiento/views/helpers.py::_empresa@14`<br>`mantenimiento/views/helpers.py::_empresa@66` |
| `mantenimiento/views/helpers.py::_req_empresa` | shadowed_redefinition | `mantenimiento/views/helpers.py::_req_empresa@18`<br>`mantenimiento/views/helpers.py::_req_empresa@72` |
| `mantenimiento/views/helpers.py::_req_empresa.inner` | shadowed_redefinition | `mantenimiento/views/helpers.py::_req_empresa.inner@21`<br>`mantenimiento/views/helpers.py::_req_empresa.inner@76` |
| `mantenimiento/views/helpers.py::_get_ip` | shadowed_redefinition | `mantenimiento/views/helpers.py::_get_ip@30`<br>`mantenimiento/views/helpers.py::_get_ip@85` |
| `seguridad/views/helpers.py::_empresa_staff_o_redirect` | shadowed_redefinition | `seguridad/views/helpers.py::_empresa_staff_o_redirect@10`<br>`seguridad/views/helpers.py::_empresa_staff_o_redirect@57` |
| `seguridad/views/helpers.py::_empresa_staff_o_json` | shadowed_redefinition | `seguridad/views/helpers.py::_empresa_staff_o_json@21`<br>`seguridad/views/helpers.py::_empresa_staff_o_json@68` |

## Limitación obligatoria

Este ledger garantiza censo AST de las definiciones Python dentro del alcance declarado. No permite afirmar que cada función sea correcta: para eso cada función productiva debe quedar enlazada a una prueba conductual y cobertura de ramas, y las integraciones deben verificarse en el entorno objetivo.
