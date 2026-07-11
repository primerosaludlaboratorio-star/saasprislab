# Revalidación de Hallazgos Críticos — PRISLAB SaaS
**Fecha:** 2026-07-11  
**Realizado por:** Copilot Coding Agent (revalidación post-auditoría externa)  
**Cobertura:** H1-06, H2-01, H2-03, H3-01, H5-01, H1-03, H1-04, H4-02, H4-03

---

## Resumen Ejecutivo

| ID    | Título breve                                 | Estado             |
|-------|----------------------------------------------|--------------------|
| H1-06 | Cross-tenant data leak LIMS                  | ✅ FALSE POSITIVE  |
| H2-01 | Sentinel admin_token derivado de SECRET_KEY  | ✅ FIXED           |
| H2-03 | resetear_password eleva is_staff/is_superuser| ✅ FIXED           |
| H3-01 | Rutas de impresión de lab con reglas distintas| ✅ FIXED           |
| H5-01 | provision_usuarios_base con contraseñas por defecto | ✅ FIXED    |
| H1-03 | Contraseñas hardcodeadas en archivos de test | ⚠️ PARCIALMENTE FIXED |
| H1-04 | LAB_VALIDATION_PIN default "1234"            | ✅ FIXED           |
| H4-02 | Redis default password en docker-compose.yml | ✅ FIXED           |
| H4-03 | AI_PROVIDER default `deepseek`               | ✅ FIXED           |

**`python manage.py check`:** 0 issues (0 silenced)  
**Tests de aislamiento multitenant:** 22/22 OK

---

## Detalle por Hallazgo

---

### H1-06 — Cross-tenant data leak público (LIMS)
**Clasificación: FALSE POSITIVE — NO ERA FUGA REAL**

**Evidencia:**

- `lims/views/tenant_lims.py` (`empresa_lims`):
  ```python
  def empresa_lims(request):
      return getattr(getattr(request, 'user', None), 'empresa', None)
  ```
  Solo acepta la FK explícita del usuario; no usa fallback de middleware.

- `core/views/laboratorio/config_lims.py:145`:
  ```python
  analito = get_object_or_404(Analito, pk=parametro_id, empresa=empresa)
  ```
  Filtra explícitamente por `empresa` del usuario. Un analito de otro tenant devuelve 404.

- Tests verificados: `core.tests.test_lims_config_tenant_security` — 5/5 OK.
  - `test_rangos_parametro_no_expone_analito_de_otro_tenant` PASS.

**Contexto:** Documentado en `docs/ai_coordination/inbox/20260624_lims_tenant_404_masking.md`. La contradicción canónica fue resuelta: `Usuario.save()` ya no asigna empresa por defecto, el middleware LIMS usa solo FK explícita.

**Acción requerida:** Ninguna.

---

### H2-01 — Sentinel usa `admin_token = SECRET_KEY[:16]`
**Clasificación: FIXED**

**Evidencia:**

`core/views/sentinel_api.py:27–43`:
```python
def _sentinel_remote_token_valid(admin_token):
    ops = (
        (os.environ.get('PRISLAB_SENTINEL_RESET_TOKEN') or '').strip()
        or (os.environ.get('PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN') or '').strip()
    )
    if not ops:
        return False
    return admin_token == ops
```

No hay referencia a `SECRET_KEY` como fallback en ningún endpoint Sentinel. Los tres endpoints (`api_shield_telemetry`, `api_sentinel_reset`, `api_sentinel_diagnostico`) verifican tokens de variables de entorno dedicadas o sesión de superusuario.

**Acción requerida:** Ninguna.

---

### H2-03 — `resetear_password` eleva `is_staff`/`is_superuser`
**Clasificación: FIXED**

**Evidencia:**

`reset_password.py:16–32` (script de utilidad, no ruta HTTP):
```python
def resetear_password(username, password):
    usuario = Usuario.objects.get(username=username)
    usuario.set_password(password)
    usuario.is_active = True
    usuario.save()
```
Solo modifica `password` e `is_active`. No eleva privilegios.

