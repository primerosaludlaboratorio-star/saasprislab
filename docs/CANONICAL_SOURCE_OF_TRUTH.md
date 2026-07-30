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
- Última revisión local: `4ac7903` (`fix(security): consolidate middleware and atomic rate limits`). La revisión desplegada se actualizará después de verificar este despliegue.
- Copias alternas: apartadas como archivos de resguardo con fecha
  `20260729`.
- Sincronización remota verificada el 2026-07-29: el remoto visible permanece
  en `8a0e3e8`, mientras el checkout canónico está en `4ac7903` y adelante
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

## Qué no se debe hacer

- No editar simultáneamente Desktop y `.copilot`.
- No tomar una auditoría externa como fuente de código si usa otra ruta.
- No copiar documentos con el mismo nombre desde otra carpeta sin comparar
  contenido y fecha.
- No borrar una corrección sin probarla y registrar su razón.
