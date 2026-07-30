# Auditoría exhaustiva PRISLAB — Hallazgos

## H-NUEVO-05 — CRÍTICO: `ExpedienteNotaSHA.save()` crashea SIEMPRE — blockchain de notas clínicas nunca funcionó
- **Archivo:** `core/models/expediente_blindaje.py:147-168` (`calcular_hash`) y `:203-220` (`save`).
- **Causa raíz:** `calcular_hash()` usa `self.timestamp_creacion.isoformat()`, pero `timestamp_creacion` es `DateTimeField(auto_now_add=True)`. Django solo asigna ese valor dentro de `pre_save()`, que se ejecuta DENTRO de `super().save()` — es decir, DESPUÉS de que el `save()` sobrescrito ya llamó a `calcular_hash()`. Para una instancia nueva, `self.timestamp_creacion` vale `None` en ese punto.
- **Verificación empírica (no solo lectura de código):** ejecuté directamente contra la base de datos de desarrollo (dentro de una transacción con rollback forzado, sin dejar huella):
  ```
  RESULTADO: AttributeError AttributeError("'NoneType' object has no attribute 'isoformat'")
  ```
  Reproducido de forma 100% consistente creando `Empresa`, `Usuario`, `Paciente`, `NotaClinicaSOAP` y luego `ExpedienteNotaSHA(...).save()` sin pasar `timestamp_creacion` — exactamente como lo hacen TODOS los call sites reales del proyecto (confirmé por grep que `timestamp_creacion=` nunca se pasa explícitamente en ningún `.create()`/`.save()` de este modelo en toda la base de código).
- **Impacto por punto de uso:**
  - `core/middleware/blindaje_expediente.py::crear_snapshot_automatico` (señal `post_save` de **TODA** `NotaClinicaSOAP`, línea 178-244): el `except Exception` de la línea 243 traga el error silenciosamente y solo hace `logger.error(...)`. **Cada nota SOAP guardada en la historia del sistema intenta crear un snapshot blockchain y falla en silencio** — la tabla `ExpedienteNotaSHA` probablemente nunca ha recibido un registro válido en producción vía este flujo.
  - `core/views/blindaje_expediente.py::sellar_con_pin` (línea 188-220, dentro de `transaction.atomic()`): el `except Exception` de la línea 313 atrapa el error y responde `{'success': False, ...}` al usuario. **La función de "Sellado con PIN" (cierre legal e inmutable de una nota clínica, el corazón de la Capa 2 de Blindaje) falla el 100% de las veces.**
  - `enfermeria/views.py:144-154` (`crear_expediente_sha` llamado directo, sin pasar por el signal): el `except (DatabaseError, ValidationError)` de la línea 151 **NO captura `AttributeError`** — este call site debería propagar un error 500 no controlado al usuario (enfermería) al registrar signos vitales vinculados a una nota SOAP existente.
  - `core/views/blindaje_expediente.py:386-394` (registro de auditoría de desbloqueo forense): mismo patrón, envuelto en el `except Exception` de línea 417 — el desbloqueo forense también fallaría en registrar su snapshot de auditoría.
- **Alcance del impacto:** esto invalida la premisa central del módulo, declarada en su propio docstring: *"Expediente Médico Legalmente Inexpugnable"*, *"Encadenamiento SHA256 tipo blockchain"*, *"Verificación criptográfica de integridad"*. Si el hallazgo se confirma también en producción (no solo en este entorno de desarrollo), significa que **no existe ninguna cadena de hashes real respaldando el cumplimiento NOM-004/NOM-024** que el sistema dice garantizar, y que el cierre/sellado legal de notas clínicas con PIN nunca ha sido posible.
- **Recomendación:** en `ExpedienteNotaSHA.save()`, asignar explícitamente `self.timestamp_creacion = self.timestamp_creacion or timezone.now()` ANTES de calcular el hash (y dejar que `auto_now_add` sea un no-op porque el campo ya trae valor), o mover el cálculo de hash a un método `pre_save`/signal separado que corra después de que Django puebla el campo.
- **Severidad:** CRÍTICA — funcionalidad de cumplimiento legal/forense central completamente inoperante, con fallos silenciados en la mayoría de los call sites.
- **Estado:** pendiente de decisión del usuario (no se corrige sin autorización explícita). Requiere verificar además si existen registros reales en la tabla `core_expedientenotasha` en la base de datos de producción para dimensionar el impacto histórico.