No existe URL registrada para `resetear_password` en `config/urls.py` ni en `config/urls/`. 

La única ruta que puede modificar `is_staff` es `api_actualizar_usuario` (`administracion_usuarios.py:125`), que está correctamente protegida con `if not (request.user.is_superuser or request.user.is_staff)`.

**Acción requerida:** Ninguna.

---

### H3-01 — Rutas de impresión de resultados con reglas distintas
**Clasificación: FIXED**

**Evidencia:**

Ambas rutas aplican exactamente las mismas tres comprobaciones ("Triple Llave de Envío"):

| Check | `imprimir_resultados` (reportes.py) | `imprimir_resultados_pdf` (pdf_impresion.py) |
|-------|--------------------------------------|-----------------------------------------------|
| Estado validado | `estado in ('RESULTADOS_LISTOS', 'ENTREGADO')` ✅ | `estado in ('RESULTADOS_LISTOS', 'ENTREGADO')` ✅ |
| Saldo = $0 | `tiene_saldo_pendiente(orden)` → retorna `respuesta_retenida_html` ✅ | `saldo_pendiente <= Decimal('0.00')` → `respuesta_retenida_html` ✅ |
| Firma de privacidad | `paciente_autorizado_canal_digital_resultados` ✅ | `paciente_autorizado_canal_digital_resultados` ✅ |

Además, ambas rutas registran acceso forense con `registrar_acceso_forense`.

**Acción requerida:** Ninguna.

---

### H5-01 — `provision_usuarios_base` con contraseñas por defecto
**Clasificación: FIXED**

**Evidencia:**

`core/management/commands/provision_usuarios_base.py:29–34`:
```python
password = environ.get('PRISLAB_INIT_PASSWORD') or environ.get('PRISLAB_INIT_ADMIN_PASSWORD')
if not password:
    raise RuntimeError(
        "Debe configurar PRISLAB_INIT_PASSWORD o PRISLAB_INIT_ADMIN_PASSWORD "
        "antes de provisionar el usuario admin."
    )
```

Líneas 70–75 (usuario Brizia):
```python
password = environ.get('PRISLAB_INIT_PASSWORD_BRIZIA') or environ.get('PRISLAB_INIT_PASSWORD')
if not password:
    raise RuntimeError(...)
```

No existen contraseñas hardcodeadas. El comando falla de forma explícita si las variables de entorno no están configuradas.

**Acción requerida:** Ninguna.

---

### H1-03 — Contraseñas hardcodeadas en archivos de test
**Clasificación: ⚠️ PARCIALMENTE FIXED**

**Evidencia:**

Los archivos nombrados explícitamente en el hallazgo original (`test_final_verification.py`, `test_laboratorio_full_e2e.py`, `test_farmacia_pdv_e2e.py`) **no existen en el repositorio**. Fueron eliminados o integrados, cerrando la exposición específica.

**Situación actual:** Sin embargo, múltiples archivos de test existentes aún contienen contraseñas hardcodeadas para usuarios de prueba:

| Archivo | Contraseñas presentes |
|---------|----------------------|
| `core/tests/test_director.py` | `test123456789` |
| `core/tests/test_bienestar_mejorado.py` | `testpass123` |
| `core/tests/test_farmacia_carga_masiva_excel.py` | `test123456789` |
| `core/tests/test_auditoria_funcional_20260621.py` | `Test2026!PRIS` |
| `core/tests/test_tenant_isolation.py` | `Test2026!PRIS` |
| `core/tests/test_contabilidad_personal.py` | `secret123` |
| `core/tests/test_devoluciones_farmacia_api.py` | `admin_dev_123` |
| Otros 10+ archivos | Contraseñas genéricas |

**Evaluación de riesgo:** Las contraseñas son genéricas de prueba (no credenciales de producción). Los tests de Django usan bases de datos aisladas en memoria (`file:memorydb_default?mode=memory&cache=shared`). El riesgo de explotación es **BAJO** en un entorno de CI/CD correctamente aislado.

