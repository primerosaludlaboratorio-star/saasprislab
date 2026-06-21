# Acceso y Deploy Operativo VPS

Estado: vigente al 2026-06-20

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

Commits ya preparados y empujados:

- `d159850` - Bloque A - Claude
- `5650acb` - Bloque B - Codex
- `e04ca4b` - Bloque C - Documentacion

Estos cambios ya fueron empujados a GitHub y estan listos para bajarse al VPS con `git pull`.

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