## H-NUEVO-01 — PINs financieros en texto plano (severidad media) — CORREGIDO
- **Archivo:** `core/models/base.py:283-298` (`ConfiguracionModulos.pin_precio_neto`, `pin_cancelacion_venta`)
- **Uso:** `farmacia/views/inventario.py:806` (`validar_pin_precio_neto`), `farmacia/views/devoluciones.py:141`
- **Problema:** El PIN se guarda como `CharField` sin hash y se compara con `==`/`strip()` directo contra el valor guardado. No usa `django.contrib.auth.hashers` ni comparación de tiempo constante (`secrets.compare_digest`).
- **Precedente:** migración `core/migrations/0078_remove_default_pin_and_disable_emergency_bypass.py` ya tuvo que purgar un PIN default inseguro `'1234'` — el equipo ya sabía que esto era sensible.
- **Impacto:** filtración de BD (backup, dump, acceso DBA malicioso) expone directamente el PIN de autorización de descuentos/cancelaciones, sin necesidad de crackear nada.
- **Recomendación:** hashear con `django.contrib.auth.hashers.make_password`/`check_password`, o cifrar con Fernet igual que `Empresa.byok_gemini_api_key_enc`. Comparación con `secrets.compare_digest`.
- **Estado:** corregido en `core.0098_hash_farmacia_pins` y en el modelo/verificadores centrales. Los PIN existentes se migran a hash Django PBKDF2; precio neto, devolución y servicio de cancelación usan `check_password`.
- **Nota de consistencia:** el patrón correcto SÍ existe en el código: `core/models/catalogos.py::Medico.lab_validation_pin_hash` guarda el PIN-LAB como hash SHA256 con comentario explícito "NUNCA almacenar el PIN en texto plano". Confirma que `ConfiguracionModulos.pin_precio_neto`/`pin_cancelacion_venta` es una inconsistencia, no una limitación técnica del proyecto.

## H-NUEVO-03 — Generación de folios por count()+1 sin bloqueo (condición de carrera)
- **Archivos:** `core/models/clinico.py`: `HistoriaClinica.save()` (142-151), `ConsultaMedica.save()` (312-327), `CertificadoMedico.save()` (374-387), `EstudioImagen.save()` (626-638).
- **Problema:** todos generan folio/expediente con `Model.objects.filter(...).count()` seguido de `+1` y `zfill`, sin `select_for_update()` ni secuencia atómica de BD. Dos requests concurrentes (ej. dos consultas finalizándose al mismo tiempo) pueden leer el mismo `count()` antes de que cualquiera confirme.
- **Impacto:** con `unique=True`/`UniqueConstraint` en el folio, la segunda escritura falla con `IntegrityError` (error 500 visible al usuario) en vez de reintentar o usar un contador atómico. No genera duplicados silenciosos, pero sí interrumpe el flujo clínico bajo concurrencia real (dos consultorios, alta demanda).
- **Contraste:** `core/services/ventas/cobro_service.py` sí usa `select_for_update()` correctamente para esta misma clase de problema (folios/stock).
- **Recomendación:** usar secuencia de BD, `select_for_update()` sobre un contador dedicado, o reintento con backoff ante `IntegrityError`.
- **Estado:** pendiente de decisión del usuario.

