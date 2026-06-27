# CONTABILIDAD / FINANZAS — ESTADO FINAL DE CIERRE (CFDI 4.0 + superficie financiera)

**Fecha:** 2026-06-26 (última revisión)  
**Rama/entorno:** release V1.0 local  
**Responsable:** Cascade / revisión de módulo

---

## 1. Estado resumido

| Frente | Estado | Justificación |
| --- | --- | --- |
| **CFDI 4.0 multi-tenant** | **CERRADO** | Modelo, migraciones, vistas, servicio de timbrado, admin y tests validados. Empresa FK canonizada a `NOT NULL`. Filtrado directo por `empresa` en todas las operaciones. Tests OK. |
| **Reportes financieros** | **CERRADO** | `reportes_financieros.py` usa `timezone.localdate()`, `empresa`, roles. Tests de reporte, Excel y zona horaria pasan. Balance General sigue siendo un stub documentado, pero carga y se puede exportar. |
| **Caja Lab / Caja Farmacia / Master Dashboard** | **CERRADO** | `finanzas.py` usa `UserPassesTestMixin` con roles correctos y `localdate()`. Tests de seguridad y zona horaria pasan. |
| **Autofactura pública** | **CERRADO** | `autofactura_publica` tiene rate limiting, validación, bandeja interna protegida. Tests de seguridad pasan. |
| **Contabilidad personal** | **CERRADO** | Solo `DIRECTOR`; usa `user_passes_test`. Tests de acceso pasan. |
| **Motor financiero / reporte de caja** | **CERRADO** | Se agregaron `@role_required` y se alineó `localdate()`. Se agregó URL y tests de regresión. |
| **Cuentas por cobrar + convenios** | **ABIERTO** | El código `@core/views/cuentas_por_cobrar.py` no está en `URLconf`; faltan templates `core/cuentas_por_cobrar.html` y `core/convenios_lista.html`. Se higienizó con `@role_required` y `localdate()` pero no se puede declarar operativo. |
| **Catálogo de cuentas / pólizas / balance real** | **ABIERTO** | Vistas en `@core/views/contabilidad.py` son stubs que redirigen. No hay modelos de catálogo, pólizas ni asientos contables. |
| **Módulo Contabilidad / Finanzas completo** | **ABIERTO** | Aunque la superficie operativa (CFDI, reportes, caja, autofactura, contabilidad personal, motor financiero) está cerrada, queda deuda estructural de contabilidad formal y CxC. |

---

## 2. Hallazgos confirmados

- **CFDI 4.0 multi-tenancy canonizada**  
  - `FacturaCFDI.empresa` es `NOT NULL` desde `@contabilidad/migrations/0011_facturacfdi_empresa_not_null.py`.  
  - `FacturaCFDI.cfdi_empresa_scope_id` devuelve directamente `self.empresa_id` en `@contabilidad/models.py`.  
  - Todas las queries y bloqueos de `FacturaCFDI` usan `empresa` directamente en `@contabilidad/views.py` y `@contabilidad/services/timbrado_cfdi.py`.  
  - El admin de `FacturaCFDI` incluye `empresa` en list_display, list_filter y fieldsets en `@contabilidad/admin.py`.  

- **Timbrado idempotente y sin fugas de tenant**  
  - `ejecutar_timbrado` hace `select_for_update(nowait=True).get(id=factura_id, empresa=empresa)` y bloquea las fuentes de operación.  
  - `FacturamaAPI.timbrar_cfdi` usa clave determinista `idempotency_key` basada en `empresa_id` y `factura_id`.  

- **Cálculo de IVA en borrador automático**  
  - `_split_iva_incluido_16` en `@contabilidad/services/cfdi_borrador_auto.py` redondea a 2 decimales con `ROUND_HALF_UP`.  

- **Validadores SAT**  
  - RFC genérico, RFC persona moral, CP, limpieza de nombre fiscal. Tests en `@contabilidad/tests/test_validators_cfdi40.py` pasan.  

- **Seguridad en superficie financiera**  
  - Se agregaron `@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')` a `@core/views/motor_financiero.py` (`genera_reporte_caja`, `api_resumen_ejecutivo_pris`) y a `@core/views/cuentas_por_cobrar.py` (`api_registrar_pago_cxc`, `api_crear_cxc`, `convenios_lista`, `api_crear_convenio`, `reporte_fiscal_mensual`).  
  - Se alineó `timezone.localdate()` en `@core/views/motor_financiero.py` y `@core/views/cuentas_por_cobrar.py` para evitar desfases UTC.  
  - Se agregó ruta `/reportes/api/resumen-ejecutivo/` en `@config/urls.py` para el API que estaba huérfano.  

- **Migrations limpias**  
  - `makemigrations --check` reporta `No changes detected`.  
  - `check` del sistema no arroja advertencias.  

---

## 3. Hallazgos descartados

- **“test_cfdi_borrador_auto tenía 22 tests OK”** → **Descartado**. El archivo solo contiene **2 tests** (`test_borrador_desde_pago_lab` y `test_borrador_desde_venta_farmacia`). El conteo correcto es **2 OK**.  
- **“Falta migración de empresa”** → **Descartado**. La migración `@contabilidad/migrations/0011_facturacfdi_empresa_not_null.py` ya existe y se aplica.  
- **“Timbrado no está aislado por tenant”** → **Descartado**. Los queries de timbrado usan `empresa=empresa` directamente.  

---

## 4. Archivos modificados en esta revisión

