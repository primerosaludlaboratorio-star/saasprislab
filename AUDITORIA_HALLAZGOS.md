# Auditoría exhaustiva PRISLAB — Hallazgos

## Limpieza aplicada — 2026-07-30
- Retirados símbolos sin consumidores: `Paciente.generar_pris_id()`, `TokenLIMSV7Manager`, `conectar_seniales()` y el registro legacy `PrisAgent`/`TOOL_REGISTRY`/`register_tool`/`can_execute_tool`.
- Retiradas las copias huérfanas `core/models/motor_financiero.py` y `core/models/reportes_financieros.py`. Las implementaciones activas permanecen en `core/views/` y sus URLs/pruebas fueron verificadas por referencia.
- No se eliminaron `core/services/auto_repair.py`, `core/rbac/permissions.py`, scripts legacy ni documentación histórica porque tienen consumidores, pruebas o función de archivo explícita.

## Farmacia — baja de caducados — 2026-07-30
- **Incidente reportado por personal:** los botones de baja desde el panel de caducidad eran marcadores visuales (`alert('Función ... por implementar')`) y no iniciaban ningún flujo.
- **Corrección:** los botones ahora enlazan con `farmacia:crear_movimiento`, preseleccionan lote y movimiento `SALIDA_MERMA`; el servidor valida empresa, producto y lote exactos.
- **Corrección adicional:** `ValidationError` operativo devuelve HTTP 400 con mensaje accionable; ya no se convierte en HTTP 500 ni dispara la pantalla de reparación de Sentinel.
- **Pruebas añadidas:** `core/tests/test_farmacia_baja_caducidad.py` cubre acceso desde alertas, baja total del lote y rechazo de baja sin lote.
- **Estado:** corregido localmente; pendiente de despliegue y validación humana en producción en este turno.

## Farmacia — historial de devoluciones — 2026-07-30
- **Incidente reportado por personal:** la devolución se confirmaba como exitosa, pero el historial podía aparecer vacío.
- **Causa:** la vista consultaba únicamente `core.SalesReturn`, mientras el flujo ERP registra `farmacia.DevolucionVenta`.
- **Corrección:** historial unificado de ambos registros, ordenado por fecha y filtrado por empresa; muestra folio de devolución, folio de venta, cliente, monto, tipo, motivo, acción de stock, usuario y estado.
- **Estado:** corregido localmente; pendiente de despliegue y validación humana en producción en este turno.

## H-NUEVO-05 — CRÍTICO: `ExpedienteNotaSHA.save()` crashea SIEMPRE — CORREGIDO Y VERIFICADO EN PRODUCCIÓN
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
- **Corrección aplicada:** `timestamp_creacion` usa `default=timezone.now` en vez de `auto_now_add`, se normaliza `user_agent=None` a cadena vacía, se carga `hash_anterior` antes de calcular el bloque y la comparación del PIN médico usa `secrets.compare_digest`. Migración `core.0099_alter_expedientenotasha_timestamp_creacion`.
- **Verificación local:** transacción con rollback creó dos snapshots, verificó ambos hashes y confirmó la cadena `v2 -> v1` (`BLINDAJE_ROLLBACK_OK 1 2`). También existe prueba focalizada en `core/tests/test_sensitive_authorizations.py`.
- **Severidad:** CRÍTICA — funcionalidad de cumplimiento legal/forense central completamente inoperante, con fallos silenciados en la mayoría de los call sites.
- **Estado:** corregido y desplegado. Producción aplicó `core.0099`; la transacción reversible confirmó `PROD_BLINDAJE_ROLLBACK_OK 1 2`. La tabla productiva estaba sin snapshots al momento de la verificación (`SHA_COUNT 0`), por lo que no había histórico que reparar.
- **Call site adicional confirmado:** `core/models/expediente_blindaje.py::NotaClinicaSellar.sellar_con_pin()` (línea 506-554) también llama `SnapshotNotaMiddleware.crear_expediente_sha()` dentro de `transaction.atomic()`, sin try/except propio — mismo crash, revierte la transacción de sellado.
- **Limpieza aplicada:** se retiró `conectar_seniales()` y su guard de importación. El flujo vigente de snapshots permanece en `core/middleware/blindaje_expediente.py::crear_snapshot_automatico`, que es el único receptor activo y maneja sus errores explícitamente.
- **Limpieza aplicada:** se retiró `TokenLIMSV7Manager` y sus métodos sin consumidores (`resolver_a_orden()`/`_resolver_token()`/`_crear_detalle_orden()`). Era una implementación incompleta y desconectada del flujo LIMS vigente; la integración activa permanece en `core/utils/lims_tokens_v75.py` y en los servicios LIMS.
- **Hallazgo menor adicional:** `NotaClinicaSellar._validar_pin_medico()` (línea 556-573) compara hashes con `==` directo en vez de `secrets.compare_digest`. Riesgo bajo (es un hash SHA256, no el PIN crudo; resistencia a preimagen protege), pero rompe el estándar de comparación de secretos usado correctamente en otras partes (`require_api_token`).


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
- **Archivos:** `core/models/clinico.py`: `HistoriaClinica.save()` (142-151), `ConsultaMedica.save()` (312-327), `CertificadoMedico.save()` (374-387), `EstudioImagen.save()` (626-638). También `core/models/laboratorio.py::OrdenDeServicio.save()` (597-602, `folio_orden`, `unique=True`), `core/models/expediente_blindaje.py::NotaClinicaSellar.generar_folio()` (473-485, `folio_unico`), `core/models/ventas.py::Receta.save()` (122-130, `folio_receta`) y `core/models/ventas.py::Venta.save()` (348-357, `folio_operacion`).
- **Problema:** todos generan folio/expediente con `Model.objects.filter(...).count()` seguido de `+1` y `zfill`, sin `select_for_update()` ni secuencia atómica de BD. Dos requests concurrentes (ej. dos consultas finalizándose al mismo tiempo) pueden leer el mismo `count()` antes de que cualquiera confirme.
- **Impacto:** con `unique=True`/`UniqueConstraint` en el folio, la segunda escritura falla con `IntegrityError` (error 500 visible al usuario) en vez de reintentar o usar un contador atómico. No genera duplicados silenciosos, pero sí interrumpe el flujo clínico bajo concurrencia real (dos consultorios, alta demanda).
- **Contraste:** `core/services/ventas/cobro_service.py` sí usa `select_for_update()` correctamente para esta misma clase de problema (folios/stock).
- **Recomendación:** usar secuencia de BD, `select_for_update()` sobre un contador dedicado, o reintento con backoff ante `IntegrityError`.
- **Estado:** pendiente de decisión del usuario.

## H-NUEVO-04 — Hash de integridad computado antes de que `auto_now_add` fije el timestamp — CORREGIDO Y VERIFICADO EN PRODUCCIÓN
- **Archivo:** `core/models/clinico.py:730-735` (`HistorialCambiosConsulta.save`)
- **Problema:** `self.hash_integridad` se calcula incluyendo `self.timestamp` ANTES de llamar a `super().save()`. Para un registro nuevo, `timestamp` (campo `auto_now_add=True`) todavía no ha sido poblado por Django en ese punto — su valor es `None`. El hash queda atado a un valor constante `None` en vez del timestamp real de creación.
- **Impacto:** debilita el propósito declarado del hash ("Hash SHA256" de integridad forense) — no vincula criptográficamente el registro a su momento exacto de creación, aunque conserva algo de unicidad por `consulta.id + campo + valores`.
- **Corrección aplicada:** `timestamp` usa `default=timezone.now` para conservar el instante incluido en el hash; migración `core.0101`. Prueba añadida en `core/tests/test_clinical_integrity.py` y verificación transaccional local confirmada.
- **Estado:** corregido, migrado y verificado en producción con `PROD_CLINICAL_HASH_ROLLBACK_OK 1`.

## H-NUEVO-02 — EncryptedTextField degrada a texto plano silenciosamente (severidad media-alta) — CORREGIDO
- **Archivo:** `core/fields.py:64-79` (`EncryptedTextField.encrypt`)
- **Problema:** Si `cryptography` no está instalado, o `Fernet(...)`/`fernet.encrypt()` lanza cualquier excepción, la función atrapa el error y hace `return text` (el texto SIN cifrar), en vez de abortar el guardado. Solo emite `logger.critical(...)` si `not DEBUG`; no levanta excepción, no bloquea `save()`.
- **Impacto:** Campos declarados explícitamente como "NUNCA legibles sin la clave" (`core/models/bienestar_staff.py`: `DiarioEmocionalStaff.contenido`, `SesionCoachingStaff.notas_privadas`, `EvaluacionNOM035.respuestas_json`) podrían terminar en texto plano en la base de datos de producción si el cifrado falla por cualquier causa (paquete no instalado, `FERNET_KEY` corrupta, etc.), sin que la operación falle visiblemente para quien la ejecuta.
- **Relacionado:** `decrypt()` (línea 81-92) también atrapa `(InvalidToken, Exception)` de forma amplia y devuelve el valor crudo sin distinguir "dato legacy sin cifrar" de "fallo real de descifrado" — dificulta detectar si el cifrado está realmente funcionando.
- **Recomendación:** en producción, fallar cerrado (`raise`) si el cifrado no puede aplicarse, igual que ya se hace con `FERNET_KEY` ausente en `config/settings/security.py`.
- **Estado:** corregido. `EncryptedTextField.encrypt()` lanza `ImproperlyConfigured` ante ausencia, clave inválida o fallo de Fernet; nunca devuelve texto plano en un guardado nuevo.

## H-NUEVO-06 — `datetime.strptime` sin try/except en reportes financieros (baja severidad) — CORREGIDO Y DESPLEGADO
- **Archivo activo:** `core/views/reportes_financieros.py` — cinco rutas usan ahora `_fecha_segura`, que aplica un valor por defecto ante entrada inválida.
- **Problema:** parsean `fecha_inicio`/`fecha_fin`/`fecha_corte` desde `request.GET` con `datetime.strptime(valor, '%Y-%m-%d')` sin capturar `ValueError`. Un parámetro malformado provoca `500 Internal Server Error` no controlado.
- **Contraste:** `core/models/motor_financiero.py::genera_reporte_caja` sí captura `ValueError` con fallback a rango por defecto — mismo archivo/dominio, patrón inconsistente.
- **Severidad:** baja — requiere sesión autenticada con rol `DIRECTOR`/`ADMIN`/`GERENTE`/`FINANZAS`; no es bypass de autenticación ni fuga de datos, solo UX pobre y ruta de excepción no controlada.
- **Nota adicional:** este archivo, igual que `motor_financiero.py`, vive en `core/models/` pero no contiene ninguna clase de modelo — son 8 vistas/helpers. Confirma que el patrón de mala ubicación de código no es aislado.
- **Estado:** corregido, probado y desplegado en `core/views/reportes_financieros.py`. `core/models/reportes_financieros.py` es una copia no enlazada por las URLs; no se modificó para evitar mantener una segunda fuente ejecutable.

## H-NUEVO-07 — `IncidenciaAsistencia.documento_soporte` sin validador de archivo (baja-media severidad) — CORREGIDO LOCALMENTE
- **Archivo:** `core/models/rrhh.py:518` (`FileField(upload_to='incidencias/', ...)`, sin `validators=`).
- **Problema:** a diferencia de `Bitacora39A.pdf_firmado` (mismo archivo, línea 92-99) que sí usa `validators=[validate_document_upload]`, este campo acepta cualquier tipo/tamaño de archivo sin restricción — cualquier empleado que suba un "documento de soporte" para una incidencia (falta, permiso, incapacidad) puede subir un ejecutable, script, o archivo arbitrariamente grande.
- **Impacto:** subida de archivos sin restricción de tipo/tamaño; superficie de ataque para malware almacenado o agotamiento de disco, aunque requiere sesión autenticada de empleado.
- **Recomendación:** aplicar `validators=[validate_document_upload]` igual que en el resto del sistema.
- **Estado:** corregido y desplegado con `validators=[validate_document_upload]` y migración `core.0100`.

## H-NUEVO-08 — CLABE interbancaria hardcodeada como default en modelo `Pago` (higiene/riesgo bajo) — CORREGIDO LOCALMENTE
- **Archivo:** `core/models/ventas.py:503` — `Pago.clabe_interbancaria = models.CharField(..., default="0123 4567 8901 2345", ...)`.
- **Problema:** el campo tiene un valor `default` que parece una CLABE de prueba/placeholder (secuencia obviamente ficticia). Si algún flujo de pago SPEI no captura la CLABE real y confía en el default del modelo, quedaría un número de cuenta falso en el registro de pago, lo cual podría confundir conciliación bancaria o auditoría contable si nadie lo nota.
- **Impacto:** bajo directamente (no es una credencial real ni secreto), pero es un dato financiero placeholder incrustado en el esquema que no debería tener un valor por defecto "parecido a real" — mejor `default=''` o `blank=True` sin valor semántico.
- **Recomendación:** cambiar el default a cadena vacía; forzar captura explícita de CLABE en el formulario de pago SPEI.
- **Estado:** corregido y desplegado: el default ahora es cadena vacía y la captura queda explícita para SPEI; migración `core.0100`.

## H-NUEVO-09 — `require_sucursal_access` omite la validación silenciosamente ante `sucursal_id` no numérico — CORREGIDO LOCALMENTE
- **Archivo:** `core/rbac/permissions.py:406-417` (`require_sucursal_access`, líneas 409-414).
- **Problema:** `suc_id = kwargs.get(sucursal_kwarg) or kwargs.get('sucursal_id')`; si `int(suc_id)` lanza `ValueError`/`TypeError`, el decorador hace `pass` y **deja pasar la request a la vista sin validar sucursal**, confiando en que "la vista manejará el error". Si la vista no revalida agresivamente el mismo valor, el aislamiento por sucursal (`SUCURSAL_SCOPED_RESOURCES`: caja, inventario, resultados, órdenes, ventas) queda efectivamente deshabilitado para ese request.
- **Impacto:** potencial bypass de aislamiento de sucursal (fail-open en vez de fail-closed) si algún valor no entero llega al kwarg y la vista subyacente no repite la validación de sucursal de forma independiente. Requiere confirmar caso por caso en `core/views/` si alguna vista protegida por este decorador confía ciegamente en él sin revalidar.
- **Contraste:** `check_sucursal_assignment` (mismo archivo, línea 173-175) sí falla cerrado (`except Exception: return False`) — el decorador `require_sucursal_access` es la única ruta que falla abierto.
- **Recomendación:** ante fallo de conversión, denegar (`PermissionDenied`) en vez de `pass`.
- **Mitigante confirmado:** `require_sucursal_access` NO está aplicado a ninguna vista actualmente (`grep` en todo el repo solo lo encuentra en `core/rbac/permissions.py` y su re-export en `core/rbac/__init__.py`) — es código muerto/sin usar hoy, por lo que el riesgo real actual es nulo. Queda como defecto latente si se adopta en el futuro.
- **Estado:** corregido y desplegado: el decorador registra el intento y falla cerrado con `PermissionDenied`; prueba añadida en `core/rbac/tests.py`.

## H-NUEVO-10 — `core/rbac/permissions.py`: decoradores `require_permission`/`require_roles`/`deny_roles`/`require_sucursal_access` no se usan en ninguna vista real (higiene/riesgo de confusión)
- **Archivo:** `core/rbac/permissions.py` completo.
- **Hallazgo:** `grep` en todo el repo confirma que `require_permission`, `require_roles`, `deny_roles`, `require_sucursal_access`, `check_sucursal_access`, `user_permissions`, `user_sucursal_permissions` NO se importan ni se usan en ningún archivo de `core/views/` ni de ninguna app de negocio — solo aparecen en `core/rbac/permissions.py` mismo y en `core/rbac/tests.py`. Los únicos símbolos de este módulo que sí se usan en producción son `check_sucursal_assignment` y `_has_permission` (función "privada" con guion bajo), consumidos desde `core/middleware/empresa.py` y `core/utils/sucursal_helpers.py`.
- **Impacto:** el `PERMISSION_MAP` extenso (con reglas explícitas por rol para lab, consultorio, caja, farmacia, finanzas, admin, IA) documenta una política de permisos que NO está siendo aplicada por ningún decorador activo en las vistas reales. El control de acceso real en producción corre por `core/decorators.py::role_required` (verificado ya, correcto), que es un mecanismo paralelo e independiente. Riesgo: un desarrollador que lea `PERMISSION_MAP` puede asumir erróneamente que ya existe enforcement centralizado por permiso, cuando cada vista debe declarar su propio `@role_required(...)` manualmente.
- **Severidad:** informativa/higiene — no es una vulnerabilidad explotable directamente, pero es deuda de arquitectura que puede llevar a incoherencias de RBAC si `PERMISSION_MAP` diverge de los `@role_required` reales sin que nadie lo note (falsa sensación de cobertura).
- **Recomendación:** o bien adoptar `require_permission`/`require_roles` como mecanismo único en las vistas, o eliminar/marcar como "no implementado" el módulo para evitar doble fuente de verdad.
- **Estado:** pendiente de decisión del usuario.

## H-NUEVO-11 — RBAC del agente PRIS (function calling) tenía riesgo fail-open ante herramienta desconocida en `_TOOL_RBAC` — CORREGIDO
- **Archivo:** `core/views/pris_ia.py:292-318` (`_verificar_rbac`), consumido por `_ejecutar_herramienta` (línea 323-402).
- **Problema:** `grupos_req = _TOOL_RBAC.get(tool_name)`; si `tool_name` no es clave de `_TOOL_RBAC` (dict hardcodeado, línea 229-264), `grupos_req` es `None`, y la función retorna `(True, "")` — es decir, **"sin restricción" es el comportamiento por defecto ante una herramienta no registrada explícitamente**, no ante una herramienta marcada intencionalmente como pública. La única red de seguridad secundaria es el campo `"grupos"` en `core/agent/tools/registry.py::TOOLS_OPERATIVOS` (línea 385-397 de `pris_ia.py`), pero **hoy ese campo está vacío (`"grupos": []`) para las 16 herramientas operativas**, por lo que en la práctica toda la protección real recae exclusivamente en que `_TOOL_RBAC` tenga una entrada manual correcta para cada nombre de herramienta.
- **Corrección aplicada:** el despachador activo (`core/views/pris_ia/_rbac.py`) y el módulo monolítico legado (`core/views/pris_ia.py`) ahora rechazan cualquier herramienta ausente del catálogo explícito antes de consultar grupos. Las herramientas operativas siguen requiriendo autorización humana para escribir y la verificación central de PRIS se ejecuta siempre.
- **Verificación:** `core.tests.test_pris_rbac` cubre herramienta desconocida; se añadió la misma política al módulo legado para evitar divergencia si una importación histórica lo reactiva. No se elimina el archivo legado en esta pasada porque requiere una comprobación separada de todos los imports externos.
- **Estado:** corregido en código local; pendiente despliegue y verificación de la revisión actual.

## H-NUEVO-12 — CRÍTICO: Django Admin expone datos cross-tenant (financieros, clínicos/PHI, RH, auditoría) sin aislamiento por empresa — CORREGIDO Y VERIFICADO EN PRODUCCIÓN
- **Archivos:** `core/admin/identidad.py`, `catalogo.py`, `ventas.py`, `clinico.py`, `bienestar.py`, `rrhh.py` (paquete activo `core/admin/`, confirmado empíricamente con `importlib.util.find_spec('core.admin')` → resuelve a `core/admin/__init__.py`, NO a `core/admin.py`).
- **Problema:** de las ~45 clases `ModelAdmin` registradas en el paquete `core/admin/`, únicamente `CustomUsuarioAdmin` y `Usuario_SucursalAdmin` (`identidad.py`) sobreescriben `get_queryset()` para filtrar por `request.user.empresa_id`. **Todas las demás** — incluyendo `VentaAdmin`, `ProductoAdmin`, `LoteAdmin`, `PacienteAdmin`, `OrdenDeServicioAdmin`, `DetalleOrdenAdmin`, `PagoOrdenAdmin`, `GastoOperativoAdmin`, `HistoriaClinicaAdmin`, `ConsultaMedicaCoreAdmin`, `ConsentimientoInformadoAdmin`, `CertificadoMedicoAdmin`, `NotaClinicaSOAPAdmin`, `AuditLogAdmin`, `ForenseAccesoAdmin`, `EmpleadoAdmin`, `ReciboNominaAdmin`, etc. — usan el `get_queryset()` por defecto de Django, que **no filtra por tenant**.
- **Vector de explotación confirmado:**
  1. `core/views/onboarding.py:158-164` — al dar de alta una empresa nueva (self-service SaaS signup), el usuario DIRECTOR creado recibe `is_staff=True` (sin `is_superuser`). Esto es válido para **todo tenant que se registra**, no un caso aislado.
  2. `core/middleware/admin_access.py::AdminAccessMiddleware` — el bastión de `/admin/` (allowlist de IP y/o grupo `ADMIN_SISTEMA`) está **desactivado por defecto**: `ADMIN_IP_RESTRICTION_ENABLED` y `ADMIN_GROUP_RESTRICTION_ENABLED` ambos parten de `os.environ.get(..., 'False')` en `config/settings/base.py:340-342`. Sin configuración explícita de entorno, cualquier usuario con `is_staff=True` accede a `/admin/` sin restricción adicional de IP o grupo.
  3. Con ambos puntos combinados: **el DIRECTOR de cualquier tenant puede iniciar sesión en `/admin/` y listar/exportar registros de Venta, OrdenDeServicio, HistoriaClinica, ConsultaMedica, ConsentimientoInformado, CertificadoMedico, AuditLog, Empleado, ReciboNomina, etc. de TODOS LOS DEMÁS TENANTS del sistema**, no solo el propio.
- **Impacto:** fuga de datos cross-tenant de máxima sensibilidad en un SaaS de salud multi-tenant — incluye PHI (expedientes clínicos, consentimientos informados, certificados médicos), datos financieros (ventas, pagos, cuentas por cobrar) y de RRHH (nómina, evaluaciones de desempeño) de clientes que no son el operador. Viola el aislamiento de tenant que sí está correctamente implementado en las vistas de negocio (`core/tenant.py`, `TenantModel`, middleware `empresa.py`).
- **Contraste:** el aislamiento multi-tenant a nivel de vistas de negocio (`core/tenant.py`, `STRICT_MODE`) fue confirmado correcto en auditorías previas — este hallazgo es específico a la capa de Django Admin, que queda fuera de ese mecanismo porque usa managers/querysets sin pasar por el `TenantManager`.
- **CONFIRMACIÓN DEFINITIVA DE EXPLOTABILIDAD (no es solo teórico):** `core/management/commands/seed_grupos_permisos.py:132-139` asigna EXPLÍCITAMENTE `'all_perms': True` al grupo Django `'DIRECTOR'`, lo cual ejecuta `Permission.objects.all(); grupo.permissions.set(todos)` (línea 173-176) — es decir, **el grupo DIRECTOR recibe TODOS los permisos de TODOS los modelos del sistema, de todas las apps, por diseño explícito** ("Director General y socios — acceso global"). Esto se combina con: (a) `core/signals/auditoria.py:164-168` sincroniza automáticamente a todo usuario con `rol='DIRECTOR'` al grupo Django "DIRECTOR" vía `sincronizar_acceso_por_rol()` en cada `save()`; (b) el DIRECTOR de onboarding recibe `is_staff=True`. Es decir, el propio diseño del sistema de permisos ya asume (incorrectamente) que "Permission de Django = acceso dentro del propio tenant", cuando `Permission` de Django es un concepto **global, no tenant-aware** — el error conceptual de diseño es exactamente la causa raíz de este hallazgo, no un descuido aislado. Si `seed_grupos_permisos` fue ejecutado en producción (comando de seed estándar, se espera que sí), el hallazgo es 100% explotable sin ninguna configuración adicional de entorno.
- **Recomendación (prioridad máxima):**
  1. Agregar `get_queryset()` con filtro por `request.user.empresa_id` a TODAS las `ModelAdmin` de datos de negocio en `core/admin/`, replicando el patrón ya usado en `identidad.py`. Esto es indispensable independientemente de los permisos Django, porque `all_perms=True` en el grupo DIRECTOR es today una decisión de diseño vigente.
  2. Habilitar `ADMIN_GROUP_RESTRICTION_ENABLED=True` en producción como mínimo indispensable mientras se corrige el punto 1 (nota: esto NO resuelve el problema para Directores legítimos, que sí necesitan pasar ese filtro).
  3. Reconsiderar si el DIRECTOR de un tenant realmente necesita `is_staff=True` + permisos globales de Django (acceso a `/admin/`) en el flujo de onboarding, o si debería gestionarse todo desde las vistas de negocio con `role_required` (que sí es tenant-aware vía `core/tenant.py`).
- **Corrección aplicada:** todos los `ModelAdmin` registrados, incluidos los de apps de negocio, heredan `TenantScopedAdmin`/`TenantScopedAdminMixin`. La ruta hacia `empresa` se descubre por relaciones FK/OneToOne y falla cerrado si no puede demostrarse. `Group` también queda restringido a superusuario; `Usuario` conserva su filtro específico existente. Se eliminaron las rutas administrativas duplicadas del módulo raíz.
- **Verificación local:** registro completo de 184 administradores sin ningún `ModelAdmin` operativo fuera del mixin; `manage.py check` y compilación pasan. Catálogos globales sin FK de tenant devuelven queryset vacío para usuarios de empresa.
- **Estado:** corregido, desplegado y verificado en producción: 184 registros Admin, cero administradores sin mixin, cero fallos de consulta; cinco catálogos globales fallan cerrado.

## H-NUEVO-14 — `WalkieTalkieConsumer` (WebSocket) sin aislamiento por tenant en el nombre de sala
- **Archivos:** `core/consumers.py::WalkieTalkieConsumer.connect()` (líneas 169-200), `core/routing.py:11`.
- **Problema:** `room_name` se toma directamente de la URL (`ws/voice/walkie/<room_name>/`, regex `\w+`) sin ninguna validación de pertenencia a la empresa/tenant del usuario conectado. `self.room_group_name = f'walkie_{self.room_name}'` NO incluye `empresa_id`. `connect()` solo verifica `self.user.is_anonymous`, sin verificar tenant.
- **Impacto:** dado que los nombres de sala son genéricos por diseño ("farmacia", "consultorio", "general" — ver comentario en `routing.py`), un usuario autenticado de CUALQUIER tenant puede conectarse a `ws/voice/walkie/farmacia/` y recibir/transmitir audio en tiempo real junto con usuarios de OTRO tenant que usan el mismo nombre de sala genérico. Es una fuga de audio en vivo cross-tenant (potencialmente conversaciones con contenido clínico/financiero).
- **Contraste:** `VoiceCommandConsumer` sí es seguro — agrupa por `voice_commands_{self.user.id}` (canal privado por usuario, no por nombre arbitrario).
- **Corrección aplicada:** `WalkieTalkieConsumer` exige un `empresa_id` en el usuario autenticado, normaliza y valida la sala, y construye grupos con el tenant (`walkie_t<empresa_id>_<sala>`). Un usuario sin empresa o con sala inválida es rechazado antes de unirse al channel layer.
- **Verificación local:** `core.tests.test_walkie_tenant_isolation` (3 pruebas OK), `manage.py check` sin incidencias y `git diff --check` sin errores.
- **Estado:** corregido, desplegado y verificado en producción en la revisión `1f091db2f36f564a88373dcdae7d19910aaffdd3`; health HTTP 200 y servicios Gunicorn/Celery/Celery Beat activos.

## H-NUEVO-15 — Auto-restart de Gunicorn (Sentinel) disparable sin autenticación (DoS de disponibilidad)
- **Archivos:** `core/middleware/sentinel.py::SentinelTelemetryMiddleware.process_exception()` (línea 219-316, ver línea 259-269), `core/services/auto_repair.py::registrar_error_critico()`/`_ejecutar_soft_restart()` (línea 51-147).
- **Problema:** `process_exception()` se ejecuta para CUALQUIER excepción no controlada en las rutas de los namespaces monitoreados (prácticamente toda la app, incluyendo rutas públicas/no autenticadas — `_resolver_namespace` incluso captura `'/'`, `/login/`, `/dashboard/` como namespace `'core'`). Si el tipo de excepción es `TimeoutError`, `MemoryError`, `ConnectionResetError`, `BrokenPipeError`, `OSError` (o el mensaje contiene "timeout"/"memory"/"cannot allocate memory"), se llama a `registrar_error_critico()` SIN ninguna verificación de autenticación, rol, o IP. Si se acumulan 3 errores de ese tipo en una ventana de 60 segundos, `_ejecutar_soft_restart()` envía `SIGHUP` al proceso master de Gunicorn, forzando el reciclaje de todos los workers.
- **Impacto:** un atacante NO autenticado que logre provocar repetidamente excepciones de timeout/memoria en cualquier endpoint público (ej. subidas de archivo grandes, requests que fuerzan un timeout upstream, slow-loris parcial) puede forzar reinicios periódicos de los workers de Gunicorn cada ~120 segundos (cooldown), degradando la disponibilidad del servicio para TODOS los tenants sin necesidad de credenciales.
- **Mitigante parcial:** cooldown de 120s entre restarts (`_RESTART_COOLDOWN_SECONDS`) limita la frecuencia máxima de disrupción; SIGHUP es un reload "graceful" en Gunicorn (no debería tumbar requests activos), por lo que el impacto es degradación de rendimiento/latencia periódica, no caída total.
- **Corrección aplicada:** el camino HTTP de Sentinel ya no puede ejecutar `SIGHUP`. `registrar_error_critico()` conserva el contador y la alerta, pero exige `permitir_restart=True` para invocar el reinicio; esa autorización no se entrega desde `process_exception()` y queda reservada a una operación explícita de infraestructura.
- **Verificación local:** `core.tests.test_auto_repair_restart_guard` confirma que tres errores públicos no reinician Gunicorn y que el reinicio solo ocurre con autorización explícita.
- **Estado:** corregido, desplegado y verificado en producción en la revisión `c733c8d6d86addf375956e966afda69866aea4ce`; migraciones sin pendientes, servicios activos y health check exitoso.

