# Acceso y Deploy Operativo VPS

Estado: procedimiento vigente; ultima comprobacion 2026-07-27

## Corte de verificacion 2026-07-24

### Corte vigente posterior a `8a0e3e8`

- La revision local `8a0e3e80a73a1e478ce015e6d4c050b6cb84af73` fue desplegada directamente al VPS, sin GitHub ni workflow remoto.
- `/opt/prislab/app/DEPLOYED_REVISION` confirma `8a0e3e80a73a1e478ce015e6d4c050b6cb84af73`.
- Migraciones aplicadas: `ia.0004_cotizacionocr_empresa_tenant` y `laboratorio.0017_noconformidad_noconformidadevento_rondaeqa_and_more`; estaticos: `0 static files copied`, `864 post-processed`.
- Servicios `prislab-gunicorn`, `prislab-celery` y `prislab-celerybeat`: `active`; `/health/`: `status=ok`, `database=ok`, `cache=ok`.
- Smoke HTTP posterior: `/live/`, `/ready/`, `/health/` y `/login/` devolvieron HTTP 200; `/farmacia/` y `/laboratorio/` devolvieron HTTP 302 hacia `/login/` como corresponde sin sesion.
- Las migraciones `ia.0004` y `laboratorio.0017` aparecen aplicadas (`[X]`) en produccion.

**Estado real:** el despliegue local esta confirmado y la infraestructura publica responde correctamente. La matriz E2E autenticada de Farmacia y Laboratorio permanece como auditoria funcional separada.

### Corte historico, no vigente

La documentacion del procedimiento existe y se conserva. El siguiente bloque se mantiene solo como trazabilidad historica y no acredita el estado actual:

- El codigo corregido de seguridad quedo publicado en `10d1156`, en `release/v1.0-local`.
- El workflow `PRISLAB Deploy to VPS` se disparo como run `30120009575`, pero fallo en `Validate deploy secrets`.
- El workflow no llego a `Setup SSH`, `Deploy on VPS` ni al smoke test; la automatizacion sigue pendiente de secretos.
- El run fallo porque falta `DEPLOY_KNOWN_HOSTS`, requisito agregado para impedir SSH sin verificacion de host.
- El despliegue manual posterior corrigio la propiedad del checkout remoto y dejo la VPS en `8194e85`.
- Evidencia: `prislab-gunicorn`, `prislab-celery` y `prislab-celerybeat` activos; `/live/`, `/ready/` y `/health/` publicos devuelven HTTP 200.

Bloqueador actual: configurar en el Environment `production` de GitHub `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` y `DEPLOY_KNOWN_HOSTS`. Las variables opcionales son `DEPLOY_ROOT_DIR=/opt/prislab`, `DEPLOY_APP_DIR=/opt/prislab/app` y `DEPLOY_APP_USER=prislab`.

El deploy manual de `8194e85` queda como evidencia historica. No debe usarse para afirmar que `551eaaa` o posteriores estan desplegados.

### Procedimiento vigente de despliegue local

La ruta vigente es local y reproducible:

```powershell
cd C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master
.\scripts\deploy_local_to_vps.ps1 -User root
```

No se usa GitHub para transferir el codigo ni para decidir que revision llega a produccion.

## Objetivo

Este documento define:

- quien puede ejecutar comandos reales en el VPS
- como desplegar PRISLAB sin ambiguedad
- que salida debe capturarse
- como validar que produccion si quedo actualizada

## Regla operativa clave

Documentar el procedimiento no equivale a tener acceso remoto activo.

- Codex puede dejar codigo, commits, push y documentacion listos
- Claude puede auditar navegador y revisar flujos funcionales
- solo quien tenga una sesion real al VPS puede ejecutar deploy

## Quien puede ejecutar realmente en el VPS

### Humano operador

Puede ejecutar deploy real si tiene:

- consola web de Vultr abierta, o
- acceso SSH funcional desde su maquina

Hoy, esta es la via segura y confirmada.

### Codex

Puede preparar:

- commits
- push
- comandos exactos
- checklist de validacion

Solo puede ejecutar realmente en VPS si el entorno de esta sesion tiene una via remota viva hacia el servidor. Eso no debe asumirse.

### Claude

No tiene acceso SSH automatico al VPS en esta sesion.

Puede:

- auditar produccion desde navegador
- validar UI y flujos
- detectar regresiones funcionales

No puede:

- hacer deploy por si mismo
- correr comandos remotos solo por existir un documento o una llave descrita en texto

## Servidor actual

- proveedor: Vultr
- IP: `216.238.89.243`
- dominio productivo: `https://prislab.labcorecloud.com`
- rama de despliegue: `release/v1.0-local`