## H-NUEVO-04 — Hash de integridad computado antes de que `auto_now_add` fije el timestamp
- **Archivo:** `core/models/clinico.py:730-735` (`HistorialCambiosConsulta.save`)
- **Problema:** `self.hash_integridad` se calcula incluyendo `self.timestamp` ANTES de llamar a `super().save()`. Para un registro nuevo, `timestamp` (campo `auto_now_add=True`) todavía no ha sido poblado por Django en ese punto — su valor es `None`. El hash queda atado a un valor constante `None` en vez del timestamp real de creación.
- **Impacto:** debilita el propósito declarado del hash ("Hash SHA256" de integridad forense) — no vincula criptográficamente el registro a su momento exacto de creación, aunque conserva algo de unicidad por `consulta.id + campo + valores`.
- **Recomendación:** calcular el hash después de `super().save()` (con timestamp ya asignado) y persistirlo en un segundo `save(update_fields=['hash_integridad'])`, o usar `timezone.now()` explícito antes de guardar en vez de depender de `auto_now_add`.
- **Estado:** pendiente de decisión del usuario.

## H-NUEVO-02 — EncryptedTextField degrada a texto plano silenciosamente (severidad media-alta) — CORREGIDO
- **Archivo:** `core/fields.py:64-79` (`EncryptedTextField.encrypt`)
- **Problema:** Si `cryptography` no está instalado, o `Fernet(...)`/`fernet.encrypt()` lanza cualquier excepción, la función atrapa el error y hace `return text` (el texto SIN cifrar), en vez de abortar el guardado. Solo emite `logger.critical(...)` si `not DEBUG`; no levanta excepción, no bloquea `save()`.
- **Impacto:** Campos declarados explícitamente como "NUNCA legibles sin la clave" (`core/models/bienestar_staff.py`: `DiarioEmocionalStaff.contenido`, `SesionCoachingStaff.notas_privadas`, `EvaluacionNOM035.respuestas_json`) podrían terminar en texto plano en la base de datos de producción si el cifrado falla por cualquier causa (paquete no instalado, `FERNET_KEY` corrupta, etc.), sin que la operación falle visiblemente para quien la ejecuta.
- **Relacionado:** `decrypt()` (línea 81-92) también atrapa `(InvalidToken, Exception)` de forma amplia y devuelve el valor crudo sin distinguir "dato legacy sin cifrar" de "fallo real de descifrado" — dificulta detectar si el cifrado está realmente funcionando.
- **Recomendación:** en producción, fallar cerrado (`raise`) si el cifrado no puede aplicarse, igual que ya se hace con `FERNET_KEY` ausente en `config/settings/security.py`.
- **Estado:** corregido. `EncryptedTextField.encrypt()` lanza `ImproperlyConfigured` ante ausencia, clave inválida o fallo de Fernet; nunca devuelve texto plano en un guardado nuevo.

## Código muerto / higiene (sin riesgo de seguridad) — CORREGIDO
- `core/services/ai_medico_backup.py` — eliminado tras confirmar que no tenía imports activos.
- `marketing/views_legacy.py` — eliminado tras confirmar que `marketing/urls.py` usa `marketing.views`.

## Confirmaciones positivas (verificado con evidencia, sin hallazgo)
- `core/decorators.py::role_required`, `core/api_contracts/ninja_api.py::_requiere_lims_captura` — sin bypass `is_staff`.
- `core/models/append_only.py`, `ForenseAcceso`, `AuditLog` — append-only real a nivel modelo y queryset.
- `core/tenant.py` — aislamiento multi-tenant + sucursal correcto, `STRICT_MODE` activo en producción.
- `core/services/ventas/cobro_service.py::ejecutar_venta_pdv` — `transaction.atomic()` + `select_for_update()` en Producto y Lote, PEPS respeta caducidad.
- `contabilidad/validators_cfdi40.py` — validación RFC/CP conforme a especificación SAT 4.0.
- `core/services/clinical_math.py` — motor de fórmulas sin `eval()`, AST restringido.
- `core/models/base.py::Usuario_Sucursal.esta_vigente()`, puente de compatibilidad `.sucursal`/`.sucursal_id` — correctos.