## H-NUEVO-19 — Receptor HL7 permitía seleccionar el tenant con header controlable por el cliente
- **Archivo:** `core/services/lims/interfaces_lims_service.py::receptor_hl7()` y `_empresa_hl7_autoritativa()`.
- **Problema:** después de autenticar una API key global o una IP permitida, el receptor aceptaba `X-EMPRESA-ID` o `empresa_id` como fuente de tenant. Un emisor autenticado podía intentar seleccionar otra empresa y dirigir allí resultados clínicos.
- **Impacto:** riesgo de contaminación cross-tenant de resultados HL7/ASTM/JSON y trazabilidad clínica incorrecta.
- **Corrección aplicada:** el tenant solo se resuelve desde `HL7_IP_EMPRESA_MAP` o desde `HL7_API_KEY_EMPRESA_MAP`, ambos configurados en el servidor. Los headers y query params del emisor ya no son autoridad. Se añadieron pruebas de binding y rechazo.
- **Configuración requerida:** para claves sin IP fija, configurar `HL7_API_KEY_EMPRESA_MAP` como JSON privado `{"clave-del-equipo": <empresa_id>}`. No registrar este valor en Git.
- **Verificación local:** `core.tests.test_hl7_tenant_binding` y regresiones Walkie/Sentinel: 8 pruebas OK; `manage.py check` y compilación OK.
- **Estado:** corregido, desplegado y verificado en producción en la revisión `3807a0df9fe2bbe7324b9cfe79943b12126de620`; migraciones sin pendientes, servicios activos y health check exitoso.

## H-NUEVO-16 — Endpoints de auditoría de campo permiten forjar entradas arbitrarias en AuditLog (integridad forense comprometida)
- **Archivos:** `core/views/auditoria_api.py::api_auditar_campo` (línea 17-89), `core/views/auditoria_campo.py::api_auditoria_campo` (línea 18-92), `core/utils/auditoria_nativa.py::registrar_cambio_campo` (línea 14-74).
- **Problema:** ambos endpoints solo exigen `@login_required` (CUALQUIER usuario autenticado, sin importar rol) y aceptan del body JSON del cliente los campos `modelo`, `objeto_id`, `campo_nombre`, `valor_anterior` y `valor_nuevo` sin ninguna verificación server-side de que: (a) el modelo/objeto realmente existe, (b) el `objeto_id` pertenece al tenant del usuario (en `auditoria_api.py` no hay ninguna validación de existencia ni de tenant; en `auditoria_campo.py` solo se valida tenant si `campo_id` sigue el patrón `resultado_<id>_*`), (c) `valor_anterior`/`valor_nuevo` corresponden al estado real anterior/actual del campo. `registrar_cambio_campo` persiste estos valores tal cual en `AuditLog` sin contraste alguno.
- **Impacto:** cualquier usuario autenticado (incluso el rol más bajo, ej. RECEPCION o CAJERO) puede escribir entradas de auditoría completamente fabricadas — para un `modelo`/`objeto_id` inexistente, o simulando cambios que nunca ocurrieron. Esto compromete el valor forense/legal de `AuditLog`, usado en el sistema como bitácora NOM-024/COFEPRIS: un atacante interno podría (1) inundar el log con ruido para dificultar una investigación real, o (2) crear una narrativa falsa de auditoría (ej. registrar un "cambio" atribuido a un valor distinto al real) para desviar la atención de una manipulación real hecha por otra vía.
- **Corrección aplicada:** el endpoint legacy `api_auditar_campo` queda deprecado con `410`; el endpoint activo solo acepta IDs `resultado_<detalle_id>`, resuelve `DetalleOrden` dentro de la empresa efectiva, obtiene `valor_anterior` desde el servidor y elimina el fallback genérico para objetos inexistentes.
- **Verificación local:** `core.tests.test_auditoria_campo_security` (3 pruebas OK), `manage.py check` OK.
- **Estado:** corregido, desplegado y verificado en producción en la revisión `2c3a0247e7032087678e9f9f7f315f4bc0d599b2`; migraciones sin pendientes, servicios activos y health check exitoso.

## H-NUEVO-17 — Portal público de autofactura (IDOR): expone nombre de paciente y monto de venta por folio adivinable, sin autenticación
- **Archivos:** `core/views/autofactura.py::autofactura_publica` (línea 79-219), `core/templates/core/autofactura_publica.html` (línea 132-145).
- **Problema:** el endpoint público `/facturacion/autofactura/?folio=<folio>` (sin login) busca `Venta.objects.filter(folio_operacion=folio, estado='COMPLETADA')` y, si existe, renderiza en el HTML el nombre completo del paciente (`venta.paciente.nombre_completo`), la fecha/hora de la compra y el monto total — para CUALQUIER folio que el visitante escriba, sin verificar que quien consulta sea el dueño real de esa venta (no se pide teléfono, email, RFC, ni ningún dato adicional de posesión del ticket). El propio docstring documenta el formato de folio como secuencial y predecible (`VTA-0001`).
- **Impacto:** un atacante no autenticado puede enumerar folios secuenciales (`VTA-0001`, `VTA-0002`, ...) y cosechar nombre completo + fecha + monto de compra de pacientes de cualquier empresa del sistema. Al tratarse de un laboratorio/farmacia clínica, la sola confirmación de que una persona compró algo en una fecha específica ya es un dato sensible de salud indirecto (revela que visitó el laboratorio/farmacia). Es una fuga de PII vía IDOR.
- **Mitigante parcial:** rate limit de 20 intentos / 5 minutos por IP (`cache`) — reduce pero no elimina la enumeración (alcanzable con múltiples IPs o distribuido en el tiempo); además cualquier intento fallido O exitoso consume el mismo contador, por lo que un atacante paciente igual puede recolectar cientos de folios por hora.
- **Corrección aplicada:** el QR y enlace del ticket incluyen un token HMAC ligado a `empresa_id` y `folio_operacion`. Sin token válido, el portal no carga ni muestra la venta y no permite registrar la solicitud. La comparación es constante y el folio por sí solo deja de ser suficiente.
- **Verificación local:** `core.tests.test_autofactura_token` OK; `manage.py check` y compilación OK.
- **Estado:** corregido, desplegado y verificado en producción en la revisión `c1837ee0eaf9eb859eb7db58cf3274c95e7f6cda`; migraciones sin pendientes, servicios activos y health check exitoso.

## H-NUEVO-20 — `LAB_VALIDATION_PIN` comparado con `!=` directo (no `secrets.compare_digest`); PIN único global compartido por todo el deployment — PARCIALMENTE CORREGIDO
- **Archivos:** `core/views/laboratorio.py::api_validar_pin` (línea ~1380-1409), `core/views/laboratorio/calidad.py` (mismo patrón, línea ~264-273), `mantenimiento/views/operativo.py` (línea 172-178).
- **Problema:** `if pin != validation_pin:` compara el PIN recibido del cliente contra `settings.LAB_VALIDATION_PIN` con el operador `!=` (no de tiempo constante). Además, este PIN es un único valor global de entorno (`os.environ.get("LAB_VALIDATION_PIN")`), no un secreto por tenant/empresa ni por usuario — a diferencia del sistema paralelo de `blindaje_expediente.py`/`Medico.lab_validation_pin_hash`, que sí es por-médico y hasheado con SHA-256.
- **Impacto:** (1) comparación no constante en tiempo — riesgo teórico de timing attack, bajo en la práctica dada la latencia de red HTTP; (2) si el deployment es verdaderamente multi-tenant (una sola instancia Django sirviendo múltiples `Empresa`), este PIN autoriza la liberación de resultados clínicos (`estado='RESULTADOS_LISTOS'`) para TODAS las empresas del sistema con el mismo valor — cualquier filtración del PIN en un tenant compromete la validación de resultados en todos los demás. Si cada cliente tiene su propio deployment/entorno aislado, este riesgo no aplica.
- **Mitigante:** `settings.py`/`security.py` fuerzan fail-closed en producción (`RuntimeError` si no está configurado o tiene menos de 8 caracteres) — según `scripts/ai_coordination_hub.py` este comportamiento fail-closed ya fue revisado y aceptado por el equipo.
- **Corrección aplicada:** las tres comparaciones directas fueron sustituidas por `secrets.compare_digest`, manteniendo el rechazo cuando el secreto no está configurado. Esto elimina la debilidad de comparación no constante.
- **Pendiente de diseño:** el secreto sigue siendo global al deployment. Antes de convertirlo en PIN por empresa hay que definir el flujo de autorización clínica, migración de configuración y compatibilidad con las interfaces de equipos; no se presenta como cerrado hasta ejecutar ese diseño.
- **Estado:** comparación segura corregida en código local; aislamiento por empresa pendiente de diseño y pruebas.

## H-NUEVO-21 — Endpoint legacy de ordenamiento de paquetes mutaba catálogo sin tenant — RETIRADO
- **Archivo:** `core/views/paquetes.py::api_actualizar_orden_paquete`.
- **Problema:** la vista autenticada modificaba `laboratorio.Estudio`, cuyo modelo legacy no tiene FK `empresa`, y tampoco filtraba el paquete ni los estudios por tenant. Si se registraba una URL hacia ella, cualquier usuario autenticado podía modificar el orden almacenado en el catálogo global.
- **Evidencia:** no existen referencias activas a `api_actualizar_orden_paquete` en URLs, templates ni código de aplicación; el catálogo vigente es el de LIMS con aislamiento por empresa.
- **Corrección aplicada:** la ruta legacy responde `410 Gone` antes de ejecutar cualquier consulta o escritura. No se alteran datos ni el flujo vigente.
- **Verificación:** búsqueda exhaustiva sin callers activos, compilación del módulo y `manage.py check` sin incidencias.
- **Estado:** corregido localmente; pendiente despliegue junto con la revisión actual.

## H-NUEVO-22 — `api_confirmar_accion` (asistente PRIS) permite validar resultados clínicos sin verificar el rol del usuario, solo tenant + login — CORREGIDO
- **Archivo:** `core/views/pris_jarvis.py::api_confirmar_accion` (línea 617-648), `_ejecutar_accion_confirmada` (línea 669-783), contraste con `lista_acciones_pris` (línea 791-808). Implementación duplicada con el mismo defecto en `core/views/pris_ia/views.py::api_confirmar_accion` (línea 346-365), que también delega en `_ejecutar_accion_confirmada` con idéntica falta de verificación de rol.
- **Problema:** `lista_acciones_pris` SÍ filtra por rol qué `AccionPRIS` puede ver cada usuario (`QUIMICO` → solo `laboratorio.*`, `CAJERO`/`GERENTE` → solo `farmacia.*`, otros roles → nada salvo `ADMIN`/`DIRECTOR`/superuser). Sin embargo, el endpoint que EJECUTA la acción (`api_confirmar_accion`) solo valida `empresa=empresa` (tenant) y `estado == PENDIENTE` — NO repite el filtro de rol. Es un caso clásico de "seguridad solo en la UI": la restricción de rol vive únicamente en el queryset de la vista de listado, no en el endpoint de mutación.
- **Impacto:** cualquier usuario autenticado de la empresa (ej. RECEPCION, sin ningún permiso de laboratorio) que conozca o adivine un `accion_id` (entero secuencial, tenant-scoped, fácilmente enumerable probando IDs consecutivos) puede hacer `POST /pris/accion/<id>/confirmar/` directamente y ejecutar `_ejecutar_accion_confirmada`, que para el tipo `laboratorio.validar_resultado` marca `Resultado.validado=True, validado_por=<ese usuario>` — es decir, firma electrónicamente la validación de un resultado clínico de laboratorio sin ser químico ni tener la calificación profesional requerida (relevante para NOM-007/COFEPRIS, donde la validación de resultados debe ser hecha por personal calificado).
- **Corrección aplicada:** se centralizó `_puede_confirmar_accion(accion, usuario)` en `core/views/pris_jarvis.py` y se aplica a confirmar, rechazar y a la vista web. El permiso se calcula por `modulo_destino`, con superusuario explícito y denegación por defecto para módulos no reconocidos.
- **Verificación adicional de enrutamiento:** las rutas reales (`config/urls.py`, líneas 138 y 660-661) resuelven `core.views.pris_ia.api_confirmar_accion`/`api_rechazar_accion` contra el paquete `pris_ia/__init__.py`, cuyo import final (línea 37-52) sobreescribe el nombre con la versión de `pris_jarvis.py` — por lo tanto el endpoint efectivamente expuesto YA usa la versión corregida. La implementación duplicada en `core/views/pris_ia/views.py` (línea 346-383) sigue sin el chequeo de rol, pero queda inalcanzable por ruteo (solo importada en tests para `asistente_chat`, no para `api_confirmar_accion`); se recomienda eliminarla o alinearla para evitar confusión futura.
- **Verificación:** pruebas aisladas de la matriz de roles y compilación; el tenant sigue filtrándose en la consulta de la acción.
- **Estado:** corregido localmente en la ruta expuesta; pendiente despliegue de esta revisión y limpieza de la copia muerta en `pris_ia/views.py`.

## H-NUEVO-23 — Creación de CxC con folio `count()+1` y reintento no idempotente — CORREGIDO
- **Archivo:** `core/views/cuentas_por_cobrar.py::api_crear_cxc`.
- **Problema:** el folio se calculaba con `count()+1` sin bloqueo; solicitudes concurrentes podían competir por el mismo folio único. La misma orden también podía generar más de una cuenta si el cliente reintentaba el POST.
- **Corrección aplicada:** dentro de `transaction.atomic()` se bloquea la fila de `Empresa` antes de calcular el folio y se rechaza una CxC existente para la misma orden con HTTP 409. El tenant y convenio siguen filtrados por empresa.
- **Verificación:** compilación, `manage.py check` y revisión del flujo transaccional; pendiente despliegue de esta revisión.
- **Estado:** corregido localmente; pendiente despliegue.

## H-NUEVO-24 — Vistas LIMS exponían equipos/analitos cross-tenant y permitían notificar pánico con analito ajeno — CORREGIDO
- **Archivos:** `core/views/laboratorio/captura.py`, `core/views/laboratorio/calidad.py`, `core/views/laboratorio/config_lims.py`.
- **Problema:** captura y calidad consultaban equipos/analitos sin empresa; `registrar_notificacion_panico` aceptaba un analito que no pertenecía a la orden y `configurar_rangos` resolvía un analito solo por ID.
- **Corrección aplicada:** todos los catálogos quedan filtrados por empresa; el analito de pánico debe pertenecer a la orden y al tenant, y el acceso a rangos exige empresa.
- **Estado:** corregido localmente; pendiente despliegue.
- **Estado:** pendiente de decisión del usuario.

## H-NUEVO-26 — `NameError` no capturado en `api_cobrar_orden` (cobro de laboratorio) ante error operacional de base de datos
- **Archivo:** `core/views/laboratorio/caja.py::api_cobrar_orden`, línea 269: `except (IntegrityError, OperationalError, ValueError, TypeError) as e:`.
- **Problema:** `OperationalError` se usa en la tupla de excepciones capturadas pero nunca se importa en el archivo (los imports de `django.db` en la cabecera son solo `transaction, IntegrityError` y `models`). Si en producción ocurre un `django.db.OperationalError` real (ej. timeout de bloqueo por el `select_for_update()` usado en la misma función bajo alta concurrencia), Python lanza `NameError: name 'OperationalError' is not defined` al evaluar la cláusula `except`, en vez de manejarlo con el JSON de error 500 previsto.
- **Impacto:** bajo/operacional, no de seguridad — convierte un error transitorio de base de datos (contención de bloqueo durante un cobro) en una excepción no controlada, perdiendo el logging de bitácora crítica ("FALLO EN COBRO") y devolviendo un 500 genérico de Django en vez del JSON estructurado. No hay pérdida de datos ni riesgo de doble cobro (la idempotencia por `client_mutation_id` sigue vigente).
- **Corrección aplicada:** se agregó `OperationalError` al import de `django.db`, por lo que el handler de último recurso vuelve a capturar correctamente los bloqueos/errores operacionales.
- **Verificación:** compilación del módulo y `manage.py check` correctos.
- **Estado:** corregido localmente; pendiente despliegue.

## H-NUEVO-13 — `core/admin.py` (archivo raíz) es código MUERTO/huérfano, duplica registros de `core/admin/` — CORREGIDO
- **Archivo:** `core/admin.py` (41 KB, ~700+ líneas).
- **Hallazgo:** confirmado empíricamente (`importlib.util.find_spec('core.admin')` → resuelve a `core/admin/__init__.py`). Python resuelve el paquete `core/admin/` con prioridad sobre el módulo `core/admin.py` cuando ambos coexisten en el mismo directorio — por lo tanto Django `autodiscover()` **nunca importa `core/admin.py`**. Su contenido (registros duplicados de `Usuario`, `Producto`, `Venta`, `Paciente`, etc., aparentemente el archivo monolítico previo a la migración al paquete `core/admin/`) es completamente inerte.
- **Impacto:** ninguno funcional (nunca se ejecuta), pero es fuente de confusión para mantenimiento — un desarrollador podría editar `core/admin.py` pensando que afecta el admin real, sin efecto alguno.
- **Recomendación:** eliminar `core/admin.py` para evitar confusión, o consolidar si contiene alguna diferencia relevante no migrada al paquete.
- **Estado:** eliminado tras confirmar que `core.admin` resuelve al paquete `core/admin/` y no existían referencias activas.

## H-NUEVO-25 — Monolitos legacy de vistas duplicados — CORREGIDO
- **Archivos:** `core/views/laboratorio.py` (134 KB), `core/views/medico.py` (46 KB), `core/views/pris_ia.py` (79 KB) vs. los paquetes `core/views/laboratorio/`, `core/views/medico/`, `core/views/pris_ia/`.
- **Hallazgo:** confirmado empíricamente con `importlib.util.find_spec('core.views.laboratorio'|'medico'|'pris_ia').origin` — los tres resuelven al `__init__.py` del paquete, nunca al archivo plano. Los `__init__.py` de `laboratorio/` y `pris_ia/` documentan explícitamente "Este archivo sustituye al monolito core/views/<nombre>.py". Todos los imports reales en `config/urls.py`, `laboratorio/urls.py`, tests y management commands usan `from core.views.laboratorio import ...` / `from core.views.medico import ...` / `from core.views.pris_ia import ...`, que se resuelven contra el paquete. Los tres archivos planos son inertes.
- **Impacto:** ninguno funcional, pero riesgo de mantenimiento — un desarrollador (o auditor) podría revisar/editar el archivo plano pensando que refleja el comportamiento real. Nota de transparencia: partes de mi propia auditoría del Bloque 5 sobre estos tres archivos (decoradores, patrones de tenant scoping) se hicieron inicialmente contra los archivos planos; los hallazgos reportados (`H-NUEVO-20`, `H-NUEVO-21`, verificación de `H-NUEVO-11`) fueron re-confirmados directamente contra el código vivo en los paquetes correspondientes (`laboratorio/calidad.py`, `pris_ia/views.py` + `pris_jarvis.py`), por lo que siguen siendo válidos.
- **Corrección aplicada:** eliminados los tres archivos planos después de verificar que `find_spec` resuelve los imports hacia los paquetes y que no existen referencias a rutas de archivo. Los paquetes activos conservan las APIs públicas mediante sus `__init__.py`.
- **Verificación:** `django.setup()` e importación de `core.views.laboratorio`, `core.views.medico` y `core.views.pris_ia` correctos; se ejecutarán `manage.py check` y pruebas dirigidas antes del despliegue.
- **Estado:** corregido localmente; pendiente despliegue.

## H-NUEVO-27 — `core/management/commands/resetear_usuarios_acceso.py`: credenciales en texto plano de empleados reales (incluye superusuario) hardcodeadas en el código fuente — CRÍTICO, CORREGIDO
- **Ubicación:** `core/management/commands/resetear_usuarios_acceso.py:20-92`.
- **Descripción:** El comando contiene una lista `usuarios_base` con usernames, nombres y **contraseñas en texto plano** de 7 empleados reales (`jonathan/Admin2026!` con `is_superuser=True`, `nancy/Nancy2026!`, `gabriela/Gabriela2026!`, `janette/Janette2026!`, `tania/Tania2026!`, `deyaneira/Deyaneira2026!`, `brizia/Brizia2026!`). Al ejecutarse: (1) desactiva TODOS los demás usuarios del sistema (`User.objects.exclude(username__in=target_usernames).update(is_active=False)`, sin distinguir tenant), y (2) crea/actualiza estas 7 cuentas con las contraseñas fijas del código. **No hay ningún prompt de confirmación** (a diferencia de `wipe_datos_operativos.py` o `purgar_datos_nom035.py`).
- **Riesgo:** (a) Fuga de credenciales reales si el repositorio se expone (Git history, backups, IDE compartido); (b) contraseñas predecibles con patrón `Nombre+Año!` fácilmente adivinables; (c) ejecución accidental desactiva instantáneamente a todos los usuarios de todos los tenants sin posibilidad de `--dry-run` ni confirmación.
- **Recomendación:** Eliminar el comando o migrarlo al patrón ya usado en `crear_usuarios_produccion.py`/`crear_superusuario_prod.py` (contraseña vía variable de entorno, `CommandError` si falta, longitud mínima, sin defaults). Rotar inmediatamente las contraseñas de los 7 usuarios listados si el comando llegó a ejecutarse alguna vez en un entorno real.

## H-NUEVO-28 — `core/management/commands/resetear_personal_final.py`: contraseña default débil compartida (`Prislab2026`) para TODOS los usuarios activos del sistema, sin confirmación ni tenant scoping — ALTO, CORREGIDO
- **Ubicación:** `core/management/commands/resetear_personal_final.py:31,57-70`.
- **Descripción:** `--password` tiene default hardcodeado `"Prislab2026"`. Si se ejecuta sin el flag, **todas** las cuentas `is_active=True` de **todos los tenants** quedan con esa misma contraseña, y las cuentas `is_active=False` no protegidas se **eliminan físicamente** (`desactivadas.delete()`), sin `transaction.atomic()` envolviendo ambas fases y sin prompt de confirmación (solo existe `--dry-run`, opt-in).
- **Riesgo:** contraseña única, predecible, y compartida entre múltiples cuentas de múltiples empresas — un compromiso de una cuenta compromete a todas hasta que cada usuario cambie su clave manualmente; no hay mecanismo que fuerce el cambio en el primer login.
- **Recomendación:** Eliminar el default; exigir `--password` explícito o generar una contraseña aleatoria distinta por usuario (como ya hace `OnboardingCrearEmpresaView._generar_password_temporal` en `core/views/onboarding.py`); agregar confirmación interactiva salvo `--force`; envolver ambas fases en `transaction.atomic()`.

## H-NUEVO-29 — `core/management/commands/wipe_datos_operativos.py`: borra `AuditLog` (bitácora que debe ser append-only) y opera sobre TODOS los tenants sin scoping ni verificación de entorno — MEDIO, CORREGIDO
- **Ubicación:** `core/management/commands/wipe_datos_operativos.py:212-214,59-63`.
- **Descripción:** El comando borra permanentemente `AuditLog`, `HistorialResultados`, `IncidenciaSentinel` y todos los registros transaccionales de **todas las empresas** (no acepta `--empresa`), contradiciendo el principio de append-only documentado para `AuditLog`/`ForenseAcceso` en el resto del proyecto (ver "Confirmaciones positivas"). La única protección es escribir la frase `CONFIRMAR_WIPE_PRISLAB`, y el flag `--yes` la omite por completo sin ninguna otra verificación (no chequea `settings.DEBUG`, `IS_PRODUCTION`, ni pide `--empresa-id`).
- **Riesgo:** ejecución accidental (o de un script CI mal configurado con `--yes`) contra la base de producción destruye irreversiblemente la bitácora de auditoría forense y expedientes clínicos de todos los clientes simultáneamente.
- **Recomendación:** Añadir verificación explícita de entorno (bloquear si `settings.IS_PRODUCTION`/`DEBUG=False` salvo variable de entorno adicional dedicada), excluir `AuditLog`/`ForenseAcceso` del wipe (o exportarlos antes de borrar), y permitir/objetar por `--empresa-id` en vez de operar siempre global.

## H-NUEVO-30 — `core/management/commands/unificar_empresa_prislab.py`: fusión destructiva multi-tenant sin guardarraíl de entorno ni confirmación — MEDIO, CORREGIDO
- **Ubicación:** `core/management/commands/unificar_empresa_prislab.py` (completo).
- **Descripción:** El comando reasigna todas las FKs de `Empresa`/`Sucursal` de las empresas "fuente" hacia una empresa destino y luego **elimina** las empresas fuente (`Empresa.objects.filter(pk__in=source_ids).delete()`), colapsando el aislamiento multi-tenant. El docstring indica "desarrollo/datos de prueba", pero el comando no verifica `settings.DEBUG` ni pide ninguna confirmación interactiva (solo `--dry-run`, opt-in) antes de ejecutar la fusión real.
- **Riesgo:** si se invoca por error contra una base de producción con múltiples clientes reales, fusionaría y eliminaría empresas de clientes distintos de forma irreversible.
- **Recomendación:** Añadir guardia `if not settings.DEBUG: raise CommandError(...)` (o variable de entorno explícita `ALLOW_TENANT_MERGE`), y exigir confirmación interactiva antes de ejecutar sin `--dry-run`.

## H-NUEVO-31 — `core/management/commands/backup_nocturno.py::_generar_clave_encriptacion`: clave AES derivada de `SECRET_KEY` con salt fijo hardcodeado — MEDIO, CORREGIDO
- **Ubicación:** `core/management/commands/backup_nocturno.py:327-341`.
- **Descripción:** La clave que cifra el backup nocturno completo (BD + media + expedientes clínicos + firmas digitales) se deriva con `PBKDF2HMAC(password=settings.SECRET_KEY, salt=b'prislab_backup_salt_2025', ...)`. El salt es una constante fija en el código fuente, igual en todos los despliegues de este proyecto, y la contraseña es el mismo `SECRET_KEY` que Django usa para firmar sesiones, CSRF y tokens. A diferencia de `backup_database.py` (que exige un `FERNET_KEY` independiente y falla cerrado si no está configurado), este comando no tiene una clave de cifrado dedicada.
- **Riesgo:** (a) si `SECRET_KEY` se filtra (escenario común: commit accidental, `.env` expuesto), el atacante puede derivar la clave de cifrado de **todos** los backups nocturnos pasados y futuros sin necesitar acceso adicional al servidor; (b) si `SECRET_KEY` se rota tras un incidente de seguridad (la respuesta estándar), los backups ya cifrados quedan indescifrables porque la clave de derivación cambia junto con ella — no hay versión histórica de clave conservada.
- **Recomendación:** Usar una clave de cifrado dedicada (ej. `BACKUP_ENCRYPTION_KEY`/`FERNET_KEY`, igual que `backup_database.py`) desacoplada de `SECRET_KEY`, y un salt aleatorio generado una vez por instalación (almacenado junto al backup o en variable de entorno), no una constante en el código fuente.

## Corrección H-NUEVO-27 a H-NUEVO-31 — verificada 2026-07-30

Los cinco hallazgos del bloque de comandos fueron corregidos en el código activo:

- **H-NUEVO-27:** `resetear_usuarios_acceso.py` ya no contiene contraseñas; exige
  `PRISLAB_ACCESS_RESET_PASSWORD`, mínimo de 12 caracteres y `--confirm-reset`.
- **H-NUEVO-28:** `resetear_personal_final.py` ya no tiene contraseña por defecto,
  no imprime secretos y exige variable de entorno y confirmación explícita.
- **H-NUEVO-29:** `wipe_datos_operativos.py` está bloqueado en producción y ya no
  elimina `AuditLog`.
- **H-NUEVO-30:** `unificar_empresa_prislab.py` funciona en simulación por defecto;
  la aplicación exige `--apply` y `--confirm-merge`, y está bloqueada en producción.
