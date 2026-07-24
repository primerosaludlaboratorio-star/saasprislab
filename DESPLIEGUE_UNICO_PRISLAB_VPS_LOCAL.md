# DESPLIEGUE UNICO PRISLAB VPS LOCAL

Estado: procedimiento unico y vigente
Nombre operativo: `DESPLIEGUE_UNICO_PRISLAB_VPS_LOCAL`
Ultima verificacion: 2026-07-24

## Regla principal

PRISLAB se despliega **unicamente desde el checkout local** usando:

```powershell
.\scripts\deploy_local_to_vps.ps1 -User root
```

No se usa GitHub, GitHub Actions, `git pull`, Cloud Run, Railway, Nixpacks ni copias ZIP manuales para publicar codigo en esta produccion.

## Datos de acceso operativo

Estos son los datos no secretos necesarios para ingresar al servidor:

| Dato | Valor |
|---|---|
| Proveedor | Vultr VPS |
| Host/IP | `216.238.89.243` |
| Usuario SSH autorizado | `root` |
| Clave privada local | `C:\Users\jonil\.ssh\id_ed25519` |
| Directorio de aplicacion | `/opt/prislab/app` |
| Directorio de releases | `/opt/prislab/releases/<revision>` |
| Dominio productivo | `https://prislab.labcorecloud.com` |
| Health check | `https://prislab.labcorecloud.com/health/` |
| Rama local de trabajo | `release/v1.0-local` |

La clave privada **no se documenta, no se copia al repositorio y no se imprime**. Si la clave no existe o no esta autorizada, el despliegue se detiene; no se debe sustituir por credenciales improvisadas.

## Comando unico

Ejecutar desde el repo anidado, no desde la carpeta contenedora:

```powershell
cd C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master
git branch --show-current
git status --short
.\scripts\deploy_local_to_vps.ps1 -User root
```

La rama debe ser `release/v1.0-local` y el working tree debe estar limpio antes de publicar.

## Que hace el comando

1. Confirma SSH contra `root@216.238.89.243` con `StrictHostKeyChecking=yes`.
2. Toma la revision exacta del checkout local.
3. Empaqueta codigo local sin `.git`, `.env`, `.venv`, media, estaticos generados ni logs.
4. Transfiere el artefacto directamente por SCP al VPS.
5. Sincroniza codigo en `/opt/prislab/app` y conserva `.env`, `.venv`, media, estaticos y logs del servidor.
6. Ejecuta migraciones y `collectstatic`.
7. Reinicia Gunicorn, Celery y Celery Beat; recarga Nginx.
8. Escribe la revision en `/opt/prislab/app/DEPLOYED_REVISION`.
9. Comprueba `/health/` y exige respuesta HTTP 200.

## Criterio de despliegue correcto

No se considera publicado hasta confirmar todos estos puntos:

- `DEPLOYED_REVISION` coincide con el `HEAD` local desplegado.
- Migraciones terminan con salida correcta.
- `prislab-gunicorn`, `prislab-celery` y `prislab-celerybeat` aparecen `active`.
- `/health/` devuelve estado `ok`, base de datos `ok` y cache `ok`.
- La interfaz productiva carga y se prueba como usuario humano.
- No hay errores ni warnings nuevos en consola del navegador.

## Comandos de comprobacion remota

```powershell
ssh -i "$HOME\.ssh\id_ed25519" -o StrictHostKeyChecking=yes root@216.238.89.243 "cat /opt/prislab/app/DEPLOYED_REVISION; systemctl is-active prislab-gunicorn prislab-celery prislab-celerybeat"
Invoke-WebRequest https://prislab.labcorecloud.com/health/
```

## Prohibiciones operativas

- No publicar desde otra carpeta o desde una extraccion ZIP.
- No usar otra rama para produccion.
- No hacer `git pull` en la VPS como mecanismo de despliegue.
- No sobrescribir `.env` productivo durante la transferencia.
- No eliminar media, estaticos persistentes, logs ni releases anteriores sin procedimiento separado.
- No declarar exito solo porque SSH conecto: siempre se requiere revision, servicios, health check y prueba humana.

## Evidencia vigente

El 2026-07-24 se desplego localmente la revision `325ee39c397edbb7ba2f32fe13842bb88d9e4527`. Migraciones, estaticos, servicios y health check fueron correctos. La interfaz de PRIS se verifico en produccion con escenarios de orientacion operativa, confirmacion humana, seguridad y criterio clinico.

## Voz neural de PRIS

- La revision funcional `14d45d0` activa Google Cloud TTS con `es-US-Neural2-A`, voz neural latinoamericana calida.
- La credencial se toma exclusivamente de `GOOGLE_APPLICATION_CREDENTIALS` en el servidor y nunca se envia al navegador.
- El audio es efimero y no se almacena.
- Si TTS no esta disponible, PRIS usa automaticamente la voz local mejorada del navegador.
- Verificacion productiva: TTS devolvio audio MP3 real de `24960` bytes; la interfaz respondio y el navegador reporto cero errores.