- `@contabilidad/models.py` (empresa NOT NULL, `cfdi_empresa_scope_id`).  
- `@contabilidad/views.py` (filtros directos por `empresa`).  
- `@contabilidad/services/timbrado_cfdi.py` (scope por `empresa` en lock y recuperación).  
- `@contabilidad/admin.py` (empresa en admin).  
- `@contabilidad/migrations/0011_facturacfdi_empresa_not_null.py` (backfill + NOT NULL).  
- `@core/views/motor_financiero.py` (role_required, localdate).  
- `@core/views/cuentas_por_cobrar.py` (role_required, localdate).  
- `@config/urls.py` (ruta `/reportes/api/resumen-ejecutivo/`).  
- `@templates/core/reporte_fiscal.html` (stub mínimo para test de reporte fiscal).  
- `@core/tests/test_finanzas_roles_regression.py` (nuevo, 10 tests de regresión de roles).  

---

## 5. Tests ejecutados (validación reproducible)

Comando:

```bash
python manage.py test \
  contabilidad.tests \
  core.tests.test_finanzas_roles_regression \
  core.tests.test_reportes_financieros_regression \
  core.tests.test_finanzas_caja_tz \
  core.tests.test_contabilidad_personal \
  core.tests.test_e2e_cfdi \
  --verbosity=2 --keepdb
```

**Resultado:**

```
Ran 65 tests in 58.142s
OK (skipped=1)
```

| Archivo de test | Tests | Resultado |
| --- | --- | --- |
| `@contabilidad/tests/test_finanzas_seguridad.py` | ~29 | OK |
| `@contabilidad/tests/test_cfdi_borrador_auto.py` | 2 | OK |
| `@contabilidad/tests/test_validators_cfdi40.py` | 12 | OK |
| `@core/tests/test_e2e_cfdi.py` | 6 (+1 skipped) | OK |
| `@core/tests/test_reportes_financieros_regression.py` | 2 | OK |
| `@core/tests/test_finanzas_caja_tz.py` | 1 | OK |
| `@core/tests/test_contabilidad_personal.py` | 3 | OK |
| `@core/tests/test_finanzas_roles_regression.py` | 10 | OK |
| **Total** | **65** | **OK (1 skipped)** |

El test skipped (`test_timbrado_concurrente_una_llamada_api_cuando_hay_lock_real`) es esperado porque SQLite no soporta `select_for_update` con bloqueo real.

---

## 6. Riesgos residuales

- **Cuentas por cobrar / convenios** no están en `URLconf` y faltan templates. Cualquier intento de habilitar las rutas fallará con `TemplateDoesNotExist`. El código ya está higienizado, pero sigue sin ser accesible para usuarios.  
- **Catálogo de cuentas, pólizas y balance real** no existen como modelos ni funcionalidad. Los stubs en `@core/views/contabilidad.py` redirigen y no generan asientos contables.  
- **Ruta duplicada `/contabilidad/`**: existe el `include('contabilidad.urls')` y luego `path('contabilidad/', views.dashboard_contabilidad)`. Actualmente Django resuelve por orden; no produce error, pero es confuso y puede dejar el dashboard fuera de alcance si el include gana.  
- **Integración PAC**: los tests de timbrado usan un mock. En producción, la integración con Facturama requiere credenciales y manejo de errores de red.  
- **MovimientoCaja**: en `test_finanzas_seguridad` se ve el warning `empresa sin sucursales; no se puede crear MovimientoCaja`. No es un error de test, pero indica que reportes de caja real pueden no reflejar movimientos si la empresa no tiene sucursales.  

---

## 7. Tareas pendientes para declarar “CERRADO” al módulo completo

Para poder marcar el módulo **Contabilidad / Finanzas** como cerrado, quedan las siguientes tareas:

1. **Modelado contable real** (catálogo de cuentas, asientos, pólizas, balance general real).  
2. **Vistas y templates de Cuentas por Cobrar / Convenios** (wirar `@core/views/cuentas_por_cobrar.py` a `URLconf`, crear templates, validar flujo de crédito).  
3. **Balance General operativo** (reemplazar stub en `@core/views/contabilidad.py` y `@core/views/reportes_financieros.py` por un reporte basado en el catálogo de cuentas).  
4. **Revisar la ruta duplicada `/contabilidad/`** y dar un prefijo consistente al dashboard de contabilidad o al include de `contabilidad.urls`.  
5. **Pruebas de integración con PAC** (staging o sandbox) para validar timbrado real.  
6. **Auditoría de permisos** sobre cualquier nueva vista financiera (aplicar `@role_required`/`UserPassesTestMixin` y `empresa` desde el inicio).  

---

## 8. Recomendación

- **CFDI 4.0 multi-tenant: se puede declarar CERRADO.** No reabrir salvo que surja un nuevo defecto o cambio de alcance.  
- **Módulo Contabilidad / Finanzas: NO CERRADO.** Se recomienda cerrar la deuda estructural (puntos 1–4 de la sección 7) antes de emitir un estado final de módulo completo.  
- **No se debe hacer merge a producción de CxC/convenios hasta que tengan URL y templates.**  

---

*Validaciones reproducibles:*

```bash
python manage.py test contabilidad.tests core.tests.test_finanzas_roles_regression core.tests.test_reportes_financieros_regression core.tests.test_finanzas_caja_tz core.tests.test_contabilidad_personal core.tests.test_e2e_cfdi --keepdb
python manage.py makemigrations --check
python manage.py check
```