- **H-NUEVO-31:** `backup_nocturno.py` y `verificar_backup_cifrado.py` usan la clave
  Fernet dedicada `PRISLAB_BACKUP_ENCRYPTION_KEY`; ya no derivan claves desde
  `SECRET_KEY` ni usan salt fijo.

Evidencia: `manage.py check`, compilación de los seis comandos y cinco pruebas de
seguridad en `core/tests/test_management_command_safety.py`. Los hallazgos
H-NUEVO-32, H-NUEVO-33 y H-NUEVO-34 fueron corregidos y desplegados en las rondas
correspondientes.

Producción: se configuró una clave Fernet dedicada en `.env` (sin exponer su
valor) y se verificó que tiene formato válido. Despliegue de código:
`c4bcf50bf96b669e9a80c69142b3c738747e6ad5`.

## H-NUEVO-32 — Inyección de markup ReportLab en PDFs médicos/legales oficiales (recetas, resultados de laboratorio, consentimiento informado) — MEDIO-ALTO, CORREGIDO
- **Ubicación:**
  - `core/services/motor_recetas.py::_safe()` (líneas 81-120) — no escapa `<`,`>`,`&`.
  - `core/services/motor_reportes_lab.py::_safe_str()` (líneas 119-187) — mismo problema.
  - `core/views/consentimiento_digital.py::_generar_pdf_consentimiento()` (líneas 124-133) — **más severo**: NO usa ninguna función de saneamiento; `paciente_nombre`, `estudio_nombre` y `empresa_nombre` se insertan directo, sin escapar, en `Paragraph(f'Yo, <b>{paciente_nombre}</b>, declaro...')`. Peor aún, en `api_guardar_consentimiento` (línea 265-266) `paciente_nombre = data.get('paciente_nombre', 'Paciente')` y `estudios_texto = data.get('estudios', ...)` provienen **directamente del body JSON del POST del cliente**, no de una consulta a base de datos — es decir, el atacante controla el valor exacto que llega a `Paragraph()` sin pasar por ningún filtro.
- **Descripción:** `reportlab.platypus.Paragraph` interpreta un subconjunto de markup tipo XML/HTML (`<b>`, `<font color=...>`, `<i>`, `<br/>`, etc.). Ninguno de los tres puntos de entrada escapa `&`, `<`, `>` antes de construir el markup final.
- **Riesgo:** 
  1. En `motor_recetas.py`/`motor_reportes_lab.py`: cualquier usuario que pueda capturar nombre de paciente, alergias, diagnóstico o indicaciones de tratamiento (MEDICO, RECEPCION) puede alterar la presentación visual de un documento clínico oficial (ej. ocultar o recolorear una alerta de alergia).
  2. En `consentimiento_digital.py`: el vector es más directo y grave porque el campo llega crudo desde el request HTTP (no desde un modelo ya validado) a un **documento con valor legal/forense** (declarado explícitamente como evidencia NOM-004/ISO 15189 de consentimiento informado). Un actor malicioso con sesión válida (cualquier usuario autenticado con acceso al endpoint `api_guardar_consentimiento`) podría manipular el contenido visual del propio texto de la declaración de consentimiento, o provocar una excepción no controlada que impida generar/regenerar el PDF de evidencia legal.
  - No es RCE (ReportLab `Paragraph` no ejecuta código), pero sí manipulación de presentación de datos clínicos/legales oficiales.
- **Recomendación:** Escapar explícitamente `&`, `<`, `>` (equivalente a `xml.sax.saxutils.escape`) en los tres puntos antes de insertar en cualquier `Paragraph(...)`; en `consentimiento_digital.py` además validar/sanear `paciente_nombre`/`estudios_texto` contra el registro real de la orden (`orden.paciente.nombre_completo`) en vez de confiar en el valor enviado por el cliente en el JSON.

## H-NUEVO-33 — `core/views/medico/receta.py::verificar_qr_receta`: IDOR — divulga diagnóstico y datos de paciente de CUALQUIER receta del tenant vía enumeración de folio secuencial — ALTO, CORREGIDO
- **Ubicación:** `core/views/medico/receta.py:338-398`; folio generado en `core/models/ventas.py::Receta.save()` (líneas 122-128).
- **Descripción:** `folio_receta` se genera con formato predecible y secuencial: `REC-{YYYYMM}-{contador_zfill5}` (ej. `REC-202607-00001`, `00002`, ...), trivialmente enumerable. La vista `verificar_qr_receta` (`@login_required`, sin `@role_required`) busca la receta **solo por `folio_receta` + `empresa`** (`Receta.objects.filter(folio_receta=folio, empresa=empresa).first()`) — no valida que el `hash` recibido en el QR coincida antes de devolver los datos: `autentica = hash_calculado == hash_recibido == receta.hash_verificacion` se calcula pero **no se usa como gate**; el bloque `return JsonResponse({..., 'receta': {diagnostico, paciente, medico, cedula, fecha_emision}, ...})` se ejecuta siempre que la receta exista, incluso con `autentica: False`.
- **Riesgo:** cualquier usuario autenticado del tenant (sin necesidad de rol médico — un CAJERO o RECEPCION con sesión válida) puede iterar folios secuenciales del mes (`REC-202607-00001` a `NNNNN`) y obtener el **diagnóstico principal y nombre completo** de cada paciente con receta ese mes, sin poseer el QR físico ni el hash real. Esto es una fuga de datos de salud (NOM-024/LFPDPPP) por control de acceso roto (IDOR), no requiere ningún conocimiento previo del folio real.
- **Recomendación:** (1) Hacer que `autentica` sea un gate real: si `hash_recibido != receta.hash_verificacion`, responder 403/404 sin incluir el bloque `receta` con datos clínicos. (2) Sustituir `folio_receta` secuencial por un identificador no adivinable (UUID) para el campo usado en verificación pública, o exigir el hash completo como parte de la búsqueda (`filter(folio_receta=folio, hash_verificacion=hash_recibido, empresa=empresa)`) en vez de solo el folio. (3) Considerar `@role_required` adicional si la vista no está pensada para todos los roles del tenant.

## Corrección verificada H-NUEVO-32 y H-NUEVO-33

- **H-NUEVO-32 — CORREGIDO:** `motor_recetas._safe`, `motor_reportes_lab._safe_str` y `_generar_pdf_consentimiento` escapan `&`, `<` y `>` antes de construir contenido para ReportLab. `api_guardar_consentimiento` obtiene paciente y estudios de la `OrdenDeServicio` del tenant, en lugar de confiar en esos valores del JSON del cliente.
- **H-NUEVO-33 — CORREGIDO:** `verificar_qr_receta` exige coincidencia constante entre el hash calculado, el hash recibido y el hash persistido. Un hash inválido responde HTTP 403 sin incluir diagnóstico ni datos del paciente.
- **Evidencia:** `core/tests/test_pdf_and_qr_security.py` (2 pruebas OK), `python manage.py check` sin errores y compilación de los cuatro archivos modificados sin errores.
- **Despliegue:** revisión `405035581bdebb96f818590e9c60f98834c20112` activa en producción; migraciones sin cambios pendientes y servicios activos. La prueba `core.tests.test_lab_validation_pdf` quedó bloqueada durante la creación de la base de pruebas local; no se usa como evidencia de cierre.

## H-NUEVO-34 — `core/views/laboratorio/calidad.py::api_finalizar_toma`: audio de toma de muestra cae a texto plano si falta `FERNET_KEY` (fail-open, inconsistente con `EncryptedTextField`) — MEDIO, CORREGIDO
- **Ubicación:** `core/views/laboratorio/calidad.py:593-621`.
- **Descripción:** Al finalizar la toma de muestra, si el frontend envía audio (`audio_b64`), el código intenta cifrarlo con Fernet: `cifrado = audio_bytes  # fallback: sin cifrar` seguido de un `try/except` que solo cifra si `FERNET_KEY` está configurada; si no lo está (o `Fernet(...)` falla), el bloque `except` solo registra un `logger.warning` y el flujo continúa guardando `audio_rec.audio_cifrado = cifrado` con el audio **en texto plano**, sin abortar la operación ni alertar al usuario. Esto contradice el patrón fail-closed ya usado en `core/fields.py::EncryptedTextField.encrypt()` (confirmado en `core/tests/test_sensitive_authorizations.py::test_encrypt_fails_closed_when_fernet_unavailable`, que exige lanzar `ImproperlyConfigured` si Fernet no está disponible).
- **Riesgo:** el audio de toma de muestra puede contener verbalización de datos de identidad, consentimiento oral y contexto clínico del paciente (dato de salud sensible). Si por error de despliegue `FERNET_KEY` no está configurada, estos audios quedan almacenados sin cifrar en la base de datos indefinidamente, sin ningún registro de auditoría que distinga "cifrado" de "sin cifrar" más allá de un log de warning fácil de pasar por alto.
- **Recomendación:** Alinear con el patrón fail-closed del resto del proyecto: si `FERNET_KEY` no está disponible, rechazar el guardado del audio (o continuar la toma sin persistir el audio) en vez de almacenarlo en claro; opcionalmente añadir un campo `cifrado: bool` en `AudioTomaMuestra` para poder auditar retroactivamente qué registros quedaron sin cifrar.
- **Corrección verificada:** el flujo ya no usa fallback en claro. Si la clave falta, es inválida o falla Fernet, no se crea ni actualiza `AudioTomaMuestra`; la toma clínica termina sin audio y la respuesta informa `audio_guardado: false` con una advertencia controlada. Con una clave válida, el audio se persiste únicamente después de `Fernet.encrypt()`.
- **Evidencia:** `core/tests/test_audio_toma_security.py` (prueba de clave ausente), `python manage.py check`, compilación de `calidad.py` y prueba aislada H-032/H-033, todos correctos.

## H-NUEVO-35 — `core/views/asistencia.py`: módulo de asistencia/RH sin ningún control de rol — cualquier empleado autenticado puede autorizar/rechazar incidencias, ver documentos de soporte y registrar entradas/salidas de otros — ALTO, CORREGIDO
- **Ubicación:** `core/views/asistencia.py` (327 líneas completas) — el archivo solo importa `login_required` de `django.contrib.auth.decorators`; NO importa `role_required` de `core.decorators` en ningún punto, a diferencia de `core/views/rh.py` y `core/views/nomina.py` (mismo dominio HR/nómina) que exigen `@role_required('DIRECTOR','ADMIN','GERENTE','RH')`.
- **Descripción:** Todas las vistas del módulo (`dashboard_asistencia`, `registro_asistencia`, `registrar_entrada_salida`, `horarios_trabajo`, `crear_horario`, `incidencias_asistencia`, `crear_incidencia`, `autorizar_incidencia`) solo exigen `@login_required`, sin restricción de rol. En particular:
  - `autorizar_incidencia` (líneas 306-327): cualquier usuario autenticado del tenant puede marcar una `IncidenciaAsistencia` (falta, permiso, incapacidad) como `AUTORIZADA` o `RECHAZADA` para **cualquier empleado**, sin pertenecer a RH/Dirección.
  - `crear_incidencia`/`registrar_entrada_salida`: cualquier usuario puede crear registros de asistencia/incidencias a nombre de **cualquier `empleado_id`** de la empresa (el campo se toma directo del POST sin validar relación jerárquica).
  - `incidencias_asistencia`/`registro_asistencia`: cualquier usuario puede listar el `motivo` y `documento_soporte` (posible incapacidad médica, justificante) de incidencias de **todos** los empleados de la empresa.
- **Riesgo:** ruptura de control de acceso en un flujo que impacta nómina/RH — un empleado sin privilegios podría autoaprobar su propia falta, alterar registros de asistencia de compañeros, o acceder a motivos/documentos médicos de incidencias ajenas (dato sensible bajo NOM-035/LFPDPPP), sin necesitar rol de supervisor.
- **Recomendación:** Aplicar `@role_required('DIRECTOR','ADMIN','GERENTE','RH')` (mismo patrón que `rh.py`/`nomina.py`) a las vistas de gestión/autorización (`autorizar_incidencia`, `incidencias_asistencia`, `horarios_trabajo`, `crear_horario`), y limitar `registrar_entrada_salida`/`crear_incidencia` de autoservicio a que el `empleado_id` corresponda al propio `request.user` salvo que el actor tenga rol de supervisor.

### Corrección verificada H-NUEVO-35

- Paneles, horarios, listados globales y autorización exigen `ADMIN`, `DIRECTOR`, `GERENTE`, `FARMACIA` o `RH`.
- El autoservicio conserva registro y alta de la propia persona, pero el empleado objetivo se resuelve con `usuario=request.user`; las consultas de incidencias también quedan limitadas al propio empleado.
- Evidencia: `core/tests/test_asistencia_security.py` (2 pruebas OK), `python manage.py check` y compilación sin errores.

## H-NUEVO-36 — `core/views/catalogos_maestros.py`: cualquier usuario autenticado (sin rol ni tenant) puede sobrescribir masivamente el catálogo GLOBAL `laboratorio.Estudio` compartido por TODOS los clientes de PRISLAB — CRÍTICO, CORREGIDO
- **Ubicación:** `core/views/catalogos_maestros.py` (225 líneas completas); modelo `laboratorio.models.clinico.Estudio` (confirmado sin campo `empresa` — tabla global, no tenant-scoped).
- **Descripción:** Las 5 vistas del archivo (`gestionar_metodos`, `api_obtener_metodo`, `api_actualizar_metodo`, `gestionar_muestras`, `api_actualizar_muestra`) solo tienen `@login_required`, **sin `@role_required` ni ningún otro control de acceso**, y ninguna de sus queries filtra por `empresa` — porque el modelo subyacente `laboratorio.Estudio` (import `from laboratorio.models import Estudio as EstudioLab`) **no tiene campo `empresa`**, es decir, es una tabla compartida globalmente entre todos los tenants de la plataforma. `api_actualizar_metodo`/`api_actualizar_muestra`, con `actualizar_estudios=True`, ejecutan `estudios_afectados.update(metodo=metodo_nuevo)` / `.update(muestra_requerida=muestra_nueva)` sobre **todos** los `Estudio` que coincidan con el valor anterior, sin distinguir a qué cliente pertenecen.
- Esto contradice una nota de auditoría previa (`core/views/paquetes.py`, ver Bloque 5) que asumía que `laboratorio.Estudio` "no tenía callers activos" y por eso se dejó sin proteger — esa suposición es **incorrecta**: `catalogos_maestros.py` es un caller activo real y alcanzable vía URL autenticada. **Confirmación adicional:** `core/views/cotizacion.py::api_buscar_estudios_cotizacion` (línea 136-150) también consulta `LabEstudio`/`PerfilLaboratorio` (mismos modelos) **sin ningún filtro por `empresa`**, con un comentario explícito en el código: *"PerfilLaboratorio no tiene FK a empresa en el modelo actual. Filtrar por `empresa` aquí dispara FieldError y rompe la cotización."* — es decir, el propio equipo de desarrollo ya detectó la falta de tenant-scoping en este modelo y optó por omitir el filtro en vez de corregir el modelo, confirmando que esta es una funcionalidad **viva y en uso activo** (UI de "Cotización Flash"), no código muerto.
- **Riesgo:** cualquier usuario autenticado de **cualquier tenant**, sin necesidad de rol administrativo, puede renombrar en bloque valores de "método" o "muestra requerida" de estudios de laboratorio que pertenecen potencialmente a **otras empresas clientes de PRISLAB**, corrompiendo catálogos ajenos (integridad de datos clínicos/operativos cross-tenant). No hay aislamiento de ningún tipo — es una violación directa del principio fundamental multi-tenant de la plataforma.
- **Recomendación:** (1) Verificar con máxima prioridad si `laboratorio.Estudio` todavía tiene registros activos en producción y si son compartidos entre tenants o son remanentes de una migración; (2) si el modelo sigue en uso, agregar `empresa` FK y migrar datos, filtrando todas las queries de este archivo por `empresa=request.user.empresa`; (3) mientras tanto, aplicar `@role_required('DIRECTOR_QC','ADMIN')` (mismo patrón que `catalogos.py`) a las 5 vistas como mitigación inmediata; (4) si el modelo es verdaderamente legacy/muerto como se documentó para `paquetes.py`, retirar `catalogos_maestros.py` también, en vez de dejarlo como caller activo sin protección.

### Corrección verificada H-NUEVO-36

- Las vistas de lectura requieren rol administrativo.
- Las mutaciones `api_actualizar_metodo` y `api_actualizar_muestra` están reservadas al superusuario porque `Estudio` sigue siendo global y no permite aislamiento por tenant.
- `cotizacion.py::api_buscar_estudios_cotizacion` conserva lectura autenticada del catálogo global; solo devuelve metadatos del estudio/perfil (nombre, código, precio, categoría, descripción y conteo), no pacientes, resultados ni configuración de otro tenant. Se mantiene como deuda arquitectónica para migrar el catálogo a tenant-scoped.
- Un administrador de empresa recibe HTTP 403 y no se ejecuta ningún `.update()` masivo. Evidencia: `core/tests/test_catalogos_maestros_security.py` (2 pruebas OK).

## H-NUEVO-37 — `core/views/dashboard_unificado.py`: dashboard ejecutivo consolidado (margen bruto, nómina total, pipeline CRM) accesible a cualquier empleado autenticado, sin `@role_required` — MEDIO, CORREGIDO
- **Ubicación:** `core/views/dashboard_unificado.py::dashboard_unificado` y `api_kpis_tiempo_real` (364 líneas completas); ruta registrada en `config/urls.py:581` (`path('dashboard-unificado/', views.dashboard_unificado, name='dashboard_unificado')`).
- **Descripción histórica:** antes de la corrección ambas vistas solo tenían `@login_required`. El dashboard consolida y expone: `utilidad_bruta`/`margen_bruto` (rentabilidad real del negocio), `total_pagado_nomina` (nómina total pagada en el periodo), `valor_pipeline`/`oportunidades_abiertas` (pipeline de ventas CRM) y `porcentaje_ventas_marketing`. Esto contrastaba con `core/views/motor_financiero.py`, que expone datos financieros equivalentes o menos sensibles bajo `@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')`.
- **Riesgo histórico:** cualquier empleado autenticado del tenant (ej. un CAJERO o RECEPCIONISTA) podía consultar la rentabilidad bruta del negocio y el total de nómina pagada a todo el personal, información confidencial que normalmente solo debería ver Dirección/Finanzas.
- **Corrección aplicada:** `dashboard_unificado` y `api_kpis_tiempo_real` exigen `@role_required('ADMIN', 'DIRECTOR', 'GERENTE', 'FINANZAS')`. Los roles operativos reciben HTTP 403 antes de ejecutar la consulta financiera.
- **Evidencia:** `core/tests/test_dashboard_and_panic_security.py` verifica denegación para `CAJERO` y `RECEPCION`; `manage.py check`, compilación de los archivos modificados y `git diff --check` pasan. El test existente con base de datos `core.tests.test_dashboard_unificado` no concluyó porque la creación local de la base de datos de pruebas quedó bloqueada; no se contabiliza como aprobado.

## H-NUEVO-38 — `core/views/laboratorio_captura.py::registrar_notificacion_panico`: el check IDOR solo registra un warning y NO bloquea la operación — permite fabricar notificaciones de valor crítico para analitos no ordenados — MEDIO, CORREGIDO
- **Ubicación:** `core/views/laboratorio_captura.py:359-396`.
- **Descripción histórica:** el código validaba si el `analito_id` recibido pertenecía a la orden: `if not orden.detalles.filter(analito_id=analito_id).exists(): logger.warning('[Pánico IDOR] ...')`. Sin embargo, ese bloque **solo registraba el log de advertencia y continuaba la ejecución**, por lo que podía resolver el `Analito` por ID global y crear registros aunque nunca hubiera sido parte de la orden.
- Esto contrasta con el archivo homónimo `core/views/laboratorio/captura.py`, donde el mismo patrón de log `"[Pánico IDOR]"` (documentado como corrección de `H-NUEVO-24`) **sí aborta la operación** tras detectar la discrepancia. Aquí, en `laboratorio_captura.py` (archivo raíz, distinto de `laboratorio/captura.py`), el guardia quedó incompleto — probablemente una corrección parcial que no se replicó en ambos archivos con nombre similar.
- **Riesgo histórico:** cualquier usuario con acceso a captura de resultados (rol `QUIMICO`/`LABORATORIO`/`ADMIN`) podía registrar una notificación de valor crítico y un resultado asociado para un analito que el paciente nunca ordenó, dentro de la misma orden.
- **Corrección aplicada:** tras detectar que el analito no pertenece a la orden, la vista devuelve HTTP 400 y no continúa hacia la creación de `ResultadoParametro` ni `NotificacionPanico`.
- **Evidencia:** `core/tests/test_dashboard_and_panic_security.py` verifica el rechazo con HTTP 400; la prueba aislada de seguridad pasa junto con las dos regresiones de acceso del dashboard (3/3).

## H-NUEVO-39 — `core/views/monitor_produccion.py::api_avanzar_estado`: cualquier empleado autenticado puede validar/finalizar resultados clínicos desde el Kanban, sin exigir rol de laboratorio — ALTO, CORREGIDO
- **Ubicación:** `core/views/monitor_produccion.py:499-715` (`api_avanzar_estado`); comparar con `core/views/laboratorio_captura.py::captura_resultados_industrial` (líneas 56-76), que sí exige `rol in ('QUIMICO', 'LABORATORIO', 'ADMIN', 'ADMINISTRADOR')` o pertenencia a grupo `LABORATORIO`/`GERENCIA_OPERATIVA`.
- **Descripción histórica:** `api_avanzar_estado` no exigía rol para ninguna transición. La transición a `COMPLETO` marca la orden como `estado='RESULTADOS_LISTOS'`, genera el PDF y descuenta insumos.
- **Riesgo histórico:** un empleado sin formación clínica podía forzar la liberación de resultados sin validación formal de laboratorio.
- **Corrección aplicada:** se añadió `_puede_validar_resultados()` con el mismo criterio de `captura_resultados_industrial`. El control se aplica antes de procesar la transición `VALIDADO_PARCIAL → COMPLETO`; roles operativos conservan las transiciones tempranas del monitor, pero no pueden liberar resultados.
- **Evidencia:** `core/tests/test_dashboard_and_panic_security.py` verifica el gate unitario para `CAJERO`/`LABORATORIO`; `core/tests/test_monitor_produccion_workflow.py` contiene la regresión HTTP 403 y la regresión del flujo autorizado. La suite con base de datos no concluyó por bloqueo al crear la base local; no se contabiliza como aprobada.

## H-NUEVO-40 — `core/views/transferencias.py::api_buscar_productos_transferencia`: `Q` no está importado — `NameError` en tiempo de ejecución al buscar por texto — BAJO/FUNCIONAL, CORREGIDO
- **Ubicación:** `core/views/transferencias.py:1-19` (imports) y línea 318-321 (uso de `Q`).
- **Descripción:** El archivo importa `render`, `get_object_or_404`, `redirect`, `login_required`, `messages`, `JsonResponse`, `transaction`, `require_http_methods`, `Paginator`, `timezone`, `Decimal`, `datetime`, modelos y `logging`, pero **nunca `from django.db.models import Q`**. Sin embargo, `api_buscar_productos_transferencia` usa `Q(nombre__icontains=query) | Q(codigo_barras__icontains=query)` cuando el parámetro `q` viene en el query string. Esto genera un `NameError: name 'Q' is not defined` no capturado (no hay try/except alrededor), devolviendo un 500 sin manejar cada vez que un usuario escribe texto en el buscador de productos para transferencias.
- **Riesgo:** no es una vulnerabilidad de seguridad, pero rompe una funcionalidad operativa activa (búsqueda de productos al crear una transferencia entre sucursales) cada vez que se usa el filtro de texto — solo funciona si se filtra exclusivamente por `sucursal_id`.
- **Corrección aplicada:** se agregó `from django.db.models import Q` y se cubrió la búsqueda con texto con una prueba de regresión que confirma respuesta JSON 200.
- **Evidencia:** `core.tests.test_dashboard_and_panic_security` pasa 6/6, además de `manage.py check`, compilación Python y `git diff --check`.

## H-NUEVO-41 — `core/views/audio_legal.py::api_verificar_integridad_audio` + `core/utils/pris_audio_vision.py::verificar_integridad`: IDOR sin filtro de tenant sobre `VoiceAuditLog` — BAJO, CORREGIDO
- **Ubicación:** `core/views/audio_legal.py:51-64`; `core/utils/pris_audio_vision.py:93-117` (`verificar_integridad`).
- **Descripción histórica:** `api_verificar_integridad_audio` delegaba a `verificar_integridad(registro_id)`, que ejecutaba `VoiceAuditLog.objects.get(pk=registro_id)` sin filtro por empresa.
- **Riesgo histórico:** un usuario autenticado podía confirmar existencia y timestamps de actividad de voz de otro tenant mediante IDs secuenciales.
- **Corrección aplicada:** la vista exige empresa y la función de verificación recibe `empresa` obligatoriamente y consulta `VoiceAuditLog.objects.get(pk=registro_id, empresa=empresa)`. Sin empresa, la vista responde 403.
- **Evidencia:** `core.tests.test_dashboard_and_panic_security` verifica que la consulta siempre incluye `empresa`; la suite aislada pasa 6/6.

## H-NUEVO-42 — `core/views/administracion_usuarios.py::api_actualizar_usuario`: gate de acceso solo por `is_staff` (no por rol específico) permite escalación de privilegios — ALTO, CORREGIDO
- **Ubicación:** `core/views/administracion_usuarios.py:115-254`.
- **Descripción histórica:** el endpoint confiaba en `is_staff` sin exigir un rol administrativo y permitía actualizar campos privilegiados.
- **Riesgo histórico:** una cuenta staff no administrativa podía elevar roles, conservar `is_staff` o desactivar cuentas del tenant.
- **Corrección aplicada:** la vista exige `role_required('ADMIN', 'DIRECTOR', 'GERENTE')`, mantiene el aislamiento por empresa y bloquea que el actor modifique su propio `rol`, `is_staff` o `is_active`.
- **Evidencia:** `core.tests.test_dashboard_and_panic_security` verifica que un `CAJERO` staff recibe 403; `manage.py check`, compilación y `git diff --check` pasan.

## H-NUEVO-43 — `core/views/administracion_usuarios.py::api_actualizar_tarifa`: mutación cross-tenant del catálogo GLOBAL `laboratorio.Estudio.precio_base`, sin filtro de empresa — CRÍTICO, CORREGIDO
- **Ubicación:** `core/views/administracion_usuarios.py:257-327`.
- **Descripción histórica:** el endpoint permitía a cualquier staff modificar `laboratorio.Estudio.precio_base`, aunque `Estudio` es un catálogo global sin empresa.
- **Riesgo histórico:** un tenant podía alterar tarifas globales con impacto financiero sobre otros tenants.
- **Corrección aplicada:** la mutación queda reservada a superusuarios hasta que exista un modelo de tarifa tenant-scoped; un administrador de empresa recibe 403 y no se ejecuta ninguna escritura global.
- **Evidencia:** `core.tests.test_dashboard_and_panic_security` verifica que un `ADMIN` de tenant recibe 403; `manage.py check`, compilación y `git diff --check` pasan.

## H-NUEVO-44 — `core/views/autenticacion_2fa.py::_verificar_codigo_maestro`: comparación de hash del código maestro de emergencia sin tiempo constante — BAJO, CORREGIDO
- **Ubicación:** `core/views/autenticacion_2fa.py:83-88`.
- **Descripción:** `_verificar_codigo_maestro` calcula `hashlib.sha256(codigo).hexdigest() == hashlib.sha256(master).hexdigest()` usando el operador `==` de Python sobre strings, que **no es de tiempo constante** (compara byte a byte y corta en la primera diferencia). El resto del proyecto usa `secrets.compare_digest` correctamente en comparaciones de tokens sensibles (p. ej. `cron_tasks.py::_verificar_cron`), pero aquí, para el código maestro de recuperación de emergencia del CISO, se usa comparación directa de strings.
- **Riesgo:** teóricamente permite un ataque de canal lateral por temporización sobre el hash SHA-256 calculado del código candidato. La explotación práctica es muy difícil (requiere medir diferencias de nanosegundos sobre la red, y el valor comparado es un hash, no el secreto en claro), pero es una desviación del patrón de comparación segura ya usado en otras partes del código para material altamente sensible (código de bypass de 2FA para roles `ADMIN`/`DIRECTOR`).
- **Recomendación:** Sustituir `==` por `hmac.compare_digest(...)` o `secrets.compare_digest(...)` en la comparación final, consistente con el patrón ya usado en `cron_tasks.py`.
- **Corrección aplicada:** la comparación usa `secrets.compare_digest` sobre los hashes SHA-256.