## Estado actual del repositorio

Commits historicos ya preparados y empujados:

- `d159850` - Bloque A - Claude
- `5650acb` - Bloque B - Codex
- `e04ca4b` - Bloque C - Documentacion

El listado anterior corresponde a un corte historico. Para el corte actual, el commit fuente que debe desplegarse es `551eaaa` o posterior. No existe evidencia vigente de que ese commit este en VPS.

## Procedimiento exacto de deploy

Abrir consola web de Vultr o una sesion SSH real al VPS y ejecutar:

```bash
cd /opt/prislab
git pull origin release/v1.0-local
systemctl restart prislab-gunicorn
systemctl restart prislab-celery
systemctl restart prislab-celerybeat
systemctl reload nginx
systemctl is-active prislab-gunicorn
systemctl is-active prislab-celery
systemctl is-active prislab-celerybeat
curl -I https://prislab.labcorecloud.com
```

## Caso real detectado en esta VPS

En esta instalacion productiva se detecto que:

- el codigo vive en `/opt/prislab/app`
- inicialmente no existia `.git` dentro de esa carpeta
- por lo tanto `git pull` en `/opt/prislab` o `/opt/prislab/app` fallaba
- fue necesario inicializar Git y apuntarlo al remoto
- tambien fue necesario corregir ownership para que `prislab` pudiera aplicar el arbol descargado

Secuencia real que si funciono en este servidor:

```bash
sudo -u prislab git -C /opt/prislab/app init
sudo -u prislab git -C /opt/prislab/app remote add origin https://github.com/primerosaludlaboratorio-star/saasprislab.git
sudo -u prislab git -C /opt/prislab/app fetch --depth 1 origin release/v1.0-local
chown -R prislab:prislab /opt/prislab/app
sudo -u prislab git -C /opt/prislab/app reset --hard FETCH_HEAD
systemctl restart prislab-gunicorn
systemctl restart prislab-celery
systemctl restart prislab-celerybeat
systemctl reload nginx
```

Resultado real confirmado:

- `HEAD` quedo en `e04ca4b`
- `prislab-gunicorn`: `active`
- `prislab-celery`: `active`
- `https://prislab.labcorecloud.com`: `HTTP/2 200`

## Si `git pull` dice "not a git repository"

No insistir en `/opt/prislab`.

Verificar primero:

```bash
ls -la /opt/prislab
ls -la /opt/prislab/app
ls -la /opt/prislab/app/.git
```

Si `/opt/prislab/app/.git` no existe, usar el procedimiento del bloque "Caso real detectado en esta VPS".

## Si `reset --hard` falla con `Permission denied`

Ejecutar:

```bash
chown -R prislab:prislab /opt/prislab/app
sudo -u prislab git -C /opt/prislab/app reset --hard FETCH_HEAD
```

No continuar con auditoria funcional hasta que ese `reset --hard` termine sin error.

## Salida que se debe guardar

Antes de declarar deploy exitoso, hay que pegar o guardar:

- salida completa de `git pull`
- salida de los 3 comandos `systemctl is-active`
- salida de `curl -I https://prislab.labcorecloud.com`

## Criterio de exito

El deploy se considera correcto solo si:

- `git pull` no da error
- `prislab-gunicorn` responde `active`
- `prislab-celery` responde `active`
- `prislab-celerybeat` responde `active`
- `curl -I` responde `200`, o `302` legitimo hacia login

## Despues del deploy

Solo despues de eso Claude debe arrancar auditoria funcional en produccion.

Auditoria inmediata recomendada:

1. login
2. consultorio: paciente nuevo, agenda, nueva consulta, guardado final con `folio_consulta`
3. laboratorio: recepcion, orden, cobro, bitacora
4. farmacia: PDV, venta, devolucion, inventario
5. seguridad: accesos por rol y rutas sensibles

## Si no hay SSH

Si SSH falla o no esta disponible:

1. entrar al panel Vultr
2. abrir la consola web del servidor
3. esperar prompt `root@vultr:~#`
4. correr manualmente los comandos del bloque de deploy

## Mensaje para Claude despues del deploy

Usar este texto:

```text
Deploy confirmado en VPS.
Se ejecutó git pull origin release/v1.0-local y restart/reload de prislab-gunicorn, prislab-celery, prislab-celerybeat y nginx.
Servicios activos.
Puedes iniciar ya la auditoría funcional real sobre https://prislab.labcorecloud.com con los usuarios de auditoría.
```

## Nota de control

Si alguien modifica el procedimiento, el alcance de acceso o la rama de despliegue, debe actualizar tambien:

- `CHECKLIST_CONTROL_PRISLAB.md`
- `REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md`
- este documento
