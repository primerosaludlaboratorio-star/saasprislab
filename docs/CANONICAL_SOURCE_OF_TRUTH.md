# Fuente única de verdad PRISLAB

**Vigencia:** 2026-07-29  
**Rama operativa:** `release/v1.0-local`

## Checkout canónico

La única ruta activa para editar, probar, versionar y desplegar PRISLAB es:

```text
C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master
```

El repositorio contiene el historial Git operativo y su remoto `origin`.
Ninguna copia bajo `.copilot`, `outputs`, capturas, ZIP o carpetas legacy es
fuente de código. Las copias antiguas se conservan únicamente como archivo de
resguardo fuera de las rutas activas.

## Despliegue canónico

Desde la raíz del checkout canónico:

```powershell
.\scripts\deploy_local_to_vps.ps1 -User root
```

El proceso crea un artefacto local, lo transfiere al VPS, ejecuta migraciones,
static, reinicia Gunicorn/Celery/Celery Beat, recarga Nginx y verifica
`https://prislab.labcorecloud.com/health/`.

No se debe desplegar desde un checkout alterno, desde GitHub Actions ni desde
una extracción ZIP sin aprobación explícita y evidencia equivalente.

## Regla de alineación

Antes de editar:

1. Confirmar la ruta con `git rev-parse --show-toplevel`.
2. Confirmar rama y `HEAD`.
3. Confirmar `git status`.
4. Ejecutar pruebas y `manage.py check`.
5. Editar únicamente este checkout.
6. Documentar el resultado en `docs/ai_coordination/` y
   `CHECKLIST_CONTROL_PRISLAB.md`.
7. Desplegar únicamente después de pruebas verdes.
8. Verificar producción y registrar la revisión desplegada.

## Estado de la consolidación

- Checkout canónico: activo y limpio.
- Última revisión local y desplegada: `3807a0df9fe2bbe7324b9cfe79943b12126de620` (`fix(lims): bind HL7 integration to tenant credentials`).
- Copias alternas: apartadas como archivos de resguardo con fecha
  `20260729`.
- Sincronización remota verificada el 2026-07-29: el remoto visible permanece
  en `8a0e3e8`, mientras el checkout canónico está en `2121375` y adelante
  respecto del remoto. El `push` no terminó desde esta máquina por falta de una
  sesión Git autenticada disponible; por tanto GitHub no se declara como fuente
  activa ni sincronizada. El despliegue operativo se realiza localmente desde
  este checkout y se registra por revisión.

## Cierre H-013 y limpieza de legacy

La revisión `4ac7903` es la fuente canónica para la consolidación de middleware:

- `RateLimitMiddleware` usa contador atómico por ventana fija y limita todos los
  métodos de `/api/`, con `Retry-After` en `429`.
- Se eliminaron `admin_access_restrict.py` y `LogAccesoExpedienteMiddleware`
  como restos sin referencias runtime; los modelos de auditoría que sí usa el
  sistema se conservan.
- `TenantSubdomainMiddleware` permanece activo y documentado como parte de la
  cadena real.
- La evidencia automatizada es la suite real disponible de rate limit, tenant,
  Sentinel y drivers de middleware, además de `check`, migraciones y compilación.

## Limpieza de código muerto

- Eliminados `core/services/ai_medico_backup.py` y `marketing/views_legacy.py`.
- La búsqueda completa de imports activos no encontró referencias a ninguno.
- `marketing/urls.py` usa exclusivamente `marketing.views` y
  `marketing.views_tracking`.

## Auditoría exhaustiva: cierres desplegados

- `core.0099` corrigió la generación y encadenamiento SHA de snapshots clínicos;
  la verificación productiva transaccional confirmó dos versiones íntegras y
  rollback sin dejar datos (`PROD_BLINDAJE_ROLLBACK_OK 1 2`).
- `core.0100` aplicó validación de archivos de soporte de RH y eliminó el
  default CLABE de prueba.
- Los reportes financieros activos toleran fechas inválidas sin 500 y tienen
  prueba focalizada.
- `require_sucursal_access` falla cerrado ante identificadores no numéricos.
- Producción verificada: `https://prislab.labcorecloud.com/health/` HTTP 200,
  base de datos y caché OK; Gunicorn, Celery y Celery Beat activos.
- Aislamiento Django Admin corregido: los 184 registros activos están bajo
  `TenantScopedAdmin` y la verificación productiva quedó en verde.
- Aislamiento WebSocket del walkie-talkie corregido: los grupos incluyen el
  `empresa_id`, las salas se validan y los usuarios sin tenant son rechazados.
- Verificación productiva del aislamiento WebSocket: revisión
  `1f091db2f36f564a88373dcdae7d19910aaffdd3` desplegada; health HTTP 200 y
  Gunicorn/Celery/Celery Beat activos.
- H-NUEVO-15 corregido: Sentinel ya no puede reiniciar Gunicorn desde una
  request pública; la revisión `c733c8d6d86addf375956e966afda69866aea4ce`
  quedó desplegada con health HTTP 200 y servicios activos.
- H-NUEVO-16 corregido: el receptor HL7 resuelve el tenant solo por IP o
  credencial ligada en servidor; la revisión `3807a0df9fe2bbe7324b9cfe79943b12126de620`
  quedó desplegada con migraciones al día, health HTTP 200 y servicios activos.
- Verificación productiva del Admin: 184 registros, cero administradores sin
  mixin, cero fallos de consulta; cinco catálogos globales fallan cerrado como
  estaba diseñado.
- El script `migracion_ia.ps1` ya no lista el respaldo eliminado.
- Inventarios operativos actualizados; los reportes históricos conservan su
  carácter de evidencia y no son fuente de código.

## Cierre H-NUEVO-01 y H-NUEVO-02

- `ConfiguracionModulos` ya no guarda PINs de farmacia en texto plano.
  `core.0098_hash_farmacia_pins` migra los valores existentes a hash Django y
  los tres consumidores usan verificación centralizada.
- `EncryptedTextField` falla cerrado ante ausencia o fallo de Fernet; no puede
  guardar texto plano como degradación silenciosa.
- Pruebas de seguridad sensible y regresión de PIN de farmacia aprobadas.

## Qué no se debe hacer

- No editar simultáneamente Desktop y `.copilot`.
- No tomar una auditoría externa como fuente de código si usa otra ruta.
- No copiar documentos con el mismo nombre desde otra carpeta sin comparar
  contenido y fecha.
- No borrar una corrección sin probarla y registrar su razón.