## H-NUEVO-45 — `core/views/blindaje_expediente.py`: PIN-LAB (firma electrónica simple) almacenado con SHA-256 plano sin sal, comparación no constante — MEDIO, CORREGIDO
- **Ubicación:** `core/views/blindaje_expediente.py:177-178` (`sellar_con_pin`), `468-469` (`configurar_pin_lab`).
- **Descripción:** El PIN-LAB, usado como **firma electrónica simple** para sellar notas clínicas de forma legalmente vinculante (folio único, hash de expediente, evidencia forense), se almacena como `hashlib.sha256(pin.encode()).hexdigest()` — **sin sal (salt) y sin KDF lento** (no usa PBKDF2/bcrypt/Argon2, a diferencia del hasher de contraseñas de Django). Además, la verificación se hace con `pin_hash_input != medico_profile.lab_validation_pin_hash` (comparación de string estándar, no de tiempo constante).
- **Riesgo:** dado que el PIN se valida como de mínimo 4 caracteres (`len(pin) < 4`), el espacio de valores es pequeño; un hash SHA-256 sin sal de un PIN corto es trivialmente reversible por fuerza bruta/tabla arcoíris si la base de datos se filtra (a diferencia de una contraseña larga, donde SHA-256 sin sal ya es débil, pero aquí el impacto es mayor por la baja entropía del PIN). Esto compromete la robustez legal de la "firma electrónica simple" — un atacante con acceso de solo lectura a la base de datos podría recuperar los PIN de los médicos y falsificar sellados futuros suplantando su firma.
- **Recomendación:** Usar `django.contrib.auth.hashers.make_password`/`check_password` (o PBKDF2/Argon2 directamente) para `lab_validation_pin_hash`, igual que se hace para las contraseñas de usuario. Esto añade sal automática y un factor de costo configurable, eliminando el riesgo de tabla arcoíris y hará la comparación de tiempo constante de forma nativa.
- **Corrección aplicada:** nuevos PIN-LAB usan `make_password` y se verifican con `check_password`; hashes legacy SHA-256 se aceptan una sola vez y se actualizan automáticamente. El campo admite hashes de hasta 128 caracteres mediante migración `core.0103`.

## H-NUEVO-46 — `core/views/configuracion.py::configuracion_empresa`: sin chequeo de rol, cualquier usuario autenticado puede modificar datos fiscales de la empresa (RFC, razón social) — ALTO, CORREGIDO
- **Ubicación:** `core/views/configuracion.py:57-101`.
- **Descripción:** A diferencia de `api_cambiar_modo_ia` y `api_guardar_byok` en el mismo archivo (que correctamente usan `_puede_administrar_configuracion(request.user)` para exigir rol `ADMIN`/`DIRECTOR`/superuser), la vista `configuracion_empresa` solo tiene `@login_required`, sin ninguna verificación de rol. Permite a **cualquier usuario autenticado de la empresa** (recepción, cajero, laboratorista, etc.) enviar un POST con `EmpresaForm` que modifica `nombre`, `razon_social`, `rfc`, `direccion`, `telefono`, `email`, `logo`, `sitio_web` de la empresa completa.
- **Riesgo:** el campo `rfc`/`razon_social` alimenta directamente la facturación CFDI 4.0 (ver `contabilidad/validators_cfdi40.py` y `autofactura.py`). Un usuario de bajo privilegio (intencional o por cuenta comprometida) podría alterar el RFC/razón social de la empresa, causando que las facturas emitidas después del cambio sean fiscalmente inválidas o se emitan a nombre incorrecto, o cambiar el `logo`/`sitio_web` como vector de desfiguración (defacement) visible a pacientes en tickets/reportes.
- **Recomendación:** Aplicar `_puede_administrar_configuracion(request.user)` (o `@role_required('ADMIN','DIRECTOR')`) al inicio de `configuracion_empresa`, igual que en las otras dos vistas del mismo archivo.
- **Corrección aplicada:** la vista devuelve 403 salvo para `ADMIN`, `DIRECTOR` o superusuario.

## H-NUEVO-47 — `core/views/director.py::director_analizadores_probar_conexion`: SSRF ciego / escáner de puertos interno controlado por el usuario — MEDIO, CORREGIDO
- **Ubicación:** `core/views/director.py:417-439`.
- **Descripción:** El endpoint recibe `ip` y `puerto` arbitrarios del body JSON del cliente y el servidor ejecuta `socket.connect_ex((ip, puerto))` directamente, sin ninguna validación de que la IP pertenezca a una red permitida (lista blanca) o esté excluida de rangos internos/sensibles (p. ej. `169.254.169.254` metadata de nube, `127.0.0.1`, rangos RFC1918 internos de la infraestructura de PRISLAB). El endpoint está gateado por `_require_director`, que incluye roles `QUIMICO`/`LABORATORIO` además de administrativos.
- **Riesgo:** es un primitivo de **SSRF ciego** (blind SSRF): el atacante (usuario autenticado con rol de laboratorio) no puede leer contenido de la respuesta, pero sí puede usar el servidor como proxy para escanear puertos de la red interna/nube (host por host, puerto por puerto, observando `ok: true/false`), detectando servicios internos accesibles (bases de datos, paneles de administración, endpoints de metadata de la nube) que no deberían ser alcanzables desde fuera. Esto es reconocimiento de red (network reconnaissance) que facilita ataques posteriores si existe otra vulnerabilidad explotable en un servicio interno descubierto.
- **Recomendación:** Restringir `ip` a rangos de red de equipos de laboratorio conocidos/permitidos (allowlist de CIDR configurable por empresa), o al menos bloquear explícitamente rangos sensibles (loopback, link-local `169.254.0.0/16`, y rangos de la propia infraestructura cloud del proveedor). Considerar además `rate_limit` para prevenir escaneos masivos.
- **Corrección aplicada:** la vista exige una IP válida, bloquea loopback/link-local/multicast/unspecified y solo conecta contra un equipo activo de la empresa cuya IP y puerto coinciden con la solicitud.

## Nota de recurrencia — `core/views/motor_financiero.py::exportar_reporte_pdf` reutiliza el patrón de H-NUEVO-32 (inyección de markup ReportLab)
- **Ubicación:** `core/views/motor_financiero.py:185` (`Paragraph(f'REPORTE DE CAJA - {empresa.nombre}', title_style)`).
- **Descripción:** `empresa.nombre` se interpola sin `xml.sax.saxutils.escape()` dentro de un `Paragraph` de ReportLab (que interpreta un subconjunto de markup tipo HTML). Es el mismo patrón raíz documentado en `H-NUEVO-32`. La explotabilidad práctica depende de que un atacante pueda escribir `empresa.nombre` con contenido malicioso — lo cual **ahora es posible** vía `H-NUEVO-46` (`configuracion_empresa` sin chequeo de rol), convirtiendo esto en una cadena de explotación: cualquier usuario autenticado podría (1) cambiar `empresa.nombre` a través de `configuracion_empresa` con markup ReportLab malformado, y (2) provocar que `exportar_reporte_pdf` (u otros generadores de PDF que usen `empresa.nombre` sin escapar) fallen o rendericen contenido no intencionado al generar el reporte de caja.
- **Recomendación:** Aplicar `escape()` a `empresa.nombre` (y cualquier otro campo de `Empresa` insertado en `Paragraph`/`Table` de ReportLab) en todos los generadores de PDF, y priorizar la corrección de `H-NUEVO-46` para cerrar el vector de entrada.
- **Extensión detectada en `core/views/reportes_financieros.py`:** `exportar_excel_ingresos_egresos`, `exportar_excel_flujo_caja` y `exportar_excel_balance` escriben `empresa.nombre` directamente en celdas de Excel (`ws['A1'] = f"... — {empresa.nombre}"`) vía `openpyxl`, sin sanitizar. Si `empresa.nombre` comienza con `=`, `+`, `-` o `@` (posible tras explotar `H-NUEVO-46`), esto constituye **inyección de fórmulas CSV/Excel (CWE-1236)**: al abrir el archivo en Excel, la celda podría ejecutarse como fórmula (incluyendo fórmulas que invocan comandos externos en versiones antiguas de Excel/`DDE`). Recomendación: anteponer un apóstrofe (`'`) o sanear cualquier campo de texto controlado por el usuario antes de escribirlo en celdas de hoja de cálculo exportada.
- **Extensión detectada en `core/views/rh.py::generar_pdf_evaluacion_39a` (línea 292):** `story.append(Paragraph(evaluacion.notas_objetivas, styles['Normal']))` inserta directamente el texto libre `notas_objetivas` (capturado sin escapar en `crear_evaluacion_39a` desde `data.get('notas_objetivas', '')`) en un `Paragraph` de ReportLab. A diferencia de los otros dos casos, aquí el campo lo escribe directamente un usuario con rol `DIRECTOR`/`ADMIN`/`GERENTE`/`RH` (ya privilegiado), por lo que el impacto es menor (denegación de servicio al generar el PDF con markup malformado, o alteración visual del reporte), pero confirma que el patrón de falta de `escape()` en generadores de PDF con ReportLab es sistemático en el proyecto, no un caso aislado.

## H-NUEVO-48 — `core/views/excepciones_lab.py::registrar_merma`: cualquier usuario autenticado puede dar de baja inventario como "merma" sin aprobación de supervisor — MEDIO, CORREGIDO
- **Ubicación:** `core/views/excepciones_lab.py:327-425`.
- **Descripción:** A diferencia de `cancelar_orden` en el mismo archivo (que exige `@user_passes_test(es_superusuario)`), `registrar_merma` solo tiene `@login_required`. Permite a cualquier usuario autenticado de la empresa descontar permanentemente stock de `Producto`/`Lote` con solo un texto libre de `motivo` (`'Caducado'`, `'Roto'`, `'Consumo Interno'`, o cualquier string), sin exigir aprobación de un rol superior (Director/Gerente/Farmacia).
- **Riesgo:** es un control interno débil frente a fraude/merma no reportada: un empleado con acceso al sistema podría sustraer producto físico y "cubrir" la discrepancia de inventario registrándolo como merma, sin que el sistema exija ninguna autorización adicional o evidencia (a diferencia de `contabilidad_personal.py::marcar_orden_pagada`, que sí exige evidencia fotográfica + factura antes de aceptar un movimiento financiero). Queda registro de auditoría (`AuditLog`), pero solo de forma posterior/detectiva, no preventiva.
- **Recomendación:** Restringir `registrar_merma` a roles con responsabilidad de inventario (`FARMACIA`, `GERENTE`, `DIRECTOR`, `ADMIN`) vía `role_required`, y/o exigir un umbral de cantidad o valor por encima del cual se requiera aprobación adicional (similar al patrón de `contabilidad_personal.py`).
- **Corrección aplicada:** `registrar_merma` exige `role_required('FARMACIA', 'GERENTE', 'DIRECTOR', 'ADMIN')` antes de modificar existencias.

## H-NUEVO-49 — `core/views/pris_jarvis.py`: todas las llamadas a `sellar_transcripcion(ip=...)` fallan silenciosamente — sellado legal de audio (AES-256 + RFC 3161) roto en todos los endpoints de dictado por voz — ALTO, CORREGIDO
- **Ubicación:** `core/views/pris_jarvis.py` — `api_dictado_resultado` (línea ~123-129), `api_dictado_inventario` (línea ~192-198), `api_crear_archivo_raw` (línea ~414-420), `api_consulta_voz` (línea ~497-503), `api_coach_toma_muestra` (línea ~885-891).
- **Descripción:** Todas estas llamadas invocan `sellar_transcripcion(transcripcion=..., modulo=..., empresa=..., usuario=..., ip=_ip_cliente(request))`. Sin embargo, la firma real de `sellar_transcripcion` en `core/utils/pris_audio_vision.py:34-42` es `sellar_transcripcion(transcripcion, usuario, empresa, modulo='PRIS', duracion_segundos=None, url_actual='', datos_pantalla=None)` — **no acepta ningún parámetro `ip`**. Esto provoca un `TypeError: sellar_transcripcion() got an unexpected keyword argument 'ip'` en tiempo de ejecución cada vez que se llama.
- El error se traga silenciosamente porque cada llamada está envuelta en un `try/except Exception` que solo hace `logger.warning(...)` y continúa — el endpoint responde `200 OK` con éxito aparente al usuario, pero **el sellado legal nunca ocurre**.
- **Riesgo:** el módulo se documenta explícitamente como "Caja Negra" / evidencia forense con "AES-256 + timestamp RFC 3161" para dictados clínicos, de inventario, y consultas por voz — usado como respaldo legal (`docstring`: "Archivo RAW sellado con éxito. Hash inmutable registrado."). Al fallar silenciosamente en el 100% de las invocaciones, **no existe ningún registro forense real de estas transcripciones de voz**, comprometiendo cualquier defensa legal/regulatoria que dependa de esta bitácora (NOM-024, trazabilidad de dictado clínico). Es un incumplimiento silencioso de un control de cumplimiento crítico.
- **Recomendación:** Corregir la llamada eliminando el kwarg `ip=` inexistente (o añadir el parámetro `ip` a la firma de `sellar_transcripcion` si se desea capturar la IP como metadato forense adicional), y agregar una prueba de regresión que verifique que `VoiceAuditLog` efectivamente registra un `hash_sha256` no vacío tras cada llamada a estos endpoints.
- **Corrección aplicada:** se eliminó el kwarg inexistente en los cinco endpoints y se corrigió el consumo del resultado tipo diccionario, incluyendo `id`, hash y timestamp del sellado.

## H-NUEVO-50 — `core/views/catalogos.py::catalogo_convenios`: cualquier usuario autenticado puede crear un convenio con descuento arbitrario, sin rol ni aprobación — MEDIO, CORREGIDO
- **Ubicación:** `core/views/catalogos.py:86-141`.
- **Descripción:** A diferencia de `convenio_precios` en el mismo archivo (que exige `@role_required('DIRECTOR_QC', 'ADMIN')` para fijar precios especiales por analito) y de `cuentas_por_cobrar.py::api_crear_convenio` (que exige `role_required('DIRECTOR','ADMIN','GERENTE','FINANZAS')`), `catalogo_convenios` solo tiene `@login_required`. Permite a cualquier usuario autenticado crear un `Convenio` con un `descuento_porcentaje` arbitrario (parseado directamente de `request.POST.get('descuento_porcentaje')` sin límite superior) para la empresa.
- **Riesgo:** un convenio con descuento alto (incluso 100%) creado sin autorización podría luego usarse en el flujo de ventas/cotizaciones para aplicar descuentos no autorizados a órdenes de laboratorio, constituyendo un vector de fraude interno (dar servicios gratis o con descuento indebido a "clientes" ficticios vinculados a un convenio creado sin supervisión).
- **Recomendación:** Aplicar `role_required('DIRECTOR','ADMIN','GERENTE','FINANZAS')` (consistente con `cuentas_por_cobrar.py::api_crear_convenio`) a `catalogo_convenios`, y considerar un límite máximo de `descuento_porcentaje` validado en el modelo o la vista.
- **Corrección aplicada:** la vista exige `DIRECTOR`, `ADMIN` o `GERENTE`, requiere empresa asignada y rechaza descuentos fuera de 0-100 o valores no numéricos. Evidencia: `core.tests.test_dashboard_and_panic_security` pasa 13/13.

## H-NUEVO-51 — `core/agent/tools/registry.py::TOOLS_OPERATIVOS`: campo `"grupos": []` vacío en las 16 herramientas — capa de RBAC "adicional" es no-operativa (dead code), no un bypass real — BAJO/HIGIENE, CORREGIDO
- **Ubicación:** `core/agent/tools/registry.py:20-101` (los 16 diccionarios de `TOOLS_OPERATIVOS`); consumido en `core/views/pris_ia/_dispatcher.py:97-112`.
- **Descripción:** El dispatcher aplica esta lógica para herramientas operativas: `grupos_req = entry.get("grupos", []); if grupos_req and not user.is_superuser: [verificar RBAC]`. Como **cada una de las 16 entradas** en `TOOLS_OPERATIVOS` (incluyendo `gestionar_usuario`, cuya descripción dice explícitamente "solo Director/Admin") tiene `"grupos": []`, la condición `if grupos_req` es siempre `False` (lista vacía es falsy en Python), por lo que esta "capa adicional" de RBAC declarada en el comentario del dispatcher (`"Capa adicional para herramientas operativas que declaren grupos propios"`) **nunca se ejecuta para ninguna herramienta**.
- **Por qué NO es una vulnerabilidad explotable hoy:** Verificado que `_verificar_rbac()` (capa primaria, `core/views/pris_ia/_rbac.py` + `_constants.py::_TOOL_RBAC`) se ejecuta **antes** de llegar a esta rama del dispatcher para TODAS estas herramientas, y `_TOOL_RBAC` sí tiene grupos reales y correctos para cada una de ellas (p. ej. `gestionar_usuario: ["DIRECTOR","ADMIN","Administrador","GERENCIA"]`). Además, `tool_gestionar_usuario` en `operaciones.py` tiene una **tercera capa** de verificación explícita en código (`if not (user.is_superuser or rol in ('ADMIN','DIRECTOR'))`). Por lo tanto, el control de acceso real está intacto.
- **Riesgo residual:** el diseño depende ÚNICAMENTE de que `_TOOL_RBAC` en `_constants.py` se mantenga sincronizado y correcto para cada herramienta nueva que se agregue a `TOOLS_OPERATIVOS` — la "capa adicional" declarada en `registry.py` da una falsa sensación de defensa en profundidad que en realidad no existe. Si en el futuro alguien agrega una herramienta operativa nueva y omite (por error) registrarla en `_TOOL_RBAC`, `_verificar_rbac` la rechazaría por "no registrada" (fail-closed, correcto) — pero si alguien la registra con `None` (sin restricción) por error, no habría ninguna red de seguridad secundaria real que lo detenga, ya que `registry.py` nunca declara grupos.
- **Recomendación:** Poblar el campo `"grupos"` en `registry.py` con los mismos roles que `_TOOL_RBAC` (haciendo la capa "adicional" real), o eliminar el código muerto en el dispatcher que revisa `entry.get("grupos", [])` para evitar la falsa impresión de una segunda capa de defensa.
- **Corrección aplicada:** se eliminó el campo vacío y la segunda capa inerte del dispatcher. `_TOOL_RBAC` queda como fuente única efectiva, fail-closed y cubierta por prueba que impide registrar entradas con grupos ficticios.

## H-NUEVO-52 — `farmacia/views/inventario.py::carga_masiva_productos` + `core/services/inventario/catalogo_farmacia_service.py::CatalogoFarmaciaService`: (A) borrado masivo del catálogo sin rol, y (B) upsert cross-tenant por código de barras global — CRÍTICO, CORREGIDO
- **Ubicación:** `farmacia/views/inventario.py:375-444` (`carga_masiva_productos`); `core/services/inventario/catalogo_farmacia_service.py:80-151` (`_limpiar_catalogo_empresa`, `carga_masiva_productos`).
- **Problema A — sin control de rol para una operación destructiva:** La vista `carga_masiva_productos` solo tiene `@login_required`, sin ningún `role_required`. Acepta un flag `limpiar` (`request.POST.get('limpiar')`) que, si es verdadero, invoca `_limpiar_catalogo_empresa(empresa)`, la cual **borra permanentemente TODOS los `Lote` y TODOS los `Producto`** de la empresa (`Lote.objects.filter(producto__empresa=empresa)...delete()` y `Producto.objects.filter(empresa=empresa)...delete()`) antes de cargar el archivo subido. Cualquier usuario autenticado (recepción, cajero, etc.) puede destruir irreversiblemente todo el catálogo de farmacia de su empresa con un solo POST.
- **Problema B — upsert cruza tenants por `codigo_barras` global:** Dentro de `CatalogoFarmaciaService.carga_masiva_productos`, la búsqueda de productos existentes para decidir si se actualiza o se crea es: `existing_qs = Producto.objects.filter(codigo_barras__in=unique_cbs)` — **sin filtrar por `empresa`**. El comentario del código confirma la intención: *"Upsert masivo por codigo_barras (único global)"*. Esto significa que si dos empresas distintas (tenants) tienen productos con el mismo código de barras (algo **extremadamente probable** en un sistema de farmacias reales, ya que el mismo medicamento de fábrica trae el mismo GTIN/código de barras impreso), la carga masiva de la Empresa A **sobrescribirá silenciosamente** el nombre, precio de compra, precio público, stock, categoría, etc. del producto de la Empresa B, y hará `bulk_update` sobre sus lotes (`Lote.objects.filter(producto_id__in=prod_ids)` — de nuevo sin filtro de empresa al recolectar lotes existentes por `producto_id`, aunque `producto_id` en sí ya pertenece a la empresa incorrecta tras el upsert cruzado).
- **Riesgo:** Combinando ambos problemas: (1) fuga/corrupción de datos entre tenants — un tenant puede alterar precios, stock y catálogo de otro tenant sin ninguna interacción directa, solo subiendo un archivo con códigos de barras coincidentes; (2) destrucción total del catálogo de farmacia de la propia empresa por cualquier usuario sin rol elevado, sin ningún backup/confirmación adicional. Es una combinación de **corrupción de integridad cross-tenant** (violación del aislamiento multi-tenant, el pilar de seguridad más crítico de un SaaS) y **destrucción de datos sin autorización**.
- **Recomendación:**
  1. Agregar `@role_required('ADMIN','DIRECTOR','GERENTE','FARMACIA')` (o equivalente) a `carga_masiva_productos`, y exigir una confirmación explícita adicional (ej. re-ingreso de contraseña o PIN) cuando `limpiar=True`.
  2. Corregir `existing_qs` para filtrar `Producto.objects.filter(codigo_barras__in=unique_cbs, empresa=empresa)` — el upsert debe resolverse siempre dentro del tenant activo, incluso si `codigo_barras` no es único por empresa a nivel de esquema.
  3. Revisar si `Producto.codigo_barras` tiene una restricción `unique=True` a nivel de base de datos (global) — si es así, es un problema de modelado adicional que debería ser `unique_together` con `empresa`, no un `unique` global, ya que múltiples tenants comparten catálogos con los mismos productos comerciales.
- **Corrección aplicada:** la vista exige rol de farmacia/administración y confirmación literal `CONFIRMAR_LIMPIEZA` para borrar el catálogo. El servicio filtra por `empresa` tanto en el upsert como en la relectura posterior; los lotes se resuelven únicamente a partir de productos del tenant activo. Evidencia: `core.tests.test_dashboard_and_panic_security` pasa 16/16.

## H-NUEVO-53 — `farmacia/views/devoluciones.py::procesar_devolucion_venta`: endpoint alterno de devolución sin rol ni PIN, bypass del flujo canónico protegido — ALTO, CORREGIDO
- **Ubicación:** `farmacia/views/devoluciones.py:313-436` (`procesar_devolucion_venta`); comparar con `procesar_devolucion` (líneas 531-595) en el mismo archivo.
- **Descripción:** El archivo tiene **dos** endpoints que logran el mismo efecto (crear una devolución, reembolsar y reingresar/mermar stock), pero con protecciones radicalmente distintas:
  - `procesar_devolucion` (el flujo "canónico"): `@user_passes_test(_es_gerente_o_admin)` (exige rol FARMACIA/ADMIN/GERENTE/DIRECTOR) + `_validar_pin_devolucion` (PIN de 4 dígitos configurado por la empresa) + `venta = Venta.objects.select_for_update()` dentro de `transaction.atomic()` (previene condiciones de carrera en devoluciones concurrentes).
  - `procesar_devolucion_venta`: solo `@login_required`. **Sin `user_passes_test`, sin PIN, sin `select_for_update()`**. Crea `DevolucionVenta` + `SalesReturn`, reingresa stock vía `MovimientoInventarioService.reponer_stock_devolucion`, y registra auditoría — el mismo impacto financiero y de inventario que el flujo protegido, pero accesible a **cualquier usuario autenticado de la empresa**, sin autorización de un supervisor.
- **Riesgo:** un cajero (o cualquier usuario con sesión válida) puede procesar devoluciones/reembolsos y reingresos de stock sin la autorización PIN que el propio diseño del sistema exige para esta operación sensible en su flujo "oficial" — un vector directo de fraude interno (reembolsos ficticios, manipulación de inventario) que evade el control ya implementado para el caso equivalente.
- **Recomendación:** Aplicar `@user_passes_test(_es_gerente_o_admin)` + `_validar_pin_devolucion` a `procesar_devolucion_venta`, o eliminarlo/redirigirlo hacia `procesar_devolucion` si es una ruta legacy duplicada sin uso activo (verificar en `farmacia/urls.py` cuál de las dos rutas usa el frontend actual).
- **Corrección aplicada:** el endpoint alterno exige el mismo supervisor, PIN de cuatro dígitos y bloqueo `select_for_update()` dentro de la transacción antes de modificar devoluciones o stock.

## H-NUEVO-54 — `farmacia/views/compras.py::entrada_express`: incrementa stock sin el permiso Django exigido por el flujo de compra "oficial" del mismo archivo — MEDIO, CORREGIDO
- **Ubicación:** `farmacia/views/compras.py:309-407` (`entrada_express`); comparar con `registrar_compra` (líneas 20-156) en el mismo archivo, que sí exige `@permission_required('farmacia.add_movimientoinventario', raise_exception=True)`.
- **Descripción:** `entrada_express` solo tiene `@login_required`. Crea directamente un `MovimientoInventario` (`tipo_movimiento='ENTRADA_COMPRA'`) y aumenta el stock del lote correspondiente, el mismo efecto que `registrar_compra`, pero sin el permiso Django (`add_movimientoinventario`) que esa vista sí exige para la misma acción de negocio.
- **Riesgo:** cualquier usuario autenticado de la empresa (sin el permiso de compras) puede fabricar entradas de inventario ("Restock Rápido") declarando una cantidad, costo y lote arbitrarios, sin haber recibido mercancía real — un vector de fraude interno (inflar existencias para encubrir faltantes, o crear stock ficticio con costo bajo para manipular el CPP y luego venderlo con margen artificial).
- **Recomendación:** Aplicar el mismo `@permission_required('farmacia.add_movimientoinventario', raise_exception=True)` (o `role_required` equivalente) a `entrada_express`.
- **Corrección aplicada:** `entrada_express` usa ahora `@permission_required('farmacia.add_movimientoinventario', raise_exception=True)`.

## H-NUEVO-55 — `contabilidad/views.py::descargar_pdf`: inyección de markup ReportLab vía `razon_social`/RFC del cliente, alcanzable desde endpoint PÚBLICO sin login — ALTO, CORREGIDO
- **Ubicación:** `contabilidad/views.py:343-391` (`descargar_pdf`); origen del dato contaminado: `contabilidad/views_public.py:69-166` (`api_generar_autofactura`, endpoint público SIN `@login_required`); saneamiento insuficiente en `contabilidad/validators_cfdi40.py:53-69` (`clean_nombre_fiscal`).
- **Descripción:** `descargar_pdf` construye el PDF con `reportlab.platypus.Paragraph`, que interpreta un subconjunto de markup tipo HTML/XML (`<b>`, `<font>`, etc.). Dentro de la función, `empresa.nombre` y `empresa.rfc` SÍ se pasan por `html_escape()` (línea 347-348), pero **`factura.cliente.razon_social` y `factura.cliente.rfc` (líneas 354-355) se insertan directamente en `Paragraph(...)` sin ningún escape** — inconsistencia dentro de la misma función.
  - El campo `razon_social` de `ClienteFacturacion` se sanea en `ClienteFacturacion.clean()` (`contabilidad/models.py:94-95`) únicamente con `clean_nombre_fiscal()`, que solo normaliza espacios, pasa a mayúsculas y elimina sufijos societarios (`S.A. DE C.V.`, etc.) — **no elimina ni escapa `<`, `>`, `&`, `"`, `'`**.
  - Crucialmente, el valor llega desde `contabilidad/views_public.py::api_generar_autofactura`, un endpoint **público, sin `@login_required`**, accesible por cualquier persona que escanee el QR de un ticket (protegido solo por un token UUID de la orden, no por el contenido del payload). El atacante controla `razon_social` (y hasta cierto punto el RFC, aunque este sí tiene regex estricta) y puede insertar markup ReportLab arbitrario, ej. `razon_social: "<font size=999>X</font>"` o tags mal balanceados.