**Ningún archivo de test usa actualmente `PRISLAB_TEST_PASSWORD` como variable de entorno.**

**Recomendación:** Migrar gradualmente a `os.environ.get('PRISLAB_TEST_PASSWORD', 'test-only-fallback')` en los archivos de test más expuestos. Prioridad baja dado el aislamiento de la base de datos de prueba.

**Acción requerida:** No se realizaron cambios en esta revisión dado el bajo riesgo. Se recomienda tarea de seguimiento para estandarizar todos los archivos de test.

---

### H1-04 — `LAB_VALIDATION_PIN` con default `"1234"`
**Clasificación: FIXED**

**Evidencia:**

`config/settings.py:742`:
```python
LAB_VALIDATION_PIN = os.environ.get("LAB_VALIDATION_PIN", "").strip()
```
Default vacío (no `"1234"`). En producción:

```python
if IS_PRODUCTION and not LAB_VALIDATION_PIN:
    raise RuntimeError('🔴 PRISLAB SEGURIDAD: LAB_VALIDATION_PIN no está configurado...')
if IS_PRODUCTION and len(LAB_VALIDATION_PIN) < 8:
    raise RuntimeError('🔴 PRISLAB SEGURIDAD: en producción LAB_VALIDATION_PIN debe tener al menos 8 caracteres...')
```

`docker-compose.yml:131`:
```yaml
LAB_VALIDATION_PIN: ${LAB_VALIDATION_PIN:?Debes definir LAB_VALIDATION_PIN en .env}
```
Usa `:?` (falla si no definida). PIN mínimo de 8 caracteres en producción.

**Acción requerida:** Ninguna.

---

### H4-02 — Redis con default password `prislab_redis_2026`
**Clasificación: FIXED**

**Evidencia:**

`docker-compose.yml:61`:
```yaml
--requirepass ${REDIS_PASSWORD:?Debes definir REDIS_PASSWORD en .env}
```

`docker-compose.yml:107,109`:
```yaml
REDIS_URL: redis://:${REDIS_PASSWORD:?Debes definir REDIS_PASSWORD en .env}@redis:6379/0
CACHE_LOCATION: redis://:${REDIS_PASSWORD:?Debes definir REDIS_PASSWORD en .env}@redis:6379/1
```

Todos los usos de `REDIS_PASSWORD` usan `:?` (error fatal si no definida). No existe fallback `:-prislab_redis_2026`.

**Acción requerida:** Ninguna.

---

### H4-03 — `AI_PROVIDER` default `deepseek`
**Clasificación: FIXED**

**Evidencia:**

`docker-compose.yml:112`:
```yaml
AI_PROVIDER: ${AI_PROVIDER:-gemini}
```
Default actualizado a `gemini`. En `config/settings.py:15`:
```python
AI_PROVIDER = os.environ.get("AI_PROVIDER", "").strip().lower()
```
Default vacío en settings (proveedor queda sin configurar si no se define, previene uso silencioso de deepseek).

**Acción requerida:** Ninguna.

---

## Resultado de Verificación Técnica

```
$ python manage.py check
System check identified no issues (0 silenced)

$ python manage.py test core.tests.test_lims_config_tenant_security core.tests.test_tenant_isolation
Ran 22 tests in 9.849s
OK
```

---

## Hallazgos Abiertos

| ID    | Estado  | Acción pendiente |
|-------|---------|------------------|
| H1-03 | ⚠️ Parcial | Migrar test files restantes a `PRISLAB_TEST_PASSWORD`. Riesgo BAJO. Tarea de seguimiento recomendada. |

---

## Hallazgos Cerrados en Esta Revisión

Ninguno requirió cambio de código — todos los hallazgos estaban ya corregidos en el código base actual.

---

*Generado automáticamente por Copilot Coding Agent — 2026-07-11*
