# Instrucción final — Programador (PRISLAB v7.5 / cierre v1.28)

**Fecha de referencia:** 2026-04-04  
**Ámbito:** LIMS v7.5, PrisMath (Punto 10), handshake HL7 (Punto 13), deuda de esquema §9.1.

---

## Estado sellado en código (resumen)

- **PrisMath:** `core/services/clinical_math.py` + captura industrial + tests `core.tests.test_clinical_math`.
- **HL7 (Punto 13):** `laboratorio/services/hl7_handshake.py` (normalización de unidades, `Decimal` sin `float` intermedio en el camino crítico), `laboratorio/views/hl7_receptor.py` (cuarentena + War Room), modelo **`laboratorio.ResultadoHL7Huerfano`**, tipos **`HL7_MAPEO`** / **`HL7_CUARENTENA`** en `inventario.NotificacionDiscrepancia`. Admin: cola de cuarentena registrada.
- **Migraciones de este cierre:** `laboratorio.0013_hl7_huerfano_y_notif`, `inventario.0005_notificaciondiscrepancia_tipo_hl7`. **No** se versionó `core.0065` masivo (sigue bloqueado §9.1).

---

## Siete pasos para producción

1. **`migrate`** en staging (Postgres): aplicar en orden habitual de dependencias; confirmar **`laboratorio.0013`** e **`inventario.0005`** aplicadas.
2. **Secretos y HL7:** `HL7_ACTIVE`, `HL7_API_KEY`, `HL7_ALLOWED_IPS`, `CRON_SECRET`, `FERNET_KEY`, `SECRET_KEY` (producción ≥ 50 caracteres aleatorios). Cabecera **`X-EMPRESA-ID`** en el middleware/equipo para que cuarentena y notificaciones tengan tenant.
3. **Cron Cloud Scheduler:** verificar `X-Cron-Secret` en `/cron/check-stock-critico/` y resto de jobs; War Room recibe `NotificacionDiscrepancia`.
4. **Catálogo LIMS:** en analitos integrados por HL7, rellenar **`Analito.unidades`** con la misma cadena que enviará el equipo (normalización: mayúsculas, espacios alrededor de `/`). Si el catálogo deja unidades vacías, **no** se exige coincidencia (compatibilidad legado; documentar procedimiento).
5. **Pruebas:**  
   `python manage.py test core.tests.test_guardian_v53 inventario.tests.test_critical_stock core.tests.test_clinical_math laboratorio.tests.test_hl7_handshake --noinput`  
   `python manage.py check --deploy` → **0 errores**; advertencias W004/W008/… son esperables en entorno local sin HTTPS completo; en Cloud Run deben alinearse con la guía del maestro §3.
6. **§9.1 (Día D):** antes de `makemigrations` masivo en `core`/`lims`, backup, staging, `remap_placeholder_resultados` / `ensamblar_lims_v75` según runbook; **no** generar `core.0065` hasta acta explícita.
7. **Revisión QC HL7:** monitorizar **`ResultadoHL7Huerfano`** y notificaciones **`HL7_*`** en War Room; resolver mapeos/unidades y reenviar tramas tras corrección en catálogo o conversión aprobada.

---

## Verificación registrada (local 2026-04-04)

- `check --deploy`: **0 errores**, 6 advertencias de seguridad típicas de desarrollo (HSTS, `DEBUG`, cookies secure, etc.).
- `showmigrations --plan`: revisar salida filtrada por `core`, `lims`, `inventario`, `farmacia`, `marketing`, `iot`, `laboratorio` en el entorno de despliegue.
- Tests unitarios rápidos: `laboratorio.tests.test_hl7_handshake` + `core.tests.test_clinical_math` en verde.

---

*Documento generado bajo gobernanza `DOCS_AUDIT_MAESTRO.md`.*