- **Riesgo:** un usuario externo no autenticado puede persistir un `ClienteFacturacion` con `razon_social` conteniendo markup ReportLab malicioso o mal formado. Cuando un usuario interno (DIRECTOR/ADMIN/GERENTE/FINANZAS) más tarde llame a `descargar_pdf` para esa factura, el parser de `Paragraph` puede: (a) lanzar una excepción no controlada (`ValueError`/`ParseError` de ReportLab) causando un DoS reproducible en la descarga de esa factura; o (b) alterar el layout/contenido visual del PDF fiscal entregado (ej. ocultar texto, insertar contenido falso) según lo que ReportLab permita interpretar en su micro-lenguaje de marcado.
- **Recomendación:**
  1. Aplicar `html_escape()` a `factura.cliente.razon_social` y `factura.cliente.rfc` en `descargar_pdf`, igual que ya se hace con `empresa.nombre`/`empresa.rfc` — consistencia dentro de la misma función.
  2. Extender `clean_nombre_fiscal()` (o agregar un sanitizador adicional a nivel de modelo, en `ClienteFacturacion.clean()`) para rechazar o escapar caracteres `<`, `>`, `&` en `razon_social`, ya que el campo se usa en múltiples superficies de renderizado (PDF, XML CFDI vía Facturama, HTML de templates).
  3. Auditar el resto de usos de `Paragraph(...)` en el proyecto (patrón recurrente ya visto en `core/views/motor_financiero.py`, `core/views/reportes_financieros.py`, `core/views/rh.py`) para confirmar que ningún campo de texto libre controlado por el usuario final llegue sin `html_escape()`.
- **Corrección aplicada:** `razon_social` y RFC del cliente se escapan antes de enviarse a `Paragraph`. La prueba de regresión confirma que etiquetas ReportLab introducidas por el cliente se convierten en texto literal. `manage.py check` y compilación de los archivos modificados pasan.

## H-NUEVO-56 — `inventario/views/lab.py::liberar_lote_qc`: sin control de rol pese a que el propio docstring exige "Químico Jefe / Director / Admin" — CRÍTICO, CORREGIDO
- **Ubicación:** `inventario/views/lab.py:419-450`.
- **Descripción:** El docstring de la función dice explícitamente: *"Liberación Técnica: cambia estado de CUARENTENA → ACTIVO. Solo Químico Jefe / Director / Admin."* Sin embargo, los únicos decoradores aplicados son `@_empresa_required` (login + empresa) y `@require_POST` — **no hay `role_required` ni verificación de rol alguna dentro del cuerpo de la función**.
- **Riesgo:** cualquier usuario autenticado de la empresa (recepcionista, auxiliar, etc.) puede liberar un lote de reactivo de laboratorio de `CUARENTENA` a `ACTIVO`, es decir, autorizar por sí mismo que ese reactivo se use en pruebas clínicas de pacientes sin que haya pasado por el control de calidad (QC) que el propio sistema fue diseñado para exigir. Tiene impacto directo en seguridad del paciente (resultados de laboratorio con reactivos no verificados) y en cumplimiento normativo (trazabilidad NOM/ISO 15189 del proceso de liberación QC).
- **Recomendación:** Agregar `@role_required('QUIMICO', 'DIRECTOR', 'ADMIN')` (o el nombre de rol equivalente usado en el resto del proyecto, ej. `'QUIMICO_JEFE'`) a `liberar_lote_qc`, replicando el patrón ya usado en `inventario/views/compra_ocr.py::_acceso` (`{"ADMIN", "DIRECTOR", "QUIMICO", "GERENTE"}`).

## H-NUEVO-57 — `inventario/views/traspasos.py::_ejecutar_recepcion`: lotes de reactivo de laboratorio recibidos por traspaso inter-sede se activan directamente, saltándose la cuarentena QC obligatoria del flujo de compra normal — CRÍTICO, CORREGIDO
- **Ubicación:** `inventario/views/traspasos.py:272-326` (`_ejecutar_recepcion`), específicamente líneas 296-302 (`'estado': 'ACTIVO'` para silo `LAB`); comparar con `inventario/views/compras.py:264-302` (`_recibir_mercancia`, silo LAB) y `inventario/views/lab.py:284-338` (`crear_lote`), que ambos fuerzan `'estado': 'CUARENTENA'` para todo lote de reactivo nuevo.
- **Descripción:** Cuando un lote de reactivo de laboratorio llega a la empresa por **compra** (`compras.py::_recibir_mercancia`) o registro manual (`lab.py::crear_lote`), el sistema lo crea en estado `CUARENTENA`, exigiendo pasar por `liberar_lote_qc` (liberación técnica QC) antes de poder consumirse en pruebas. Sin embargo, cuando un lote de reactivo llega a la empresa por **traspaso inter-sede** (`traspasos.py::_ejecutar_recepcion`), el código construye `lote_data` con `'estado': 'ACTIVO'` directamente (línea 301) — el lote queda disponible de inmediato para consumo analítico en pacientes, **sin pasar nunca por cuarentena ni por liberación QC**, incluso aunque ya hubiera sido liberado (o no) en la sede de origen.
- **Riesgo:** rompe la cadena de control de calidad de reactivos de laboratorio en un punto de entrada completo del inventario (traspasos entre sucursales/empresas), permitiendo que reactivos nunca verificados en la sede receptora se usen en estudios clínicos de pacientes. Es inconsistente con el propio diseño del sistema (que sí protege el flujo de compra) y agrava el impacto de H-NUEVO-56.
- **Recomendación:** Forzar `'estado': 'CUARENTENA'` también para lotes de silo `LAB` creados vía traspaso en `_ejecutar_recepcion`, exigiendo la misma liberación QC (`liberar_lote_qc`, ya corregido con rol) antes de permitir su consumo en `crear_salida_tecnica`/salidas analíticas del LIMS.

## H-NUEVO-58 — Autoaprobación sin control de rol en flujos de aprobación interna (`ValeRequisicion` y `OrdenDeCompra`) — ALTO, CORREGIDO
- **Ubicación:** `inventario/views/generales.py:284-355` (`detalle_vale`, rama `accion == 'aprobar'`, línea 297-302); `inventario/views/compras.py:161-205` (`detalle_oc`, rama `accion == 'aprobar'`, línea 173-178).
- **Descripción:** Ambos flujos modelan un estado explícito de espera de autorización gerencial: `ValeRequisicion.estado == 'PENDIENTE'` (esperando aprobación) y `OrdenDeCompra.estado == 'PENDIENTE_DIRECTOR'` (el propio nombre del estado indica que solo el Director debería poder avanzarlo). En ambos casos, la vista que procesa la acción `aprobar` solo exige `@_empresa_required` (login + empresa) — **no hay ninguna verificación de que `request.user` sea distinto de `solicitado_por`/`generada_por`, ni de que tenga un rol de autoridad (Director/Gerente/Admin)**.
- **Riesgo:** cualquier usuario autenticado de la empresa puede aprobar su propio vale de requisición o su propia orden de compra (autoaprobación), anulando el propósito del control de doble validación / segregación de funciones que el flujo de estados fue diseñado para imponer. Para `OrdenDeCompra` esto tiene impacto financiero directo (compras a proveedores sin autorización real).
- **Recomendación:** Agregar `@role_required('DIRECTOR', 'ADMIN', 'GERENTE')` (u homólogo) a las ramas de aprobación de ambas vistas, y adicionalmente comparar `request.user != vale.solicitado_por` / `request.user != oc.generada_por` para bloquear la autoaprobación incluso si el aprobador tiene el rol correcto pero es la misma persona que solicitó.

## H-NUEVO-59 — `marketing/views/*`: todas las operaciones de marketing, cupones, CRM/contactos y reactivación accesibles a cualquier usuario autenticado, sin control de rol — ALTO, CORREGIDO
- **Ubicación:** `marketing/views/campanas.py` (`lista_campanas`, `crear_campana`, `editar_campana`, `api_crear_campana`, `dashboard_campanas`); `marketing/views/cupones.py` (`api_generar_cupon`, `api_aplicar_cupon`, `generar_cupon`, `lista_cupones`); `marketing/views/contactos.py` (`lista_contactos`, `importar_contactos`); `marketing/views/dashboard.py` (`dashboard_marketing`, `entrenamiento_ia`, `dashboard_reactivacion_ia`); `marketing/views/reactivacion.py` (`api_detectar_pacientes_inactivos`).
- **Descripción:** Todo el módulo `marketing` aplica únicamente `@login_required` (o filtro manual `request.user.empresa`) y **no utiliza `@role_required` ni verificación de rol de autorización** en ninguna de sus vistas. Esto permite a cualquier usuario autenticado de la empresa —recepcionista, enfermería, técnico de laboratorio, almacenista, etc.—: crear/editar campañas de comunicación a pacientes; generar cupones de descuento (`generar_cupon`/`api_generar_cupon`) y aplicar cupones a órdenes de servicio (`api_aplicar_cupon`, con impacto financiero directo en el cobro de estudios); importar contactos/pacientes desde CSV (`importar_contactos`) creando registros en `core.Paciente`; y consultar listados de pacientes inactivos con datos personales (`api_detectar_pacientes_inactivos`: nombre, teléfono, fecha de nacimiento, enlace WhatsApp). Las URL del módulo están activas en `marketing/urls.py`.
- **Riesgo:** pérdida total de segregación de funciones entre roles clínicos/operativos y marketing/comercial. Cualquier empleado con credenciales puede manipular promociones, descuentos, base de datos de pacientes y campañas; además accede a PII y genera cupones con valor financiero sin aprobación de un rol autorizado. Es especialmente grave en `api_aplicar_cupon`, que modifica el descuento aplicado a una `OrdenDeServicio`.
- **Recomendación:** Aplicar `@role_required` a las vistas de gestión (`MARKETING`, `DIRECTOR`, `ADMIN`, `GERENTE` u homólogo). Para `api_aplicar_cupon` (usado desde PDV/farmacia) se requiere un análisis de permisos específico: mantenerlo accesible a `CAJERO`/`FARMACIA` pero nunca a roles sin relación con cobro o marketing. Las APIs de consulta de pacientes inactivos y listas de contactos deben restringirse a roles de marketing/dirección.

## H-NUEVO-60 — Código maestro de recuperación 2FA como bypass global y endpoint `api_verificar_codigo_2fa` sin autenticación ni rate limit — CRÍTICO, CORREGIDO
- **Ubicación:** `seguridad/views/api.py:32-59` (`api_verificar_codigo_2fa`); `seguridad/views/auth2fa.py:41-75` (`_verificar_codigo_2fa_usuario`); `seguridad/views/auth2fa.py:255-271` (`verificar_2fa_login`); `seguridad/urls.py:30`.
- **Descripción:** `api_verificar_codigo_2fa` carece de `@login_required` y no aplica rate limiting. Procesa `request.user`; si la petición no está autenticada, `request.user` es `AnonymousUser` y las queries de TOTP/backup no devuelven dispositivos, **pero el flujo continúa hasta comparar el código contra `settings.PRISLAB_MASTER_RECOVERY_CODE`**. Si ese secreto global está configurado, el endpoint devuelve `{'valido': True, 'tipo': 'master_recovery'}` para cualquier usuario (incluido el anónimo). El mismo `_verificar_codigo_2fa_usuario`/`verificar_2fa_login` aceptan `PRISLAB_MASTER_RECOVERY_CODE` como bypass universal del 2FA, permitiendo iniciar sesión como cualquier usuario (junto con la contraseña).
- **Riesgo:** un único secreto en `settings` compromete la autenticación de dos factores de **todos** los usuarios del sistema. Un endpoint sin login actúa como **oráculo público** para validar/verificar el código maestro (sin siquiera autenticar), facilitando la detección del secreto mediante fuerza bruta o exfiltración. Bypass total del 2FA.
- **Recomendación:** Eliminar el `PRISLAB_MASTER_RECOVERY_CODE` global o reemplazarlo por un flujo de recuperación auditado (códigos de respaldo individuales, tokens de un solo uso firmados, o recuperación controlada por correo/SMS). Añadir `@login_required` y rate-limit estricto a `api_verificar_codigo_2fa`; si el endpoint es parte del login, integrarlo en el flujo de autenticación con límite por usuario/IP.

## H-NUEVO-61 — Botón de pánico (`panic_button`) activable por GET sin autenticación, POST ni control de rol — ALTO, CORREGIDO
- **Ubicación:** `seguridad/views/panico.py:33-109`; `seguridad/urls.py:32`.
- **Descripción:** `panic_button` no tiene `@login_required`, `@require_http_methods(["POST"])` ni `role_required`. Si el usuario no está autenticado, `get_empresa_usuario(request.user)` devuelve `None` y responde `403`; pero para un usuario autenticado, **cualquier GET a `/seguridad/api/panic/` crea una `AlertaPanico` y dispara notificaciones por Telegram/push**. Las peticiones GET no requieren token CSRF, por lo que un sitio malicioso puede activar el botón de pánico en segundo plano (imagen, iframe, redirección) mientras el usuario está logueado en PRISLAB.
- **Riesgo:** spam de alertas de pánico, notificaciones falsas masivas al director/seguridad, consumo de presupuesto de notificaciones y desensibilización ante alertas reales. También expone la IP del usuario en la `ubicación`.
- **Recomendación:** Decorar `panic_button` con `@login_required` y `@require_http_methods(["POST"])`. Añadir rate-limit por usuario e IP más estricto (el cache de 30s limita solo por canal de notificación, no por petición HTTP). Si el botón de pánico es para todo personal, mantenerlo accesible a cualquier usuario autenticado de la empresa, pero nunca vía GET.

## H-NUEVO-62 — Regeneración y lectura de códigos de respaldo 2FA sin reautenticación, con almacenamiento en texto plano — ALTO, ABIERTO
- **Ubicación:** `seguridad/views/auth2fa.py:210-240` (`mostrar_codigos_backup`, `regenerar_codigos_backup`); `seguridad/models.py:329-392` (`CodigoBackup2FA`); `seguridad/admin.py:17-27` (`CodigoBackup2FAAdmin`).
- **Descripción:** `regenerar_codigos_backup` solo requiere `@login_required` y `@require_POST` pero **no pide la contraseña actual ni step-up**. Invalida los códigos anteriores, genera 10 nuevos y redirige a `mostrar_codigos_backup`, donde se muestran en claro. Un atacante con una sesión robada (XSS, cookie, token) puede regenerar y leer todos los códigos de respaldo, obteniendo un mecanismo de acceso persistente incluso si la contraseña cambia o el TOTP se desactiva. Además, el modelo `CodigoBackup2FA` almacena `codigo` en **texto plano** junto al `codigo_hash`, y `CodigoBackup2FAAdmin` incluye `codigo` en `readonly_fields`, permitiendo a un administrador con acceso a Django Admin ver los códigos de respaldo completos de cualquier usuario.
- **Riesgo:** secuestro persistente de cuentas vía códigos de respaldo, violación del principio de mínimo conocimiento del segundo factor, y exposición a insiders con acceso admin.
- **Recomendación:** Requerir reautenticación con contraseña (o un nuevo código TOTP) antes de `regenerar_codigos_backup` y `mostrar_codigos_backup`. Almacenar únicamente el hash SHA256; mostrar los códigos en claro una sola vez en el momento de la generación y nunca en el admin (usar un resumen parcial no recuperable o excluir el campo).

## H-NUEVO-63 — `mantenimiento/views/*`: operaciones críticas de CMMS accesibles a cualquier usuario autenticado, sin `role_required` y con autoautorización en tickets — ALTO, PARCIALMENTE CORREGIDO
- **Ubicación:** `mantenimiento/views/director.py` (`wizard_dashboard`, `wizard_protocolo`, `wizard_arbol`, `lista_expedientes`, `crear_expediente`, `detalle_expediente`); `mantenimiento/views/operativo.py` (`lista_equipos_operativo`, `ejecutar_checklist`, `diagnostico_inicio`, `diagnostico_nodo`, `lista_tickets`, `crear_ticket`, `detalle_ticket`); `mantenimiento/views/metrologia.py` (`lista_certificados`, `subir_certificado`, `eliminar_certificado`, `lista_sensores`, `crear_sensor`, `dashboard_sensores`, `registrar_lectura_manual`); `mantenimiento/views/api.py` (`api_stock_lote_para_refaccion`, `api_checklist_bloqueado`); `mantenimiento/views/tco.py` (`dashboard_tco`); `mantenimiento/urls.py`.
- **Descripción:** El módulo CMMS utiliza `_req_empresa` (login + empresa) en la mayoría de las vistas pero **no aplica `@role_required`**. Cualquier usuario autenticado puede: crear/editar protocolos de arranque/limpieza/calibración y sus pasos críticos; crear/editar árboles de diagnóstico y nodos; registrar, modificar y eliminar expedientes de equipo; subir/eliminar certificados de metrología; crear sensores IoT y registrar lecturas manuales; ejecutar y *bypass* checklists; crear, cerrar y escalar tickets; consumir refacciones de inventario (`registrar_consumo_refaccion`); consultar stock de lotes. Además, `wizard_dashboard`, `dashboard_tco` y `lista_equipos_operativo` carecen incluso de `_req_empresa` y reciben `empresa` como parámetro, mientras que sus URL no lo pasan (vistas potencialmente inalcanzables / control gap). Los campos `nivel_requerido` y `aplica_a_perfil` del modelo (`ProtocoloEquipo`, `NodoDiagnostico`, `ProcedimientoReparacion`) **nunca se validan** en las vistas. En `detalle_ticket`, la acción `escalar` a `PROVEEDOR` permite autoasignarse como `autorizado_por_director` sin verificar rol. `api_checklist_bloqueado` no exige siquiera `@login_required`.
- **Riesgo:** pérdida total de segregación de funciones en un módulo regulado (ISO 15189 / COFEPRIS) que impacta calidad, metrología, trazabilidad y seguridad del paciente. Un empleado con credenciales básicas puede falsificar registros de calibración, manipular checklists, consumir inventario de mantenimiento y autoautorizar escalamientos a proveedor.
- **Recomendación:** Aplicar `@role_required` a todas las vistas de configuración/director (`DIRECTOR`, `ADMIN`, `QUIMICO_JEFE`, `TECNICO` según el recurso). En `ejecutar_checklist`, validar `request.user.rol` contra `protocolo.nivel_requerido` y `aplica_a_perfil`. En `detalle_ticket`, restringir cierre/escalamiento a roles `DIRECTOR`, `ADMIN` o `QUIMICO_JEFE` y evitar la autoasignación de `autorizado_por_director`. Restaurar `_req_empresa` en `wizard_dashboard`, `dashboard_tco` y `lista_equipos_operativo`. Validar tipos de archivo en subidas (`foto_equipo`, `manual_pdf`, `paso_imagen`, `archivo_pdf`).

## H-NUEVO-64 — Endpoint IoT `api_iot_lectura` autentica con el código del sensor (identificador público), `csrf_exempt` y sin rate limit — ALTO, CORREGIDO
- **Ubicación:** `mantenimiento/views/metrologia.py:251-301` (`api_iot_lectura`); `mantenimiento/urls.py:66`.
- **Descripción:** El endpoint es `@csrf_exempt`, no requiere login y recibe `X-SENSOR-TOKEN`. El mecanismo de autenticación es comparar el header directamente con `SensorIoT.codigo` (un identificador legible de máx. 50 caracteres, no un secreto criptográfico). Si un atacante conoce o adivina un `codigo` (p.ej. secuencial, etiqueta física, expuesto en QR/equipo), puede enviar lecturas falsas de temperatura/humedad. El endpoint crea `LecturaSensorIoT`; el signal `post_save` (`mantenimiento/signals.py:48`) evalúa el rango y, si la lectura está fuera de rango, crea un `TicketMantenimientoCMMS` de prioridad CRITICA y una `NotificacionDiscrepancia` al Director.
- **Riesgo:** alertas falsas masivas, tickets críticos de mantenimiento espurios, notificaciones a dirección y desensibilización ante alertas reales. En escenarios extremos se puede forzar la creación de tickets que indiquen falla de refrigeradores/congeladores de reactivos o muestras, causando descarte o paro de procesos. Fácil enumeración de códigos por fuerza bruta si no hay rate limit.
- **Recomendación:** Reemplazar `codigo` como credencial por un token secreto fuerte por sensor (`secrets.token_urlsafe(32)`) y usar `secrets.compare_digest`. Añadir rate limiting por token/IP. Considerar mTLS o firma del payload para sensores físicos. No usar un identificador legible como única credencial.

## H-NUEVO-65 — `bypass_checklist` permite omisión de checklists con PIN compartido global y sin verificación de rol del supervisor — ALTO/CRÍTICO, CORREGIDO
- **Ubicación:** `mantenimiento/views/operativo.py:142-211` (`bypass_checklist`); `mantenimiento/urls.py:30-31`.
- **Descripción:** Para autorizar el bypass de un checklist, la vista exige `supervisor_username`, `supervisor_pin` y `motivo`. El PIN se compara contra `settings.LAB_VALIDATION_PIN` (un único PIN global compartido) o contra `supervisor.check_password(supervisor_pin)`. **No verifica que el supervisor tenga un rol de autoridad** (`DIRECTOR`, `ADMIN`, `QUIMICO_JEFE`) ni que su nivel sea superior al del ejecutante. El modelo `BypassChecklistAutorizacion` documenta que "El nivel del autorizante debe ser mayor al del ejecutante", pero el código no lo implementa. Cualquier usuario que conozca `LAB_VALIDATION_PIN` o la contraseña de otro usuario puede autorizar la omisión de cualquier checklist, incluidos los que bloquean la Worklist.
- **Riesgo:** omisión de pasos críticos de control de calidad/seguridad sin autorización real, permitiendo que personal no calificado pase por alto checks de arranque, limpieza o calibración con impacto directo en seguridad del paciente y cumplimiento normativo.
- **Recomendación:** Verificar el rol del supervisor contra `NIVEL_AUTORIZACION_CHOICES` de forma jerárquica y exigir que sea estrictamente mayor al nivel requerido del protocolo y al rol del ejecutante. Eliminar o proteger el `LAB_VALIDATION_PIN` global; si se conserva, limitarlo a un uso de emergencia con doble autorización y auditoría. Registrar el bypass como acción sensible con `LogAccionSensible`.

## H-NUEVO-66 — `bienestar` almacena el diario emocional en texto plano, sin campo `empresa` ni cifrado real, y expone recursos sin aislamiento de tenant — MEDIO, ABIERTO
- **Ubicación:** `bienestar/models.py:37-40` (`DiarioEmocional.contenido_privado`); `bienestar/admin.py:7-74` (`DiarioEmocionalAdmin`); `bienestar/views.py:446-469` (`recursos_bienestar`); `bienestar/urls.py`.
- **Descripción:** El campo `contenido_privado` de `DiarioEmocional` es un `TextField` plano. Aunque el admin lo oculta con la etiqueta "simula cifrado visual" y restringe add/change/delete a `is_superuser`, **no hay cifrado real en reposo ni en tránsito** para las entradas emocionales de los usuarios. El modelo tampoco tiene campo `empresa`, por lo que `TenantScopedAdmin` no puede filtrar correctamente por tenant en el admin (riesgo de fuga cross-tenant si un staff de una empresa ve el listado, ya que `has_view_permission` no está restringido y el scoping depende de un campo inexistente). Además, `RecursoCrecimiento` no tiene `empresa` y se muestra global a todos los tenants (`filter(activo=True)`), lo que puede filtrar recursos creados para otra empresa. `DiarioEmocionalAdmin.contenido_privado_display` depende de `self._request`, atributo que Django admin no establece por defecto, por lo que el contenido nunca se muestra (fallo funcional, no de seguridad).
- **Riesgo:** exposición de datos sensibles de salud mental/emocional si la base de datos es comprometida (backup, acceso no autorizado, insider) o si el admin no scopa correctamente por tenant. Incumplimiento del principio de privacidad por diseño y de la NOM-035 (datos de bienestar deben estar aislados y protegidos).
- **Recomendación:** Cifrar `contenido_privado` con cifrado autenticado (p. ej. `django-cryptography` o cifrado de campo) o, como mínimo, el modelo debe tener campo `empresa` y un admin con `get_queryset` filtrado por `usuario__empresa`. Añadir `empresa` a `RecursoCrecimiento` o filtrar recursos por `empresa` (o un flag de global). Revisar `DiarioEmocionalAdmin.contenido_privado_display` para usar el `request` del changelist adecuadamente.

## Código muerto / higiene (sin riesgo de seguridad) — CORREGIDO
- `core/services/ai_medico_backup.py` — eliminado tras confirmar que no tenía imports activos.
- `marketing/views_legacy.py` — eliminado tras confirmar que `marketing/urls.py` usa `marketing.views`.

## H-NUEVO-67 — `consultorio` permite a cualquier usuario autenticado crear consultas, recetas, certificados médicos y órdenes de laboratorio sin verificar rol médico — CRÍTICO, CORREGIDO
- **Ubicación:** `consultorio/views/api_consulta.py:45-114` (`api_crear_consulta_directa`), `:120-218` (`api_crear_paciente_y_consulta`), `:428-531` (`api_generar_receta_inmediata`), `:537-632` (`api_generar_certificado_inmediato`), `:639-722` (`api_generar_orden_laboratorio_inmediata`); `consultorio/views/clinico.py:109-161` (`consulta_sin_cita`), `:662-688` (`nueva_consulta_simplificada`), `:690-865` (`nueva_consulta_con_paciente`); `consultorio/views/certificados.py:27-147` (`generar_certificado`); `consultorio/urls.py`.
- **Descripción:** Los endpoints y vistas anteriores están decorados solo con `@login_required` y filtran por `empresa`, pero no aplican `@role_required('MEDICO', 'ADMIN')` ni verifican que el usuario sea el médico asignado o un profesional de la salud. `nueva_consulta_con_paciente` auto-crea una `CitaMedica`, `SignosVitales`, `ConsultaMedica`, `Receta`, `CertificadoMedico` y `OrdenDeServicio` en una sola transacción. `generar_certificado` y `api_generar_certificado_inmediato` permiten seleccionar el tipo `DEFUNCION`, `NACIMIENTO`, `INCAPACIDAD`, etc., sin control adicional. Un usuario de recepción, enfermería o cualquier cuenta comprometida puede emiter documentos clínicos con validez legal/fiscal.
- **Riesgo:** fraude médico, falsificación de recetas, certificados de defunción/incapacidad y órdenes de laboratorio no autorizadas; responsabilidad legal y regulatoria (NOM-004, COFEPRIS, SAT); escalada de privilegios dentro del tenant.
- **Recomendación:** Aplicar `@role_required` o verificación de rol médico (`MEDICO`, `ADMIN`, `DIRECTOR`) en todas las vistas/APIs de creación de consultas y documentos clínicos. Verificar que el usuario es el médico asignado a la cita o tiene permiso explícito. No permitir que `request.user` auto-firme documentos sin un `Medico` verificado.
- **Corrección aplicada:** las vistas y APIs de escritura clínica exigen `MEDICO`, `ADMIN` o `DIRECTOR`; la resolución de médico ya no crea cédulas sintéticas sin cédula interna registrada.

## H-NUEVO-68 — `consultorio` permite a cualquier usuario autenticado registrar cobros, marcar consultas como pagadas y liquidar vales sin control de rol ni autorización — ALTO, CORREGIDO
- **Ubicación:** `consultorio/views/cobros.py:31-118` (`cobro_consulta`), `:120-223` (`api_registrar_cobro`), `:225-276` (`api_liquidar_vale`), `:278-324` (`reporte_liquidacion`); `consultorio/models/cobros.py:95-249` (`CobroConsulta`), `:251-332` (`ValeLiquidacion`).
- **Descripción:** Todas las vistas de cobros usan solo `@login_required`. `api_registrar_cobro` recibe `monto_total`, `monto_efectivo/tarjeta/transferencia`, `concepto`, `cobrado_por` y `referencia` sin validar que el usuario tenga rol de caja/recepción/medico. Marca la consulta como `pagada=True`, fija `precio_consulta` y crea `ValeLiquidacion` si `cobrado_por='RECEPCION'`. `api_liquidar_vale` acepta un `monto` arbitrario y liquida el vale del médico solicitado sin verificar que el usuario tenga permiso de liquidación o sea el acreedor.
- **Riesgo:** fraude financiero, cobros falsos, alteración del estado de pago de consultas, liquidaciones indebidas, desbalance de caja y riesgo de lavado de dinero/control interno.
- **Recomendación:** Restringir a roles `CAJA`, `RECEPCION`, `MEDICO` y/o `ADMIN` según `ConfiguracionMedico.modo_cobro`. Validar que el cobrador tenga permiso para cobrar en nombre del médico. Auditizar cambios de estado de pago y liquidaciones con `LogAccionSensible`/`AuditLog`.
- **Corrección aplicada:** cobros, liquidación de vales y reportes requieren rol operativo/financiero (`MEDICO`, `RECEPCION`, `ADMIN`, `GERENTE` o `DIRECTOR`).

## H-NUEVO-69 — `_resolver_medico_usuario` auto-crea registros `Medico` con cédulas profesionales sintéticas, permitiendo que usuarios no médicos firmen documentos clínicos — ALTO, CORREGIDO
- **Ubicación:** `consultorio/views/_helpers.py:19-68` (`_resolver_medico_usuario`, especialmente `:59-68`); `consultorio/views/api_consulta.py:70-71,164-165,451-452,561-562,662-663`; `consultorio/views/certificados.py:103`; `consultorio/views/clinico.py:709-743`.
- **Descripción:** El helper resuelve un `core.Medico` para el `request.user`. Si no lo encuentra y `autocrear=True`, crea un registro con `cedula_profesional = cedula_interna or f'USR-{request.user.id}'` y `especialidad = 'Médico General'`. No valida que el usuario tenga una cédula profesional real registrada en el sistema, que pertenezca a la empresa o que tenga rol médico. Este `Medico` sintético se utiliza para firmar recetas, certificados, órdenes de laboratorio y PDFs.
- **Riesgo:** suplantación de identidad médica, documentos clínicos firmados por personas no autorizadas, invalidez legal de recetas/certificados, responsabilidad médica mal atribuida.
- **Recomendación:** Eliminar la opción `autocrear` en flujos clínicos. Exigir un `Medico` pre-existente, activo y vinculado a `request.user` (o a su `FirmaDigital`) con `cedula_profesional` verificada y `empresa` correcta. La creación de médicos debe ser un proceso administrativo con validación de cédula.
- **Corrección aplicada:** se eliminó el fallback `USR-{user.id}`; sin cédula interna y perfil existente el helper no crea identidad clínica sintética.

## H-NUEVO-70 — `consultorio` expone historial clínico, signos vitales, certificados y reportes de productividad a cualquier usuario autenticado del tenant — ALTO, CORREGIDO
- **Ubicación:** `consultorio/views/historial.py:28-70` (`historial_clinico_paciente`), `:137-165` (`ver_consulta_detalle`); `consultorio/views/reportes.py:283-300` (`historial_signos_vitales`), `:510-566` (`encuestas_satisfaccion`), `:612-710` (`reportes_productividad`); `consultorio/views/api_consulta.py:898-930` (`api_signos_vitales_tendencia`).
- **Descripción:** Estas vistas/APIs solo están protegidas por `@login_required` y filtran por `empresa`. Cualquier usuario (incluyendo recepción, limpieza, marketing, staff sin rol clínico) puede ver el historial completo de un paciente (`consultas`, `signos_vitales`, `certificados`, `historia_clinica`), el detalle SOAP de una consulta, las encuestas NPS con comentarios y los reportes financieros/productividad del consultorio.
- **Riesgo:** violación de privacidad de datos de salud (PHI/ePHI), incumplimiento de NOM-004, LFPDPPP y HIPAA; exposición de comentarios sensibles de pacientes y datos financieros internos.
- **Recomendación:** Restringir el acceso al historial y detalle de consultas a `MEDICO`, `ENFERMERIA` y `ADMIN`, y además scopar por relación médico-paciente cuando aplique. Los reportes de productividad deben requerir `DIRECTOR`/`ADMIN`/`FINANZAS`. Registrar acceso forense.
- **Corrección aplicada:** historial, dashboard y detalle de consulta requieren roles clínicos o administrativos autorizados; la prueba de regresión bloquea a `CAJERO`.

## H-NUEVO-71 — `consultorio` expone contexto de incidencias Sentinel, instrucciones SSH, traceback y código propuesto a cualquier usuario autenticado — ALTO, CORREGIDO
- **Ubicación:** `consultorio/views/sentinel.py:226-298` (`api_sentinel_exportar_cursor`), `:301-324` (`api_sentinel_ssh`); `consultorio/sentinel_service.py:410-530` (`generar_prompt_cursor_reparacion`, `generar_resumen_ssh_rapido`).
- **Descripción:** A diferencia de `sentinel_dashboard`, `api_sentinel_exportar_cursor` y `api_sentinel_ssh` solo requieren `@login_required`. Retornan el `traceback_completo`, `codigo_original`, `codigo_propuesto`, `instrucciones_ssh`, `archivo_principal`, `ruta_contenedor /app/`, comandos SSH (`cd /app`, `nano`, `kill -HUP 1`) y prompts para Cursor. Aunque no ejecutan comandos, filtran correctamente por `empresa`, pero cualquier usuario autenticado del tenant puede pedir el contexto técnico de cualquier incidencia.
- **Riesgo:** divulgación de información sensible del sistema (rutas, nombres de funciones, estructura de código, detalles de errores) que facilita reconocimiento y explotación posterior; filtración de instrucciones de mantenimiento interno.
- **Recomendación:** Aplicar el mismo control de rol que `sentinel_dashboard` (`is_superuser` o grupos `Administrador`/`Director`/`Gerente` o `rol` `ADMIN`/`DIRECTOR`/`GERENTE`). No exponer `traceback_completo` ni códigos propuestos a usuarios sin privilegio de mantenimiento.
- **Corrección aplicada:** dashboard, detalle, guía SSH y APIs de exportación/SSH requieren `ADMIN`, `GERENTE` o `DIRECTOR`.

## H-NUEVO-72 — Generación de PDFs de recetas y expediente forense en `consultorio` sin verificación de rol médico/permiso más allá del login — ALTO, CORREGIDO
- **Ubicación:** `consultorio/views/pdf_views.py:50-289` (`imprimir_receta_paciente`), `:296-550` (`imprimir_expediente_forense`); `consultorio/views/pdf_views_prislab.py:18-62` (`imprimir_receta_profesional`), `:64-114` (`api_generar_receta_pdf`); `consultorio/urls.py`.
- **Descripción:** `imprimir_receta_paciente`, `imprimir_receta_profesional` y `api_generar_receta_pdf` solo usan `@login_required` y `empresa`. No verifican que el solicitante sea el médico tratante, tenga permiso `ver_historia_completa` o rol clínico. `imprimir_expediente_forense` sí exige `@permission_required('core.ver_historia_completa')`, pero las recetas no. Combinado con H-NUEVO-67, un atacante puede crear una consulta/receta falsa e inmediatamente imprimirla.
- **Riesgo:** generación y descarga de recetas y expedientes por personal no autorizado; falsificación de documentos médicos; pérdida de control sobre documentos firmados digitalmente.
- **Recomendación:** Exigir `MEDICO`/`ADMIN`/`ENFERMERIA` y verificar que la consulta pertenezca al usuario o que tenga permiso explícito. Aplicar `@permission_required` consistente para todas las vistas PDF clínicos. Registrar impresión/descarga en auditoría forense.
- **Corrección aplicada:** las tres rutas de receta PDF requieren `MEDICO`, `ADMIN` o `DIRECTOR`; el expediente forense mantiene su permiso específico.

## H-NUEVO-73 — APIs de IA/transcripción en `consultorio` permiten sobrescribir la transcripción de cualquier consulta y envían datos a Gemini sin rate limiting ni validación del output — MEDIO/ALTO, ABIERTO
- **Ubicación:** `consultorio/views/api_consulta.py:268-422` (`api_analizar_transcripcion`, especialmente `:395-405`), `:847-891` (`api_buscar_vademecum`); `consultorio/api_views.py:42-113` (`procesar_audio_consulta`), `:116-227` (`procesar_audio_laboratorio`), `:229-268` (`verificar_api_gemini`); `consultorio/sentinel_service.py:105-254` (`analizar_error_con_ia`).
- **Descripción:** `api_analizar_transcripcion` recibe `cita_id` y `transcripcion_completa`, llama a Gemini y luego guarda el resultado en `ConsultaMedica.transcripcion_completa` si se proporciona `cita_id`. Solo filtra la cita por `empresa`, no por médico asignado, por lo que cualquier usuario puede sobrescribir la transcripción de cualquier consulta del tenant. `procesar_audio_consulta` recibe archivos de audio y los envía a `procesar_consulta_medica` sin rate limit ni validación del contenido. La respuesta de Gemini se pasa a `json.loads` directamente sin esquema ni sanitización.
- **Riesgo:** manipulación de historial clínico (transcripción), inyección de contenido en registros médicos, consumo abusivo de API de Gemini/costos elevados, posible exfiltración indirecta de datos si el prompt incluye contexto sensible, alucinaciones médicas persistidas en el expediente.
- **Recomendación:** Verificar que el usuario sea el médico de la cita. Añadir rate limiting por usuario/empresa. Validar el JSON devuelto contra esquema estricto y sanitizar antes de guardar. Loggear interacciones con IA. Considerar no persistir la transcripción generada por IA como fuente única de verdad.

## H-NUEVO-74 — Triage, recepción, agenda y videollamada en `consultorio` carecen de controles de rol adecuados — MEDIO, CORREGIDO
- **Ubicación:** `consultorio/views/recepcion.py:30-62` (`tablero_recepcion`), `:64-78` (`check_in_cita`), `:81-220` (`agendar_cita`); `consultorio/views/triage.py:38-61` (`lista_triage`), `:63-154` (`captura_signos_vitales`); `consultorio/views/videollamada.py:29-119` (`videollamada_segura`), `:122-162` (`api_crear_sala_videollamada`); `consultorio/views/reportes.py:307-355` (`agenda_medico`).
- **Descripción:** Triage y recepción solo usan `@login_required`; no requieren `ENFERMERIA`, `RECEPCION` ni `MEDICO`. `check_in_cita` permite cambiar el estado de cualquier cita del día a `EN_SALA`. `agendar_cita` puede asignar cualquier `medico_id` y, si el usuario no es médico, `_resolver_medico_usuario(..., autocrear=True)` crea un `Medico` para él. `videollamada_segura` lista todas las citas del día y `api_crear_sala_videollamada` genera un token firmado para cualquier paciente/cita del tenant sin verificar que el usuario sea el médico asignado.
- **Riesgo:** manipulación de flujo de citas, triaje por personal no capacitado, salas de videollamada accesibles por usuarios no autorizados, agendamiento con médicos incorrectos.
- **Recomendación:** Aplicar `@role_required('RECEPCION', 'MEDICO', 'ADMIN')` a recepción, `ENFERMERIA` a triaje, y `MEDICO` a videollamada/creación de salas. Validar `medico_id` y evitar auto-creación de médicos en agendamiento.

## H-NUEVO-75 — `ArchivoAdjuntoConsulta` permite a cualquier usuario autenticado subir archivos a expedientes de pacientes sin control de rol — MEDIO, CORREGIDO
- **Ubicación:** `consultorio/views/api_consulta.py:762-819` (`api_subir_archivo`); `consultorio/models/medico.py:270-358` (`ArchivoAdjuntoConsulta`); `consultorio/admin.py:61-65`.
- **Descripción:** `api_subir_archivo` solo requiere `@login_required` y `empresa`. Cualquier usuario puede subir un archivo a cualquier `Paciente` (y vincularlo a una `ConsultaMedica` si proporciona `consulta_id`). El `tipo` se toma directamente de `request.POST` sin validar contra `TIPO_CHOICES`. Aunque el campo `archivo` usa `validate_document_upload`, el alcance del validador no se verificó en esta auditoría y no compensa la falta de RBAC.
- **Riesgo:** contaminación de expedientes con archivos no autorizados, posible upload de malware si el validador de archivos es débil, suplantación de documentos clínicos (radiografías, consentimientos).
- **Recomendación:** Restringir la carga a `MEDICO`, `ENFERMERIA` y `ADMIN`. Validar `tipo` contra `ArchivoAdjuntoConsulta.TIPO_CHOICES`. Verificar que `consulta_id` corresponda al `paciente_id` y al usuario. Auditar subidas y eliminaciones.

## H-NUEVO-76 — `consultorio` mantiene modelos legacy (`ConsultaMedica` en `legacy.py`, `Somatometria` sin `empresa`) que confunden el modelo de datos activo y rompen el aislamiento — BAJO/MEDIO, ABIERTO
- **Ubicación:** `consultorio/models/legacy.py:1-68` (modelo `ConsultaMedica` obsoleto); `consultorio/models/clinico.py:22-40` (`Somatometria` sin `empresa` y FK a `legacy.ConsultaMedica`); `consultorio/admin.py:25-34` (`ConsultaMedicaLegacyAdmin` registra el modelo legacy); `consultorio/urls.py` y `consultorio/models/__init__.py` (re-exporta el legacy).
- **Descripción:** El proyecto documenta que el modelo activo es `core.ConsultaMedica` y que `consultorio.models.legacy.ConsultaMedica` debe eliminarse. Sin embargo, sigue presente, registrado en admin y referenciado por `Somatometria` (que además carece de campo `empresa` y FK a un `ConsultaMedica` legacy). Esto puede provocar confusiones, doble almacenamiento o consultas cruzadas entre el modelo activo y el legacy, con riesgo de fuga de datos legacy o acceso admin a registros obsoletos no sincronizados.
- **Riesgo:** inconsistencia de datos, exposición accidental de registros legacy en admin, fallos de migración, acoplamiento indebido entre `consultorio` y `core`.
- **Recomendación:** Eliminar `consultorio/models/legacy.py` y `ConsultaMedicaLegacyAdmin` tras confirmar migración de datos a `core.ConsultaMedica`. Añadir `empresa` a `Somatometria` y vincularla a `core.ConsultaMedica` (o eliminarla si ya existe un modelo equivalente en `core`).

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

---

## BLOQUE 14 (laboratorio/ — app raíz)

## H-NUEVO-77 — `laboratorio/views/__init__.py::recepcion_lab` permite crear órdenes de laboratorio a cualquier usuario autenticado, ignora campos clínicos y mapea estudios legacy a LIMS por coincidencia de nombre — ALTO, ABIERTO
- **Ubicación:** `laboratorio/views/__init__.py:33-189` (`recepcion_lab`); `laboratorio/urls.py:45-46` (`recepcion/`); `core/OrdenDeServicio`/`core/DetalleOrden`.
- **Descripción:** La vista solo usa `@login_required` y `get_request_sucursal`, sin `@grupo_requerido`, `@permission_required` ni verificación de `rol`/`empresa` del usuario. Cualquier usuario autenticado puede crear una `OrdenDeServicio`, pasar `medico_id`/`origen` (que la función lee pero descarta) y seleccionar `Estudio`/`PerfilLaboratorio` del catálogo global. Los estudios se mapean a `lims.Analito` y `core.PerfilLims` por `nombre__iexact` dentro de la empresa, sin FK explícita: si no hay coincidencia o hay homónimos, se crean `DetalleOrden` con `analito=None`/`perfil_lims=None`, dejando la orden desconectada del LIMS nuevo.
- **Riesgo:** creación no autorizada de órdenes, pérdida de médico/origen, órdenes con detalles huérfanos del catálogo LIMS, posibles estudios incorrectos si hay homónimos.
- **Recomendación:** Requerir `RECEPCION`/`LABORATORIO`/`ADMIN` y validar que el usuario pertenezca a la empresa/sucursal. Usar FK directas a `lims.Analito`/`core.PerfilLims` (no búsquedas por nombre) o migrar `recepcion_lab` a consumir el catálogo nuevo. Guardar `medico_id`/`origen` en `OrdenDeServicio`.

## H-NUEVO-78 — Las vistas `imprimir_etiqueta_zpl` e `imprimir_etiquetas_lote_zpl` carecen de control de rol y permiten SSRF a cualquier host/puerto — CRÍTICO, CORREGIDO
- **Ubicación:** `laboratorio/views/imprimir_zpl.py:24-85` (`imprimir_etiqueta_zpl`), `:100-145` (`imprimir_etiquetas_lote_zpl`); `laboratorio/services/etiquetas_zpl.py:145-181` (`enviar_zpl_tcp`); `laboratorio/urls.py:59-60`.
- **Descripción:** Ambas vistas son `@login_required` sin `@grupo_requerido` ni permiso. Extraen `zebra_host` y `zebra_port` del cuerpo JSON (o de `empresa.zebra_printer_host`/`port`), y llaman a `socket.create_connection((host, port))`. No hay validación de IP interna/localhost, lista blanca de impresoras ni rate limiting. Un atacante autenticado puede hacer que el servidor abra conexiones TCP arbitrarias a cualquier destino y puerto, escanear la red interna, atacar servicios internos (metadata de cloud, credenciales, etc.) o enviar ZPL a impresoras ajenas.
- **Riesgo:** SSRF desde el servidor; escaneo/explotación de red interna; fugas de información interna; manipulación de impresión de etiquetas.
- **Recomendación:** Restringir a `LABORATORIO`/`RECEPCION`. Validar `zebra_host` contra una lista blanca de impresoras de la empresa (no permitir IPs privadas, localhost, metadatos, etc.). Limitar `zebra_port` a 9100/tcp. No permitir host/port libres en el cuerpo de la petición; usar configuración por empresa.

## H-NUEVO-79 — `kiosko_check_in_qr` es un endpoint público que expone datos de paciente/orden por folio adivinable — ALTO, CORREGIDO
- **Ubicación:** `laboratorio/views/imprimir_zpl.py:165-229` (`kiosko_check_in_qr`); `laboratorio/urls.py:74-75` (`kiosko/`); `laboratorio/templates/laboratorio/kiosko/bienvenida.html`.
- **Descripción:** La vista no requiere autenticación. Recibe un `qr_token` (que es el folio de orden, formato `PRIS-YYYYMMDD-XXXX`) y busca con `OrdenDeServicio.objects.filter(folio_orden=token_clean)` y `folio_orden__iexact`, sin filtro de empresa y sin límite de intentos. El folio es secuencial y se imprime en etiquetas. Si se adivina/explora, se renderiza una plantilla con `paciente`, `nombre_paciente`, `empresa` y la orden. Aunque no modifica la orden, filtra por estados pero aun así renderiza y setea sesión.
- **Riesgo:** exposición de información personal y clínica de pacientes por enumeración de folios; violación a NOM-024/ISO 15189 sobre confidencialidad.
- **Recomendación:** Proteger con token criptográfico firmado (`itsdangerous`/`Signer`) o `UUID` no secuencial, no usar el folio directamente. O requerir autenticación del paciente (portal/login). Añadir rate limiting y logging de accesos.

## H-NUEVO-80 — `crear_medico_ajax` y `crear_paciente_ajax` permiten a cualquier usuario autenticado crear médicos y pacientes — MEDIO/ALTO, CORREGIDO
- **Ubicación:** `laboratorio/views/__init__.py:131-192` (`crear_paciente_ajax`), `:195-273` (`crear_medico_ajax`); `laboratorio/services/unificacion.py:38-63` (`crear_paciente_unificado`), `:130-171` (`_encontrar_core_medico`); `laboratorio/urls.py:33-34`.
- **Descripción:** Ambas vistas usan `@login_required` y filtran por `empresa`, pero no exigen rol (`RECEPCION`, `LABORATORIO`, `ADMIN`). `crear_medico_ajax` genera un `cedula_profesional` aleatorio `PEND-{uuid}` cuando no se proporciona, sin validar cédula real, y crea `core.Medico`. `crear_paciente_unificado` crea `core.Paciente` con tipo `GENERAL`. Un usuario con cuenta (incluido un paciente o empleado no autorizado) puede poblar el catálogo de médicos/pacientes.
- **Riesgo:** creación masiva de médicos/pacientes falsos; suplantación de profesionales; contaminación del directorio médico/pacientes; posible bypass de recepción.
- **Recomendación:** Exigir `@grupo_requerido('RECEPCION','LABORATORIO','ADMIN')` y validar que el usuario tenga permiso de escritura en `core.Medico`/`core.Paciente`. Validar `cedula_profesional` contra formato/regex y verificar duplicados.

## H-NUEVO-81 — `cargar_tarifas_desde_csv` modifica catálogo global sin aislamiento de empresa y sin autor de auditoría — CRÍTICO, PARCIALMENTE CORREGIDO
- **Ubicación:** `laboratorio/views_admin.py:19-123` (`cargar_tarifas_desde_csv`); `laboratorio/admin.py` (registro de `CategoriaExamen`, `Estudio`); `laboratorio/models/catalogo.py:14-185`.
- **Descripción:** `@staff_member_required` + `@require_POST`. Lee un CSV, salta 2 líneas y hace `CategoriaExamen.objects.get_or_create(nombre=tipo)` y `Estudio.objects.update_or_create(codigo=...)` sin `empresa` (ambos modelos carecen de `empresa`). El catálogo resultante es global; un staff de un tenant puede sobrescribir estudios/categorías de todos los tenants. No hay límite de tamaño del archivo, no se registra el usuario que cargó ni se emiten eventos de auditoría. No se filtran estudios inactivos ni se valida la unicidad por empresa.
- **Riesgo:** contaminación cruzada del catálogo; un tenant afecta el catálogo de otros; pérdida de precios/códigos propios de otros tenants; no trazabilidad del cambio.
- **Recomendación:** Añadir `empresa` a `CategoriaExamen`/`Estudio`/`PerfilLaboratorio` y filtrar por `empresa` en todas las operaciones del admin/CSV. Limitar tamaño del archivo. Registrar autor, timestamp y diff de cambios. Usar `transaction.atomic()` con validaciones.

## H-NUEVO-82 — Modelos legacy del catálogo de `laboratorio` carecen de `empresa` y rompen el aislamiento multi-tenant — ALTO, ABIERTO
- **Ubicación:** `laboratorio/models/catalogo.py` (`CategoriaExamen:14-40`, `Estudio:42-160`, `PerfilLaboratorio:162-195`); `laboratorio/models/clinico.py` (`ValorReferencia:60-90`, `RangoReferenciaParametro:320-435`); `laboratorio/models/resultados.py` (`Parametro:20-280`); `laboratorio/models/hl7.py` (`ResultadoHL7:12-77`); `laboratorio/models/ordenes.py` (`Orden:35-253`, `DetalleOrden`).
- **Descripción:** Los modelos de catálogo clínico-prueba-parametro-rango de `laboratorio` no tienen campo `empresa`; usan `unique_together` global (`CategoriaExamen.nombre`, `Estudio.categoria+nombre`, `Parametro.estudio+nombre`, etc.). El flujo operativo `core.OrdenDeServicio`/`lims.Analito` sí es multi-tenant, pero `laboratorio` sigue actuando como catálogo maestro global y como capa de compatibilidad. Esto provoca colisiones de códigos/nombres entre tenants, imposibilidad de que cada tenant tenga su propia lista de precios y catálogo propio, y confusiones con el catálogo nuevo (`lims.Analito`/`core.PerfilLims`/`core.PaqueteLims`).
- **Riesgo:** fugas/confusión de catálogo entre tenants; precios incorrectos; estudios invisibles o sobrescritos; imposibilidad de escalar SaaS.
- **Recomendación:** Migrar a modelos `lims` (con `empresa`) como fuente de verdad, eliminar o desactivar los modelos legacy globales, y eliminar las búsquedas por nombre en el catálogo legacy.

## H-NUEVO-83 — `HistorialResultadosAdmin` permite editar el historial de cambios de resultados, rompiendo trazabilidad forense — ALTO, CORREGIDO
- **Ubicación:** `laboratorio/admin.py:243-259` (`HistorialResultadosAdmin`); `laboratorio/models/resultados.py:280-469` (`HistorialResultados`); `laboratorio/signals.py:111-125`.
- **Descripción:** El `readonly_fields` se define como `tuple(...) if False else ()`, por lo que siempre es `()`. Staff con acceso a admin puede modificar `valor_anterior`, `valor_nuevo`, `motivo_cambio`, `usuario_responsable`, `fecha_hora_cambio`, etc. Solo `has_add_permission` es False y `has_delete_permission` requiere superuser, pero `has_change_permission` queda por defecto `True`. Además, `HistorialResultados.save()` genera el hash SHA-256 antes del `super().save()`, por lo que `fecha_hora_cambio` (auto_now_add) es `None` y no se incluye en el hash.
- **Riesgo:** manipulación de evidencia forense de cambios de resultados; imposibilidad de demostrar integridad ante auditoría COFEPRIS/ISO 15189.
- **Recomendación:** Hacer todos los campos de `HistorialResultados` `readonly_fields`; forzar `has_change_permission=False` y `has_delete_permission=False`. Corregir la generación del hash para que incluya el timestamp real, o usar un campo separado `hash_verificado`.

## H-NUEVO-84 — `seed_rangos_iso15189` puede borrar todos los rangos de referencia de forma global — ALTO, CORREGIDO
- **Ubicación:** `laboratorio/management/commands/seed_rangos_iso15189.py:76-79`; `laboratorio/models/clinico.py:320-435` (`RangoReferenciaParametro` sin `empresa`).
- **Descripción:** El comando de management acepta `--limpiar` y ejecuta `RangoReferenciaParametro.objects.all().delete()` sin filtro de `empresa` ni confirmación. Aunque es un comando de admin/management, un error en producción con `--limpiar` borra los rangos ISO/15189 de todos los tenants. No hay rollback/excepción específica ni advertencia de alcance.
- **Riesgo:** pérdida masiva de rangos de referencia clínicos; afectación simultánea a todos los tenants; reprocesamiento costoso.
- **Recomendación:** Si `RangoReferenciaParametro` sigue vivo, añadir `empresa` y filtrar `.filter(empresa=...)`. Exigir confirmación explícita (`--yes`) y respaldo previo. Documentar que el comando es destructivo.

## H-NUEVO-85 — `ResultadoHL7` y `ResultadoHL7Huerfano` mezclan modelos legacy/LIMS y carecen de aislamiento de empresa — MEDIO, ABIERTO
- **Ubicación:** `laboratorio/models/hl7.py:12-77` (`ResultadoHL7`), `:80-116` (`ResultadoHL7Huerfano`); `laboratorio/models/ordenes.py:35-253` (`Orden` legacy); `laboratorio/models/resultados.py:20-280` (`Parametro` legacy).
- **Descripción:** `ResultadoHL7` carece de `empresa`, apunta a `laboratorio.Orden` (legacy, `empresa` nullable) y a `laboratorio.Parametro` (global). `ResultadoHL7Huerfano` tiene `empresa` nullable. No hay mecanismo visible que asocie un mensaje HL7 entrante con el tenant correcto basado en IP/equipo. La lógica de recepción HL7 vive en `core.services.lims.interfaces_lims_service` (no auditado en este bloque), pero los modelos subyacentes no aseguran aislamiento.
- **Riesgo:** resultados de analizadores pueden ligarse a la orden/tenant incorrecto; pérdida de trazabilidad HL7; posible mezcla de datos de pacientes entre tenants.
- **Recomendación:** Migrar HL7 a usar `core.OrdenDeServicio`, `core.ResultadoParametro` y `lims.Analito`, con `empresa` obligatoria y validada desde el equipo/interfaz. Eliminar referencias a `laboratorio.Orden`/`Parametro`.

## H-NUEVO-86 — `laboratorio/signals.py` usa `DatabaseError` sin importarlo y no inicializa permisos de privacidad — MEDIO, PARCIALMENTE CORREGIDO
- **Ubicación:** `laboratorio/signals.py:1-18` (imports), `:111-125` (`registrar_historial_resultado`), `:188-225` (`crear_permisos_privacidad`), `:299-318` (`inicializar_sistema_privacidad`); `laboratorio/apps.py:1-29`.
- **Descripción:** El `except (ValueError, TypeError, DatabaseError) as e` en `registrar_historial_resultado` referencia `DatabaseError` que no está importado, provocando `NameError` si se dispara una excepción de BD y abortando el registro de historial. `crear_permisos_privacidad` e `inicializar_sistema_privacidad` existen pero no se llaman desde `apps.py` (solo se importan señales, no se invoca inicialización). Los permisos creados (`ver_historial_resultados`, `modificar_resultados_validados`) son globales, no por tenant.
- **Riesgo:** fallo silencioso del historial de resultados; permisos de privacidad NOM-024 nunca activos o globales.
- **Recomendación:** Importar `DatabaseError` (`from django.db.utils import DatabaseError`). Llamar `inicializar_sistema_privacidad()` en `LaboratorioConfig.ready()` o eliminar si es obsoleto. Vincular permisos a grupos/empresa si es requerido por NOM-024.

## H-NUEVO-87 — `ResponsableSanitario` no tiene `empresa` y desactiva responsables de forma global — MEDIO/ALTO, ABIERTO
- **Ubicación:** `laboratorio/models/regulatorio.py:14-99` (`ResponsableSanitario`), `:91-99` (`save`); `laboratorio/admin.py:262-270`.
- **Descripción:** El modelo no tiene campo `empresa`, la `cedula_profesional` es `unique=True` a nivel global y `save()` hace `ResponsableSanitario.objects.filter(activo=True).exclude(pk=self.pk).update(activo=False)` sin filtrar empresa. Esto implica que solo puede haber un responsable sanitario activo en todo el sistema SaaS, compartiendo firma/autorización entre todos los tenants.
- **Riesgo:** un tenant no puede tener su propio responsable sanitario; un cambio en un tenant desactiva el de todos; incumplimiento NOM-007/COFEPRIS por responsable incorrecto en reportes.
- **Recomendación:** Añadir `empresa` a `ResponsableSanitario`, cambiar `unique_together=('empresa','cedula_profesional')` y filtrar `activo` por `empresa` en `save()`.

## H-NUEVO-88 — `laboratorio/views/etiquetas.py` descarga etiquetas con solo control de grupo amplio y sin permiso de impresión específico — BAJO/MEDIO, ABIERTO
- **Ubicación:** `laboratorio/views/etiquetas.py:30-133` (`imprimir_etiqueta_tubo`, `imprimir_etiquetas_lote`, `imprimir_etiqueta_qr`); `laboratorio/urls.py:51-54`.
- **Descripción:** Las vistas usan `@login_required` + `@grupo_requerido('LABORATORIO','RECEPCION')`. Cualquier usuario en cualquiera de esos dos grupos puede solicitar etiquetas de cualquier orden de su empresa (`empresa`). No se verifica que la orden pertenezca a la sucursal del usuario ni que tenga permiso específico de impresión. `imprimir_etiquetas_lote` acepta una lista de IDs y la descarga en PDF en bloque.
- **Riesgo:** impresión masiva de etiquetas por personal sin autorización explícita; posible fuga de folios/QR.
- **Recomendación:** Añadir permiso `imprimir_etiquetas` y verificar sucursal. Limitar número de órdenes por lote. Registrar quién imprimió y cuándo.

## H-NUEVO-89 — `HistorialResultados` genera hash de integridad antes de tener el timestamp — BAJO/MEDIO, CORREGIDO
- **Ubicación:** `laboratorio/models/resultados.py:398-430` (`save`, `generar_hash_integridad`); `laboratorio/signals.py:111-125`.
- **Descripción:** `save()` llama `generar_hash_integridad()` antes de `super().save()`, cuando `self.fecha_hora_cambio` es `None` porque es `auto_now_add`. El JSON para SHA-256 incluye `timestamp: ''`. El timestamp real no está protegido por el hash.
- **Riesgo:** manipulación del timestamp posterior a la creación sin invalidar el hash; debilidad en prueba forense.
- **Recomendación:** Generar el hash tras `super().save()` (usando el timestamp real) o almacenarlo en un campo `hash_verificado` calculado en una segunda instancia.

## H-NUEVO-90 — APIs de CAPA/EQA usan `request.user.rol` en lugar de permisos/grupos reales — BAJO/MEDIO, ABIERTO
- **Ubicación:** `laboratorio/views/compliance.py:15-22` (`_empresa_y_permiso`), `:24-75` (`no_conformidades_api`), `:77-130` (`no_conformidad_transicion_api`), `:132-185` (`rondas_eqa_api`), `:187-222` (`evaluar_resultado_eqa_api`); `laboratorio/urls.py:83-89`.
- **Descripción:** `_empresa_y_permiso` valida `request.user.rol in _ROLES_COMPLIANCE` (`ADMIN`, `DIRECTOR`, `GERENTE`, `LABORATORIO`). No usa `Permission`, `Group` ni `@permission_required`. Si el campo `rol` del usuario es editable por admin o por otra vía, un atacante puede cambiar su `rol` para acceder a CAPA/EQA. No hay control de sucursal.
- **Riesgo:** elevación de privilegios por modificación de `rol`; acceso a datos de calidad de otros usuarios.
- **Recomendación:** Usar `Permission`/`Group` (`laboratorio.view_noconformidad`, `add_noconformidad`, etc.) o `@permission_required` concretos. Verificar que el usuario pertenezca a la empresa y a la sucursal requerida.

## Confirmaciones positivas (laboratorio/) — CORRECTO
- `laboratorio/services/hl7_handshake.py` — parseo de valores HL7 a `Decimal` sin usar `float` intermedio, normalización de unidades y rechazo de no numéricos.
- `laboratorio/services/westgard.py` — motor puro de reglas Westgard sin efectos secundarios ni acceso a BD.
- `laboratorio/services/cci_canal.py` — `MedicionControlInterno` filtrado por `empresa/equipo/analito`; `EstadoCanalAnalizador` con restricción única por terna.
- `laboratorio/views/cci_api.py` — validación de `Analito.empresa`, agregaciones por día/hora mediante ORM, sin SQL raw.
- `laboratorio/services/iso15189.py` — rango dinámico por sexo/edad con fallback estático y cálculo de Z-score para EQA.
- `laboratorio/views/compliance.py` — `get_object_or_404` con `ronda__empresa=empresa`; transición de CAPA invoca `full_clean` y genera `NoConformidadEvento`.

---

## BLOQUE 15 (lims/)

## H-NUEVO-91 — `purgar_lims` y `importar_catalogo_lims --reset` ejecutan borrados globales de catálogo con SQL raw y sin `empresa_id` obligatorio — CRÍTICO, CORREGIDO
- **Ubicación:** `lims/management/commands/purgar_lims.py:110-137` (`TRUNCATE` global), `:150-163` (métodos `_truncar`/`_truncar_m2m`); `lims/management/commands/importar_catalogo_lims.py:151-155` (`Analito.objects.all().delete()` bajo `tenant_bypass`); `lims/management/commands/ensamblar_lims_v75.py:64-66` (`--reset-catalogo`).
- **Descripción:** `purgar_lims` emite `TRUNCATE ... RESTART IDENTITY CASCADE` y `DELETE FROM` sobre tablas de `lims`, `laboratorio` y `core` (catálogo técnico) sin filtro de `empresa` y sin requerir `--empresa-id`; solo pide `CONFIRMO` o `--force`. `importar_catalogo_lims --reset` borra todos los `ValorReferenciaAnalito` y `Analito` con `.objects.all().delete()` bajo `tenant_bypass`. Ambos comandos operan a nivel de toda la base de datos.
- **Riesgo:** borrado total del catálogo de todos los tenants; pérdida de datos irreversible; violación del aislamiento multi-tenant.
- **Recomendación:** Requerir `--empresa-id` y eliminar únicamente los registros de esa empresa. Evitar `TRUNCATE CASCADE` global; usar `DELETE` filtrado por `empresa`. Hacer backup/respaldos automáticos y registrar en `AuditLog`.

## H-NUEVO-92 — Constraints `unique=True` globales en modelos `lims` impiden duplicados entre tenants — ALTO, CORREGIDO
- **Ubicación:** `lims/models.py:35` (`Analito.codigo`), `:36-39` (`codigo_rastreo_iso`), `:31` (`id_legacy`), `:324` (`PerfilLims.nombre`), `:312` (`id_perfil_legacy`), `:317` (`id_examen_legacy`), `:367` (`PaqueteLims.nombre`), `:360` (`id_paquete_legacy`).
- **Descripción:** Campos de nombre/código/legacy son `unique=True` a nivel global, no por `empresa`. En un SaaS multi-tenant es esperado que cada tenant pueda tener su propio catálogo. Actualmente un segundo tenant no puede usar el mismo `codigo` (`GLU`) ni un paquete llamado `Perfil básico`. El importador mitiga colisiones renombrando códigos (`GLU-x`), lo que corrompe los identificadores.
- **Riesgo:** colisiones de catálogo, códigos renombrados, datos mezclados entre tenants, escalabilidad limitada.
- **Recomendación:** Cambiar constraints a `unique_together=('empresa','codigo')`, `('empresa','nombre')` y `('empresa','id_*_legacy')`. Migrar legacy IDs a `null` para tenants que no los usen.

## H-NUEVO-93 — `ValorReferenciaAnalito` no es `TenantModel` y las tablas M2M de `PerfilLims`/`PaqueteLims` carecen de `empresa` en sus constraints — MEDIO/ALTO, ABIERTO
- **Ubicación:** `lims/models.py:125-185` (`ValorReferenciaAnalito` hereda `models.Model`), `:290-303` (`PerfilAnalito`), `:371-380` (M2M `PaqueteLims.analitos/perfiles`), `lims/admin.py:31-40` (`ValorReferenciaAnalitoAdmin` con `TenantScopedAdmin`).
- **Descripción:** `ValorReferenciaAnalito` no tiene campo `empresa` ni hereda de `TenantModel`. Admin intenta usar `TenantScopedAdmin` con un modelo que no tiene `empresa`, lo que puede fallar o filtrar incorrectamente. `PerfilAnalito` y las tablas M2M no incluyen `empresa` en `unique_together`, permitiendo (a nivel de BD) que un perfil de tenant A incluya un analito de tenant B si se saltara `tenant_protected_get`.
- **Riesgo:** filtrado/admin incorrecto, potencial mezcla de rangos entre tenants, relaciones cruzadas.
- **Recomendación:** Hacer `ValorReferenciaAnalito` heredar de `TenantModel` con `empresa` (o `unique_together` a través de `analito__empresa`). Añadir `empresa` a `PerfilAnalito` y a las tablas M2M con constraints por empresa.

## H-NUEVO-94 — Comandos de importación y sincronización de `lims` operan con `tenant_bypass` y afectan datos de todos los tenants — CRÍTICO/ALTO, ABIERTO
- **Ubicación:** `lims/management/commands/importar_catalogo_lims.py:146-235` (`tenant_bypass` + `update_or_create` por `id_legacy`), `lims/management/commands/importar_examenes_perfil_lims.py:119-` (`tenant_bypass` + `Analito.objects.all()`), `lims/management/commands/importar_paquetes_perfil_lims.py:119-`, `lims/management/commands/sincronizar_precios_lims.py:187-343`, `lims/management/commands/limpiar_catalogo_veterinario.py:26-94`, `lims/management/commands/ensamblar_lims_v75.py:55-`.
- **Descripción:** Todos usan `with tenant_bypass():` y consultan `.objects.all()` sin filtrar `empresa`. `importar_catalogo_lims` actualiza por `id_legacy` único global; si se importa a un tenant distinto, puede sobrescribir el analito de otro tenant. `sincronizar_precios_lims` aplica una tarifa CSV única a todos los registros coincidentes de todos los tenants. `limpiar_catalogo_veterinario` desactiva registros en todos los tenants. `--empresa-id` es opcional y con frecuencia se resuelve por `resolve_default_empresa_sistema()`.
- **Riesgo:** sobreescritura cruzada de catálogos, precios y activación/desactivación global; pérdida de datos aislados por tenant.
- **Recomendación:** Filtrar todas las queries por `empresa` (o iterar por empresa con `--empresa-id` obligatorio). No usar `tenant_bypass` para operaciones de datos de un tenant. Hacer obligatorio `--empresa-id` y rechazar operaciones multi-tenant implícitas.

## H-NUEVO-95 — `PrecioItem.aplicar_inflacion_bulk` no filtra por empresa y omite `costo_lista`/`fecha_actualiz` — MEDIO, CORREGIDO
- **Ubicación:** `lims/models.py:480-488` (`aplicar_inflacion_bulk`), `lims/views/precios.py:197-239` (`ajuste_masivo`).
- **Descripción:** El classmethod recibe una lista de IDs y hace `cls.objects.filter(id__in=ids)` sin `empresa`. Aunque la vista `ajuste_masivo` filtra previamente, cualquier otro llamado puede pasar IDs de cualquier tenant. Además solo actualiza `precio_venta` (sin `fecha_actualiz` ni `costo_lista`), dejando `fecha_actualiz` desactualizada y el catálogo Nivel 1/2/3 sin sincronizar.
- **Riesgo:** actualización de precios de otro tenant; inconsistencia entre `precio_venta` y `costo_lista`.
- **Recomendación:** Añadir `empresa` al filtro y a `bulk_update`. Actualizar `costo_lista` de los objetos relacionados tras el ajuste masivo.

## H-NUEVO-96 — `ajuste_masivo` de precios no sincroniza `costo_lista` del catálogo — BAJO/MEDIO, CORREGIDO
- **Ubicación:** `lims/views/precios.py:197-239` (`ajuste_masivo`), `lims/models.py:462-469` (`aplicar_inflacion`).
- **Descripción:** `ajuste_masivo` aplica `PrecioItem.aplicar_inflacion_bulk` pero no actualiza `Analito.costo_lista`, `PerfilLims.costo_lista` ni `PaqueteLims.costo_lista`. La vista `actualizar_precio` sí actualiza ambos. Tras un ajuste masivo, `PrecioItem.precio_venta` y `costo_lista` divergen.
- **Riesgo:** inconsistencia de precios entre Nivel 4 y Nivel 1/2/3; posibles errores de cobro.
- **Recomendación:** Calcular el nuevo `costo_lista` y actualizar los registros relacionados dentro de `ajuste_masivo` o en `aplicar_inflacion_bulk`.

## H-NUEVO-97 — APIs de rangos en `Analito` no validan choices ni consistencia de edades — BAJO/MEDIO, CORREGIDO
- **Ubicación:** `lims/views/analitos.py:140-235` (`api_rangos`, `api_rango_item`).
- **Descripción:** `api_rangos` y `api_rango_item` toman `sexo` y `unidad_edad` directamente del cuerpo JSON sin validar contra `SEXO_CHOICES` / `UNIDAD_EDAD_CHOICES`. `edad_minima` y `edad_maxima` se convierten con `int()` sin validar `min <= max`. No se asignan valores críticos ni se valida `ref_minimo <= ref_maximo`.
- **Riesgo:** rangos inválidos en catálogo; validaciones ISO 15189 incorrectas; posible excepción por `ValueError`.
- **Recomendación:** Validar choices, orden de edades, y consistencia de rangos. Usar forms/serializers.

## Confirmaciones positivas (lims/) — CORRECTO
- `lims/models.py` — `Analito`, `PerfilLims`, `PaqueteLims`, `PrecioItem` heredan `TenantModel` y tienen `empresa`.
- `lims/views/*` — usan `empresa_lims(request)` (solo `request.user.empresa`) y `tenant_protected_get` para leer/escribir objetos.
- `lims/views/precios.py::ajuste_masivo` — acota IDs a `PrecioItem` de la empresa antes de `bulk_update`.
- `lims/signals.py` — sincroniza `PrecioItem.precio_venta` desde `costo_lista` con señales `post_save`.
- `lims/veterinary_catalog.py` — filtro de catálogo veterinario con normalización de texto.

---

## BLOQUE 16 (config/)

## H-NUEVO-98 — `ALLOWED_HOSTS` en producción cae a `localhost`/`127.0.0.1` si no se configura `SERVER_NAME`/`DOMAIN_NAME` — MEDIO/ALTO, CORREGIDO
- **Ubicación:** `config/settings/security.py:200-207`; `config/settings/production.py:27-29`.
- **Descripción:** Si en producción no se define `ALLOWED_HOSTS` ni `SERVER_NAME`/`DOMAIN_NAME`, la lista queda `['localhost', '127.0.0.1']`. Django aceptará peticiones cuyo header `Host` sea `localhost`, lo que puede usarse para Host header injection / cache poisoning, especialmente si el rate-limiting o el logging de IP confían en `X-Forwarded-For`.
- **Riesgo:** bypass parcial de validación de host, envenenamiento de caché/proxy, desvío de webhooks internos.
- **Recomendación:** En producción exigir `ALLOWED_HOSTS` o `SERVER_NAME` con el dominio real; nunca incluir `localhost`/`127.0.0.1` en producción. Rechazar arranque si no está configurado.

## H-NUEVO-99 — Archivos monolíticos muertos `config/settings.py` y `config/urls.py` coexisten con la configuración activa — MEDIO, ABIERTO
- **Ubicación:** `config/settings.py` (1176 líneas, ~53 KB), `config/urls.py` (824 líneas, ~64 KB); `config/settings/__init__.py` y `config/urls/__init__.py` son los módulos activos.
- **Descripción:** `DJANGO_SETTINGS_MODULE='config.settings'` resuelve al paquete `config/settings/`, y `ROOT_URLCONF='config.urls'` resuelve al paquete `config/urls/`. Los archivos `.py` planos son código muerto que contienen duplicados de settings y URL routes. Pueden desfasarse, confundir auditorías futuras o ser importados por scripts legacy por error. Contienen el fallback inseguro de `SECRET_KEY` y otra lógica de arranque duplicada.
- **Riesgo:** configuración inconsistente, uso accidental, dificultad de mantenimiento, proliferación de secretos/defaults duplicados.
- **Recomendación:** Eliminar `config/settings.py` y `config/urls.py` (o renombrar a `.bak`/`_legacy`) tras confirmar que ningún script los importa directamente. Usar solo la versión modular.

## H-NUEVO-100 — `FACTURAMA_SANDBOX` por defecto `True` en producción si la variable no está definida — ALTO, CORREGIDO
- **Ubicación:** `config/settings/ia.py:45` (`FACTURAMA_SANDBOX = os.environ.get('FACTURAMA_SANDBOX', 'True') == 'True'`); `config/settings/__init__.py:52-53` (`if DEBUG or IS_SANDBOX: FACTURAMA_SANDBOX = True`).
- **Descripción:** El valor por omisión de la variable `FACTURAMA_SANDBOX` es `True`. En producción (`DEBUG=False`, `IS_SANDBOX=False`), si el operador no define explícitamente `FACTURAMA_SANDBOX=False`, el sistema continuará apuntando al entorno sandbox de Facturama en lugar del productivo. Esto generaría CFDI de prueba o fallos silenciosos en facturación real.
- **Riesgo:** facturación incorrecta, timbrado de prueba en producción, incumplimiento fiscal.
- **Recomendación:** Cambiar el default a `False` en producción o añadir validación de arranque que rechace `FACTURAMA_SANDBOX=True` si `IS_PRODUCTION`.

## H-NUEVO-101 — `PRISLAB_TENANT_SHADOW_MODE` por defecto `True` y `PRISLAB_TENANT_STRICT_MODE` depende de entorno — MEDIO/ALTO, ABIERTO
- **Ubicación:** `config/settings/security.py:229-237`.
- **Descripción:** `PRISLAB_TENANT_SHADOW_MODE` es `True` por defecto. Si `PRISLAB_TENANT_STRICT_MODE` se desactiva (por ejemplo en staging cuando no es producción pero tampoco `DEBUG`), las consultas sin tenant en `TenantModel` no serán bloqueadas, solo logueadas. La combinación de dos flags permite que un entorno no-producción/no-debug opere sin aislamiento forzado.
- **Riesgo:** fugas de datos entre tenants en entornos intermedios si `STRICT_MODE` se desactiva; dependencia de flags confusa.
- **Recomendación:** Hacer que `PRISLAB_TENANT_STRICT_MODE` sea `True` por defecto en cualquier entorno que no sea desarrollo local. Documentar y forzar que `SHADOW_MODE` no anule `STRICT_MODE`.

## H-NUEVO-102 — `PRISLAB_TRUSTED_PROXY_COUNT` y `PRISLAB_TRUSTED_PROXY_CIDRS` por defecto insuficientes — MEDIO, ABIERTO
- **Ubicación:** `config/settings/security.py:241-256`.
- **Descripción:** En producción `PRISLAB_TRUSTED_PROXY_COUNT` es `1` por defecto y `PRISLAB_TRUSTED_PROXY_CIDRS` incluye `127.0.0.0/8,::1/128`. Si el despliegue real no tiene exactamente un proxy confiable o si un atacante puede enviar `X-Forwarded-For` desde esos rangos, la dirección IP de origen podría ser spoofeada.
- **Riesgo:** bypass de rate limiting, bloqueos de IP incorrectos, posibles decisiones de seguridad basadas en IP falsa.
- **Recomendación:** Requerir que `PRISLAB_TRUSTED_PROXY_COUNT` y `PRISLAB_TRUSTED_PROXY_CIDRS` se configuren explícitamente en producción; validar en arranque. No confiar en `X-Forwarded-For` sin validar el proxy inmediato.

## H-NUEVO-103 — `RESULTADOS_PUBLICOS_TOKEN_MAX_AGE_SECONDS` por defecto es 7 días — MEDIO, ABIERTO
- **Ubicación:** `config/settings/base.py:306-308`.
- **Descripción:** Los tokens de validación pública de resultados (`validar/resultado/<uuid:token>/`) tienen una vigencia máxima de 7 días por defecto. Si un enlace se filtra o se comparte, permanece activo toda una semana.
- **Riesgo:** acceso prolongado a resultados de pacientes si el token se expone; violación de principio de mínima exposición.
- **Recomendación:** Reducir el default a 24-48 horas (o el tiempo de entrega comercial). Permitir override por empresa.

## H-NUEVO-104 — `ADMIN_IP_RESTRICTION_ENABLED` y `ADMIN_GROUP_RESTRICTION_ENABLED` desactivados por defecto — MEDIO, ABIERTO
- **Ubicación:** `config/settings/base.py:340-342`.
- **Descripción:** Las protecciones de `/admin/` por IP y por grupo están apagadas por defecto. En producción, si no se configuran, `/admin/` depende únicamente de `is_staff`/`is_superuser` y de la contraseña del usuario.
- **Riesgo:** aumenta la superficie de ataque del admin; compromiso de una cuenta `is_staff` expone todo el admin.
- **Recomendación:** Activar `ADMIN_GROUP_RESTRICTION_ENABLED` y `ADMIN_IP_RESTRICTION_ENABLED` por defecto en producción; requerir `ALLOWED_ADMIN_IPS` y grupos explícitos.

## H-NUEVO-105 — `HL7_ACTIVE` puede activarse sin `HL7_ALLOWED_IPS` — MEDIO, ABIERTO
- **Ubicación:** `config/settings/base.py:322-323`.
- **Descripción:** `HL7_ACTIVE` se activa por env y `HL7_ALLOWED_IPS` es una lista vacía si no se configura. El receptor `api/iot/hl7/` puede depender de esta lista, pero si la validación es permisiva, un endpoint HL7 activo sin restricción de IP es una superficie de ataque.
- **Riesgo:** inyección de resultados HL7 falsos desde cualquier origen; integridad de resultados comprometida.
- **Recomendación:** En `security.py` o en la vista `receptor_hl7` rechazar `HL7_ACTIVE=True` si `HL7_ALLOWED_IPS` está vacío en producción.

## H-NUEVO-106 — `IPS_INTERNAS_2FA_BYPASS` puede derivarse de `X-Forwarded-For` sin validar — MEDIO, ABIERTO
- **Ubicación:** `config/settings/base.py:303-304`.
- **Descripción:** La lista `IPS_INTERNAS_2FA_BYPASS` permite omitir 2FA si la IP del cliente coincide. Si el cálculo de IP confía en `X-Forwarded-For` y `PRISLAB_TRUSTED_PROXY_COUNT`/`CIDRS` no es estricto, un atacante externo puede enviar un `X-Forwarded-For` interno y saltarse 2FA.
- **Riesgo:** bypass de 2FA por IP spoofing; acceso sin segundo factor.
- **Recomendación:** No usar `X-Forwarded-For` crudo para `2FA_BYPASS`; usar la IP de conexión directa o validar el proxy. Documentar riesgo y desactivar por defecto.

## H-NUEVO-107 — `config/urls/modulos.py` expone módulos sensibles bajo el mismo `urlpatterns` sin separación de autenticación — BAJO, ABIERTO
- **Ubicación:** `config/urls/modulos.py:24-222`.
- **Descripción:** Muchas rutas de director, médicos, RRHH, CRM, bienestar, etc. se registran en el mismo URLconf. La protección depende de cada vista individual. No hay un prefijo de middleware o URL namespace que exija rol común. Esto aumenta el riesgo de que una vista mal protegida exponga funcionalidad crítica.
- **Riesgo:** elevación de privilegios si una vista individual omite `@login_required` o chequeo de rol/empresa.
- **Recomendación:** Añadir tests de seguridad que visiten cada ruta con usuarios de distintos roles y verifiquen 403. Considerar decoradores de grupo en URLs críticas.

## Confirmaciones positivas (config/) — CORRECTO
- `config/settings/__init__.py` — estructura modular de settings (base, database, security, storage, ia, cache, celery, logging, local/production).
- `config/settings/security.py` — validaciones de arranque: `SECRET_KEY`, `FERNET_KEY`, `LAB_VALIDATION_PIN`, `PRISLAB_ESCUDO_USUARIO_ID`, `PRISLAB_EMERGENCY_TENANT_BYPASS`, tokens de servicio.
- `config/settings/base.py` — `DEBUG` default `False`; `AUTH_PASSWORD_VALIDATORS` con `min_length=10`; `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`; `ADMIN_IP_RESTRICTION_ENABLED`/`ADMIN_GROUP_RESTRICTION_ENABLED` existen como opt-in.
- `config/settings/cache.py` — Redis/Channels comparten `REDIS_URL`; sesiones en cache cuando hay Redis.
- `config/storage_backends.py` — `TenantS3Storage` inserta automáticamente `empresa_slug` en la ruta de S3; `GoogleDriveStorage` y `TenantDriveStorage` son compatibilidad histórica inactiva.
- `config/admin_site.py` — `PrislabAdminSite` reorganiza admin por departamentos y filtra por grupos/rol del usuario; superusuario ve todo.

---

## BLOQUE 17 (core/ — middleware, tenant, RBAC, decoradores, vistas generales, 2FA y modelos base)

## Nota de cierre parcial de H-013 (cross-check docs canónicas)
- **Ubicación:** `docs/audit/PLAN_MAESTRO_LOCAL_AUDITORIA_EXTERNA.md:117-166`, `config/settings/base.py:192-193`, `core/middleware/rate_limit.py:126-137`, `core/middleware/__init__.py:1-30`, `find_by_name` para `admin_access_restrict`.
- **Descripción:** H-013 afirmaba una deriva entre documentación y código: rate limit no atómico, límite `/api/` solo a POST, `LogAccesoExpedienteMiddleware` presente, `admin_access_restrict.py` presente y `TenantSubdomainMiddleware` activo. En la revisión actual del repositorio local: `RateLimitMiddleware` usa `cache.add`+`cache.incr` (contador atómico), el límite `/api/` aplica a todos los métodos, `LogAccesoExpedienteMiddleware` ya no aparece en `core/middleware/seguridad.py` ni `__init__.py`, `admin_access_restrict.py` no existe como fuente (sólo `.pyc` en `__pycache__`) y `TenantSubdomainMiddleware` está documentado como activo en la guía de auditoría.
- **Estatus:** H-013 se considera cerrado en el código canónico actual.

## H-NUEVO-108 — `BlindajeExpedienteMiddleware` no bloquea `DELETE` sobre notas selladas — MEDIO, CORREGIDO
- **Ubicación:** `core/middleware/blindaje_expediente.py:42-48, 62-76`.
- **Descripción:** El middleware solo intercepta métodos `POST`, `PUT`, `PATCH`. Una petición `DELETE` a una nota sellada puede llegar a la vista y ejecutarse; la señal `pre_save` no se dispara al borrar, con lo que la inmutabilidad forense se rompe.
- **Riesgo:** eliminación de notas clínicas selladas, pérdida de trazabilidad NOM-004.
- **Recomendación:** Incluir `DELETE` en el filtro de métodos y/o mover la protección a `pre_delete` en el modelo.

## H-NUEVO-109 — `BlindajeExpedienteMiddleware` delega el desbloqueo a un permiso Django convencional no mapeado en RBAC — BAJO/MEDIO, ABIERTO
- **Ubicación:** `core/middleware/blindaje_expediente.py:68`.
- **Descripción:** Verifica `request.user.has_perm('core.desbloquear_nota_sellada')`, un permiso de modelo no listado en `core/rbac/permissions.py`. Si un administrador Django lo asigna manualmente, un usuario puede desbloquear notas selladas sin pasar por el mapa central de roles.
- **Riesgo:** desbloqueo forense no controlado por el RBAC central.
- **Recomendación:** Alinear con `PERMISSION_MAP` o con un permiso RBAC explícito; registrar en `LogAccionSensible`.

## H-NUEVO-110 — `SentinelTelemetryMiddleware` captura y persiste `request.POST`/`GET` en incidencias sin garantía de saneado de secretos — MEDIO, ABIERTO
- **Ubicación:** `core/middleware/sentinel.py:677-697`.
- **Descripción:** `_registrar_incidencia_async` envuelve `request.GET` y `request.POST` con `sanitizar_datos` y los guarda en `IncidenciaSentinel.datos_request`. Si `sanitizar_datos` (definido en `consultorio.sentinel_service`) no enmascara claves como contraseñas, tokens, PINs o `csrfmiddlewaretoken`, los datos sensibles quedan almacenados en la tabla.
- **Riesgo:** exposición de credenciales, PII o tokens en tabla de incidencias.
- **Recomendación:** Verificar/mostrar el saneador; adicionar claves en lista de ofuscación; enmascarar automáticamente antes de guardar.

## H-NUEVO-111 — `SentinelTelemetryMiddleware` ejecuta auto-cleanup y DB close en hilo daemon sin protección de concurrencia — MEDIO, ABIERTO
- **Ubicación:** `core/middleware/sentinel.py:109-181, 518-559`.
- **Descripción:** El contador de requests lentos es una variable de clase (`_slow_request_count`) no protegida por locks. Llegados a 5, dispara `_disparar_auto_cleanup`, que corre en un hilo daemon, llama `Session.objects.filter(...).delete()` y `close_old_connections()`. El cierre de conexiones en un hilo daemon puede afectar conexiones compartidas y el contador no es seguro en concurrencia.
- **Riesgo:** race conditions, cierre de conexiones en uso, degradación de performance.
- **Recomendación:** Usar un lock para `_slow_request_count`; evitar `close_old_connections()` global o limitarlo al hilo actual; separar responsabilidades.

## H-NUEVO-112 — `SentinelTelemetryMiddleware` redirige a la misma URL tras `DatabaseError` sin protección anti-loop — BAJO, ABIERTO
- **Ubicación:** `core/middleware/sentinel.py:468-473`.
- **Descripción:** `_repair_database_error` retorna `HttpResponseRedirect(path)` para reintentar. Si la base de datos sigue caída, el navegador recarga la misma URL y genera un bucle hasta que el usuario aborte.
- **Riesgo:** bucle de redirecciones, mala UX, posible carga innecesaria.
- **Recomendación:** Redirigir a una ruta segura como `/home/` o devolver `503` con `Retry-After` en lugar de redirigir a `path`.

## H-NUEVO-113 — `EmpresaIdentityMiddleware` puede asignar un usuario sin `empresa` a `pk=1` en entornos multi-tenant — MEDIO, CORREGIDO
- **Ubicación:** `core/middleware/empresa.py:78-81`, `core/utils/default_empresa.py:15-41`.
- **Descripción:** Si `request.user.empresa` es `None`, el middleware llama `resolve_default_empresa_sistema()`. Si hay más de una empresa activa y `pk=1` existe, retorna `Empresa(pk=1)` sin más validación. Ese usuario pasa `PRISLAB_TENANT_STRICT_MODE` y ve datos de `pk=1` aunque pertenezca a otro tenant.
- **Riesgo:** fuga cross-tenant para usuarios legacy con `empresa` nula.
- **Recomendación:** En multi-tenant eliminar el fallback a `pk=1`; requerir `PRISLAB_DEFAULT_EMPRESA_ID` explícito o bloquear login de usuarios sin `empresa`.

## H-NUEVO-114 — `TenantSubdomainMiddleware` intenta resolver `Empresa` por campos inexistentes (`subdominio`, `slug`) — BAJO, ABIERTO
- **Ubicación:** `core/middleware/tenant_subdomain.py:1-144`, `core/models/base.py:69-154`.
- **Descripción:** El middleware busca empresa por `subdominio`, `slug` o `nombre__iexact`, pero `core.models.Empresa` no define los campos `subdominio` ni `slug`. En la práctica el fallback es `nombre__iexact`, lo cual no es fiable para nombres compuestos.
- **Riesgo:** resolución incorrecta de tenant para usuarios anónimos; login/branding incorrecto; denegación innecesaria en modo estricto.
- **Recomendación:** Añadir campos `subdominio`/`slug` a `Empresa` con `unique=True` o usar un modelo relacionado `EmpresaSubdominio`.

## H-NUEVO-115 — `FeatureFlagMiddleware` permite acceso si `request.modulos_activos` no está definido — BAJO/MEDIO, CORREGIDO
- **Ubicación:** `core/middleware/feature_flags.py:119-123`.
- **Descripción:** Si `request.modulos_activos` no existe, `getattr(request, 'modulos_activos', {})` retorna `{}` y `.get(modulo_requerido, True)` devuelve `True`. Si `EmpresaIdentityMiddleware` falla o no se ejecuta, se bypassa el bloqueo de módulos.
- **Riesgo:** acceso a módulos no contratados por fallo de orden de middleware o excepción previa.
- **Recomendación:** Cambiar el default a `False` cuando no hay empresa/contexto; adoptar el principio de fallar cerrado.

## H-NUEVO-116 — `TenantStorageMiddleware` genera slug de tenant a partir del `nombre` con posible colisión — BAJO/MEDIO, ABIERTO
- **Ubicación:** `core/middleware/seguridad.py:100-133`.
- **Descripción:** El "slug" para `TenantS3Storage` se deriva de `empresa.nombre` reemplazando espacios/barras y truncando a 50 caracteres. No hay campo `slug` único en `Empresa`; dos empresas con el mismo nombre normalizado podrían compartir el prefijo en S3.
- **Riesgo:** colisión de rutas de archivos entre tenants, potencial fuga de documentos.
- **Recomendación:** Usar `empresa.id` o un `slug` único e inmutable para el prefijo de S3; validar unicidad.

## H-NUEVO-117 — `CustomLoginView` omite 2FA para IPs internas usando `REMOTE_ADDR`, que puede ser 127.0.0.1 en despliegues locales — MEDIO, ABIERTO
- **Ubicación:** `core/views/general.py:424-437`, `core/views/autenticacion_2fa.py:39-64`.
- **Descripción:** `CustomLoginView.form_valid` consulta `_ip_exenta_2fa`, que compara `request.META.get('REMOTE_ADDR')` contra `IPS_INTERNAS_2FA_BYPASS`. Si Nginx y Gunicorn están en el mismo host y `REMOTE_ADDR` es `127.0.0.1` para todo cliente, y el operador incluye `127.0.0.0/8`, cualquier cliente salta 2FA.
- **Riesgo:** bypass de 2FA por configuración de red; compromiso de cuentas con 2FA obligatorio.
- **Recomendación:** Documentar que `IPS_INTERNAS_2FA_BYPASS` solo debe usarse con NAT confiable y nunca con `127.0.0.0/8` en producción.

## H-NUEVO-118 — Código maestro de recuperación 2FA permite bypass global con un único secreto — MEDIO, ABIERTO
- **Ubicación:** `core/views/autenticacion_2fa.py:84-92`.
- **Descripción:** `_verificar_codigo_maestro` compara `hashlib.sha256(codigo)` contra `hashlib.sha256(PRISLAB_MASTER_RECOVERY_CODE)`. Si el código maestro se filtra o es débil, un atacante puede autenticarse como cualquier usuario con 2FA.
- **Riesgo:** bypass universal de 2FA con un único secreto.
- **Recomendación:** Vincular códigos de recuperación al usuario, rotar periódicamente, almacenar hash fuerte, aplicar rate-limit por cuenta.

## H-NUEVO-119 — `Usuario.totp_secret` se almacena en texto plano en la base de datos — ALTO, ABIERTO
- **Ubicación:** `core/models/base.py:388-393`.
- **Descripción:** El campo `totp_secret` es un `CharField` sin cifrado. Si la base de datos se ve comprometida, un atacante puede generar códigos TOTP y superar el 2FA de cualquier usuario. El flujo actual utiliza `DispositivoTOTP`, pero este campo heredado permanece expuesto.
- **Riesgo:** bypass total de 2FA tras exfiltración de DB.
- **Recomendación:** Cifrar `totp_secret` con `FERNET_KEY` o eliminar el campo si ya no se usa; auditar `seguridad.models.DispositivoTOTP` para confirmar cifrado.

## H-NUEVO-120 — `Usuario.sucursal` y `sucursal_id` asignan M2M sin verificar que la sucursal pertenezca a la empresa del usuario — BAJO/MEDIO, ABIERTO
- **Ubicación:** `core/models/base.py:443-482`.
- **Descripción:** Los setters `sucursal` y `sucursal_id` (compatibilidad) reciben un objeto o un `pk` y limpian/crean la relación M2M sin validar `sucursal.empresa == usuario.empresa`. Un administrador o API que reciba un `sucursal_id` de otro tenant creará la asignación.
- **Riesgo:** fuga de datos entre sucursales/tenants por asignaciones incorrectas.
- **Recomendación:** Validar `sucursal.empresa == usuario.empresa` en ambos setters y en `add_sucursal`.

## H-NUEVO-121 — `ConfiguracionModulos` almacena y verifica PINs de 4 dígitos, espacio reducido y sin limitación de intentos — MEDIO, ABIERTO
- **Ubicación:** `core/models/base.py:310-323, 249-258`.
- **Descripción:** `pin_precio_neto` y `pin_cancelacion_venta` son hashes de 4 dígitos. El espacio de claves es 10.000 y, aunque esté hasheado, es vulnerable a fuerza bruta offline. `verificar_pin_farmacia` no limita intentos ni invalida tras varios fallos.
- **Riesgo:** bypass de PINs de farmacia por fuerza bruta.
- **Recomendación:** Aumentar longitud mínima a 6-8 dígitos; rate-limit en vistas que verifican PIN; invalidar tras N intentos consecutivos.

## H-NUEVO-122 — `module_required` no concede bypass a superusuarios ni maneja ausencia de `ConfiguracionModulos` — BAJO, ABIERTO
- **Ubicación:** `core/decorators.py:325-378`.
- **Descripción:** `module_required` lee `request.user.empresa.configuracion_modulos` sin bypass para `is_superuser` y sin capturar de forma informativa `RelatedObjectDoesNotExist`. Un superusuario sin empresa o sin `ConfiguracionModulos` obtiene 403 si una vista usa este decorador directamente, aunque `FeatureFlagMiddleware` ya lo permita.
- **Riesgo:** inconsistencia de permisos y posible bloqueo de admin.
- **Recomendación:** Permitir `is_superuser`; validar empresa y mostrar mensaje claro; reutilizar lógica de `FeatureFlagMiddleware`.

## H-NUEVO-123 — `ingreso_magico` y `crear_admin_rescate` exponen backdoor en modo DEBUG con contraseña por defecto — BAJO/MEDIO, ABIERTO
- **Ubicación:** `core/views/general.py:185-241`.
- **Descripción:** Ambas vistas están bloqueadas en producción (`if not _s.DEBUG`). Si `DEBUG` se habilita accidentalmente, crean/loguean un superusuario con contraseña `admin123` por defecto (variable de entorno opcional).
- **Riesgo:** puerta trasera de emergencia con credenciales débiles.
- **Recomendación:** Eliminar estas vistas en el paquete de producción; si se necesitan, generar contraseña aleatoria y notificar por canal seguro; no confiar solo en `DEBUG`.

## H-NUEVO-124 — `rate_limit` decorador y `RateLimitMiddleware` tienen condición de carrera en el fallback `cache.set` — BAJO, ABIERTO
- **Ubicación:** `core/decorators.py:92-100`, `core/middleware/rate_limit.py:126-137`.
- **Descripción:** Ambos usan `cache.add` + `cache.incr`, y si `cache.incr` lanza `ValueError`, recurren a `cache.set(key, 1)`. En una ventana de conteo concurrente, dos requests pueden ejecutar `set` y reiniciar el contador, permitiendo un pico momentáneo superior al límite.
- **Riesgo:** límite de tasa parcialmente evadido en condición de carrera.
- **Recomendación:** No usar `set` como fallback; usar exclusivamente `cache.add` con `timeout` de la ventana o una operación atómica del backend de cache.

## H-NUEVO-125 — `log_frontend_error` acepta JSON arbitrario y loguea campos del cliente sin sanitización contra inyección de logs — BAJO, ABIERTO
- **Ubicación:** `core/views/general.py:247-308`.
- **Descripción:** Los campos del JSON (`message`, `source`, `stack`, `url`) se interpolan directamente en el mensaje de log. Si un cliente envía caracteres de control, newlines o secuencias que confundan al parser, puede generar log injection o falsificación de eventos.
- **Riesgo:** manipulación de logs de frontend; dificultad forense.
- **Recomendación:** Sanitizar/escapar caracteres no imprimibles y newlines; validar `source` y `url`; usar logging estructurado con JSON.

## H-NUEVO-126 — `core/rbac/permissions.py::require_sucursal_access` no valida `sucursal_id` en querystring ni body — BAJO, ABIERTO
- **Ubicación:** `core/rbac/permissions.py:388-422`.
- **Descripción:** El decorador lee `sucursal_id` exclusivamente de `kwargs` (URL). Vistas que reciben `sucursal_id` por `request.GET` o `request.POST` no quedan protegidas por este decorador.
- **Riesgo:** bypass de aislamiento por sucursal.
- **Recomendación:** Verificar también `request.GET` y `request.POST` o centralizar validación en la vista.

## H-NUEVO-127 — `AdminAccessMiddleware` no verifica `is_staff` antes de permitir acceso a `/admin/` — BAJO, ABIERTO
- **Ubicación:** `core/middleware/admin_access.py:26-45`.
- **Descripción:** Solo verifica el grupo `ADMIN_SISTEMA` y la IP. Si un usuario tiene el grupo pero no `is_staff`, el middleware lo deja pasar; Django admin le mostrará 403 posteriormente.
- **Riesgo:** bypass parcial (llega al admin aunque luego falle); el filtro de middleware debería requerir `is_staff`.
- **Recomendación:** Añadir `request.user.is_staff or request.user.is_superuser` a las condiciones de acceso.

## H-NUEVO-128 — `ActividadUsuarioMiddleware` escribe en base de datos en cada request — BAJO, ABIERTO
- **Ubicación:** `core/middleware/actividad_usuario.py:17-33`.
- **Descripción:** En cada request guarda `usuario.save(update_fields=['tiempo_actividad_inicio'])`. Esto genera una escritura por request, afectando rendimiento y generando contienda en la fila del usuario.
- **Riesgo:** DB lock, contienda, posible degradación de latencia.
- **Recomendación:** Actualizar solo cuando cambia el estado (inicio/nueva sesión); usar caché o campo `last_activity` menos frecuente.

## Confirmaciones positivas (core/ — middleware, tenant, RBAC, decoradores, vistas y modelos base) — CORRECTO
- `core/tenant.py` — `TenantQuerySet`/`TenantManager` filtran automáticamente por `empresa`/`sucursal`; `tenant_bypass` con context manager y auditoría; `strict_mode` y `shadow_mode` documentados; `tenant_required`/`tenant_protected_get` centralizan acceso.
- `core/middleware/empresa.py` — `EmpresaIdentityMiddleware` inyecta `request.empresa_actual`, `request.sucursal_actual` y llama `set_current_empresa`; limpia thread-local en `finally`; `X-Sucursal-ID` validado contra asignaciones M2M.
- `core/middleware/rate_limit.py` — uso de `cache.add`+`cache.incr` atómico; límite `/api/` aplica a todos los métodos; `Retry-After` en respuestas 429.
- `core/middleware/admin_access.py` — usa `REMOTE_ADDR` (no `X-Forwarded-For`) para validación de IP de `/admin/`.
- `core/middleware/seguridad.py` — `SessionTimeoutMiddleware` cierra sesión tras 8h de inactividad.
- `core/middleware/blindaje_expediente.py` — pre-save evita modificación de notas selladas y crea snapshots SHA256 por señal.
- `core/middleware/read_only.py` — kill-switch global `PRISLAB_READ_ONLY` bloquea escrituras salvo excepciones auditadas.
- `core/rbac/permissions.py` — mapa de permisos por rol, decoradores `require_permission`, `require_roles`, `deny_roles`, `require_sucursal_access`; verificación M2M de sucursales.
- `core/utils/tenant_strict.py` — `empresa_desde_request` no usa `Empresa.objects.first()`; requiere empresa del usuario o sesión explícita; `empresa_desde_management` requiere `--empresa-id`.
- `core/decorators.py` — `require_api_token` usa `secrets.compare_digest`; `check_payment_status` y `check_results_validated` filtran por `empresa`.
- `core/views/autenticacion_2fa.py` — rate limit de intentos fallidos (5 intentos, ventana 15 min), códigos backup, alerta CISO por código maestro.
- `core/models/base.py` — `Usuario` hereda `AbstractUser` con FK a `Empresa` y M2M a `Sucursal`; `ConfiguracionModulos` hereda de `TenantModel` y encripta PINs en `save`; `Empresa` encripta `byok_gemini_api_key_enc` y `drive_client_config_enc` con Fernet.

## Bloque 18 — core/models/ (modelos de negocio, clínica, laboratorio, ventas, finanzas, RRHH, operaciones, forense, IA, blindaje) — NUEVO

### H-NUEVO-129: Modelos críticos de `core/models` no heredan `TenantModel`/`TenantManager`, subvirtiendo el aislamiento multi-tenant
- **Archivos afectados principales**: `core/models/clinico.py`, `core/models/laboratorio.py`, `core/models/ventas.py`, `core/models/finanzas.py`, `core/models/rrhh.py`, `core/models/operaciones.py`, `core/models/catalogos.py`, `core/models/forense.py`, `core/models/ia_config.py`, `core/models/pris.py`, `core/models/expediente_blindaje.py`, `core/models/bienestar_staff.py`, `core/models/base.py`.
- **Severidad**: Crítica.
- **Hallazgo**: Decenas de modelos que contienen datos clínicos, financieros, de nómina, operativos, forenses, de IA y de recursos humanos definen `empresa`/`sucursal` como FK pero heredan `models.Model` y usan `objects = models.Manager()` (o `AppendOnlyManager` en `AuditLog`/`ForenseAcceso`, que tampoco filtra por tenant). Esto significa que `TenantQuerySet`/`TenantManager` de `core/tenant.py` no filtra automáticamente sus queries; el aislamiento depende de que cada vista/endpoint/admin recuerde agregar `filter(empresa=...)` manualmente. Cualquier omisión permite listar, editar o borrar registros de otro tenant.
- **Evidencia**: `Select-String '^class \w+\((TenantModel|models\.Model)\)'` sobre `core/models/*.py` muestra que solo `Paciente` (pacientes.py:17), `Producto` (catalogos.py:18), `Lote` (catalogos.py:158), `OrdenDeServicio` (laboratorio.py:384), `Venta` (ventas.py:262) y `PagoOrden` (ventas.py:524) heredan `TenantModel`; todas las demás clases con `empresa` son `models.Model`. Ejemplos críticos:
  - Clínica: `CitaMedica` (clinico.py:19), `HistoriaClinica` (78), `SignosVitales` (155), `ConsultaMedica` (218), `CertificadoMedico` (331), `NotaClinicaSOAP` (394), `PlantillaNotaClinica` (431), `Antecedente` (465), `FirmaDigital` (491), `AudioConsulta` (512), `EstudioImagen` (559), `ImagenDetalle` (642), `PlantillaEstudioImagen` (671), `HistorialCambiosConsulta` (703), `LogAccesoExpediente` (741), `ConsentimientoInformado` (779), `RegistroAuditoriaConsentimiento` (815).
  - Laboratorio: `TomaMuestra` (laboratorio.py:19), `AudioTomaMuestra` (60), `EnvioMaquila` (106), `BitacoraTemperatura` (142), `MantenimientoEquipo` (158), `HistorialResultados` (178), `ResultadoParametro` (216), `DetalleOrden` (619), `PreOrdenLaboratorio` (673), `DetallePreOrden` (703).
  - Ventas/finanzas: `Receta` (ventas.py:28), `RecetaItem` (140), `DemandaInsatisfecha` (172), `DispensacionReceta` (204), `DetalleVenta` (360), `DetalleVentaLote` (378), `DevolucionVenta` (412), `Pago` (489), `Gasto` (612), `AjusteInventario` (626), `GastoCaja` (651), `MovimientoCaja` (712), `GastoOperativo` (826), `FacturaSAT` (858), `SalesReturn` (893), `MetaVenta` (936), `CuentaPorCobrar` (958), `PagoCuentaPorCobrar` (1016), `NotaCredito` (1039); `PoliticaLimitesCaja` (finanzas.py:13), `GastoCajaEndurecido` (105), `CierreDiaConsolidado` (217), `TicketInvestigacionCaja` (340).
  - RRHH: `Empleado` (rrhh.py:15), `Bitacora39A` (65), `EvaluacionDesempeno` (171), `DetalleEvaluacion` (250), `PlanDesarrollo` (267), `RegistroAsistencia` (300), `PeriodoNomina` (346), `ReciboNomina` (391), `HorarioTrabajo` (462), `IncidenciaAsistencia` (493).
  - Operaciones/forense/IA: `AuditLog` (operaciones.py:17), `BackupRegistro` (75), `MensajeInterno` (190), `SolicitudAutorizacion` (219), `IncidenciaOperativa` (262), `BuzonQuejas` (310), `PushSubscription` (415), `VoiceAuditLog` (451), `NotificacionSistema` (535), `BitacoraEntregaResultados` (647), `ConversacionBienestar` (720), `AlertaBienestar` (755), `DocumentoCapacitacion` (805), `CapsulaSabiduria` (926); `UsoRecursosIA` (ia_config.py:13), `ReglaLocalIA` (ia_config.py:79); `AccionPRIS` (pris.py:11); `ForenseAcceso` (forense.py:13); `EvaluacionNOM035` (bienestar_staff.py:47), `DiarioEmocionalStaff` (95), `SesionCoachingStaff` (133), `AlertaBurnout` (182), `ProgramaCapacitacion` (221); `AuditoriaModel` (base.py:40), `DocumentoConocimiento` (524), `DatosFiscales` (575), `ControlCalidad` (601), `RutaLogistica` (624), `Usuario_Sucursal` (647).
- **Riesgo**: Fuga multi-tenant de confidencialidad e integridad (ICR/IMC), datos clínicos, financieros y de nómina; incumplimiento de NOM-024-SSA3-2012, HIPAA y LFPDPPP.
- **Recomendación**: Migrar todas las clases de negocio con `empresa` a `TenantModel` (o asignar `objects = TenantManager()` con `objects_all = models.Manager()` para admin global). Auditar y eliminar queries manuales que no filtren por empresa. Priorizar modelos clínicos, financieros y forenses.

### H-NUEVO-130: `ExpedienteNotaSHA` y `HashRaizDiario` no son append-only ni tenant-scoped; anclaje forense global
- **Archivo**: `core/models/expediente_blindaje.py`.
- **Líneas**: `ExpedienteNotaSHA` (41-241), `HashRaizDiario` (825-973).
- **Severidad**: Crítica.
- **Hallazgo**: `ExpedienteNotaSHA` es `models.Model` (no `TenantModel`) y, aunque crea un hash SHA-256 al insertar, no impide actualizaciones ni borrados: `save()` recalcula el hash solo si `not self.pk`; una modificación posterior deja el hash obsoleto y `verificar_integridad()` falla silenciosamente. `HashRaizDiario` no tiene campo `empresa`; su `verificar_integridad_anclaje()` consulta `ExpedienteNotaSHA.objects.filter(timestamp_creacion__range=..., firmado_con_pin=True)` de **todos los tenants**, rompiendo el aislamiento del anclaje diario.
- **Riesgo**: Ruptura de cadena forense sin detección; pérdida de evidencia legal NOM-004; fuga cross-tenant en trazabilidad.
- **Recomendación**: Convertir `ExpedienteNotaSHA` a `TenantModel` + `AppendOnlyManager`, y aplicar `reject_append_only_mutation`. Agregar `empresa` a `HashRaizDiario` y filtrar `ExpedienteNotaSHA` por empresa en `verificar_integridad_anclaje()`.

### H-NUEVO-131: Archivos clínicos, forenses y de recetas se almacenan con Google Drive heredado en lugar de S3 multi-tenant
- **Archivos**: `core/models/clinico.py`, `core/models/laboratorio.py`, `core/models/ventas.py`.
- **Líneas**: `AudioConsulta.audio_archivo` (clinico.py:515-521), `ImagenDetalle.imagen` (clinico.py:646-650), `Receta.medico_firma_digital` (ventas.py:56-64), `ResultadoParametro.imagen_microscopio` (laboratorio.py:287-295).
- **Severidad**: Alta.
- **Hallazgo**: Estos `FileField`/`ImageField` usan `storage=get_google_drive_storage` y `upload_to='core.utils.paths.generar_ruta_drive...'`. `config/storage_backends.py` comenta que Google Drive es histórico/deshabilitado y define `TenantS3Storage` para Vultr S3 con prefijo `empresa_slug`. Los campos críticos no aprovechan el aislamiento ni la disponibilidad de S3.
- **Riesgo**: Pérdida de evidencia clínica/firma si Drive se desactiva; falta de aislamiento de archivos por tenant; incumplimiento NOM-004/HIPAA.
- **Recomendación**: Migrar todos los `FileField`/`ImageField` clínicos a `TenantS3Storage` o `default_storage` configurado con tenant; eliminar `get_google_drive_storage` de modelos clínicos.

### H-NUEVO-132: Generación de folios y tokens no incluye empresa y depende de conteos no atómicos
- **Archivos**: `core/models/ventas.py`, `core/models/clinico.py`, `core/models/laboratorio.py`, `core/models/expediente_blindaje.py`.
- **Líneas**: `Receta.folio_receta` (ventas.py:123-128), `Venta.folio_operacion`/`linea_captura` (ventas.py:352-357), `CertificadoMedico.folio_certificado` (clinico.py:375-388), `OrdenDeServicio.folio_orden` (laboratorio.py:597-602), `NotaClinicaSellar.folio_unico` (expediente_blindaje.py:494-506).
- **Severidad**: Media/Alta.
- **Hallazgo**: `Receta.save()` cuenta `Receta.objects.filter(folio_receta__startswith='REC-YYYYMM-')` sin filtrar por empresa y `Receta.empresa` es nullable. `Venta.linea_captura` genera `uuid.uuid4().hex[:12].upper()` con `unique=True` global. Otros folios usan conteos `count()` +1 sin `select_for_update()` ni transacción atómica, proclives a condiciones de carrera bajo carga concurrente.
- **Riesgo**: Violación de constraints `unique` por folios duplicados; colisiones cross-tenant; truncamiento de UUID reduce espacio de claves.
- **Recomendación**: Envolver generación de folios en `transaction.atomic()` + `select_for_update()`; incluir `empresa_id` en prefijos y constraints; usar UUID completo para `linea_captura` y agregar prefijo tenant.

### H-NUEVO-133: `CatalogoCIE10` y `HashRaizDiario` son catálogos/anchajes globales sin `empresa`
- **Archivo**: `core/models/expediente_blindaje.py`.
- **Líneas**: `CatalogoCIE10` (755-818), `HashRaizDiario` (825-973).
- **Severidad**: Media.
- **Hallazgo**: `CatalogoCIE10` define `codigo` como `primary_key=True` y carece de `empresa`; una edición desde admin afecta a todos los tenants. `HashRaizDiario` tampoco tiene `empresa`, por lo que su hash raíz diario agrega hashes de todos los tenants.
- **Riesgo**: Integridad del catálogo diagnóstico; fuga/alteración cross-tenant en evidencia forense.
- **Recomendación**: Agregar `empresa` a `HashRaizDiario` y calcular una raíz por tenant. Proteger `CatalogoCIE10` con permisos de superusuario o clonar por empresa si se requiere personalización.

### H-NUEVO-134: `Receta` y `RecetaItem` no son `TenantModel`, `empresa` es nullable y folio es global
- **Archivo**: `core/models/ventas.py`.
- **Líneas**: `Receta` (28-138), `RecetaItem` (140-165).
- **Severidad**: Alta.
- **Hallazgo**: `Receta` hereda `models.Model`; `empresa` es `ForeignKey(..., null=True, blank=True)` y `Receta.save()` genera `folio_receta` con conteo global sin filtrar por empresa. `RecetaItem` carece de `empresa`. Al vincularse con `Venta`, `OrdenDeServicio` y `DispensacionReceta`, la falta de scoping automático es un vector de fuga directo.
- **Riesgo**: Fuga de recetas entre tenants; duplicación de folios; trazabilidad COFEPRIS comprometida.
- **Recomendación**: Hacer `Receta` y `RecetaItem` `TenantModel`; eliminar `null=True` de `empresa` en `Receta`; filtrar folio por empresa en `save()`.

### H-NUEVO-135: `Medico.lab_validation_pin_hash` y `ConfiguracionModulos` PIN se almacenan como SHA-256 sin sal y con poca entropía
- **Archivos**: `core/models/catalogos.py`, `core/models/base.py`.
- **Líneas**: `Medico.lab_validation_pin_hash` (catalogos.py:256-261), `ConfiguracionModulos` (base.py:261-330).
- **Severidad**: Media.
- **Hallazgo**: El PIN de validación del médico se guarda como `SHA256(pin_limpio)` (64 hex, sin sal). `NotaClinicaSellar._validar_pin_medico` (expediente_blindaje.py:577-594) compara hashes hex directamente. El PIN de módulos de `ConfiguracionModulos` también es corto (4 dígitos). Un ataque offline por fuerza bruta es factible si se exfiltra la base.
- **Riesgo**: Falsificación de firma médica; incumplimiento de NOM-004/FES.
- **Recomendación**: Usar `bcrypt`/`argon2` con sal para `lab_validation_pin_hash`; exigir longitud mínima > 6; limitar intentos en `sellar_con_pin`.

### H-NUEVO-136: `AuditLog` y `ForenseAcceso` son append-only pero no `TenantModel`
- **Archivos**: `core/models/operaciones.py`, `core/models/forense.py`.
- **Líneas**: `AuditLog` (operaciones.py:17-70), `ForenseAcceso` (forense.py:13-93).
- **Severidad**: Media.
- **Hallazgo**: Ambos usan `AppendOnlyManager` y `reject_append_only_mutation`, lo cual es positivo, pero `AppendOnlyManager` no hereda de `TenantManager`; por tanto, las queries no se filtran automáticamente por `empresa`. `AuditLog.datos_nuevos/datos_anteriores` es `JSONField` libre y podría incluir PII sin normalizar.
- **Riesgo**: Lectura de logs de auditoría o forenses de otro tenant si la vista no filtra; fuga de PII en logs.
- **Recomendación**: Crear `TenantAppendOnlyManager` que combine `TenantQuerySet` con `AppendOnlyQuerySet`; aplicarlo a `AuditLog` y `ForenseAcceso`. Normalizar/mascarar PII en `datos_nuevos`.
