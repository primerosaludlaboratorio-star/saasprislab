# Diagnostico de acceso VPS - 2026-09-13

## Alcance

Se verifico el acceso administrativo al VPS de PRISLAB mediante la API de Vultr y la consola web. No se modificaron servidores, contrasenas, usuarios, datos ni reglas de red.

## Evidencia verificada

- Instancia: `909ac8c9-0183-4e82-964d-c76cf429d2a7`
- IP publica: `216.238.89.243`
- Region: `mex` (Ciudad de Mexico)
- Sistema operativo: Ubuntu 26.04 LTS x64
- Estado Vultr: `active`
- Estado de energia: `running`
- Estado del servidor: `ok`
- Firewall administrado de Vultr: ninguno asignado
- Claves SSH administradas por Vultr: ninguna asociada
- Consola web noVNC: disponible

## Incidencia observada

La conexion SSH desde PowerShell a `216.238.89.243:22` devolvio `Connection timed out`. En una prueba anterior el servidor permitio acceso por consola web como `root`, por lo que el VPS esta accesible fuera del puerto SSH.

El timeout no demuestra aun una causa concreta. Las causas probables son el servicio `sshd`, el firewall local (`ufw`/nftables), una regla de red temporal o una restriccion de escucha del puerto 22.

## Acceso temporal

- Se uso una API key temporal de Vultr con expiracion de dos dias para consultas de lectura.
- El valor de la API key **no se almacena en este documento, en el repositorio ni en logs**.
- La API key fue expuesta durante la conversacion y debe revocarse al finalizar el diagnostico, aunque caduque automaticamente.

## Estado de despliegue

- No se ejecuto despliegue.
- No se reinicio la instancia.
- No se cambiaron contrasenas.
- No se cambiaron reglas de firewall.
- No se modificaron datos productivos.

## Siguiente accion controlada

Usar la consola noVNC para diagnosticar, en este orden:

```bash
systemctl status ssh --no-pager
ss -lntp | grep ':22'
ufw status verbose
```

Despues de obtener evidencia, se decidira si hace falta corregir el servicio o el firewall. Cualquier cambio debe quedar registrado antes y despues de ejecutarse.

## Diagnostico ejecutado

Fecha de evidencia: `2026-09-13T17:36:01Z`.

- `cloud-init`: `done`.
- `ssh.service`: habilitado y activo (`running`).
- `sshd -t`: validacion previa correcta (`status=0/SUCCESS`).
- Puerto 22: escuchando en `0.0.0.0:22` y `[::]:22`.
- `ufw`: activo, politica entrante `deny`, con reglas explicitas para 22/tcp, 80/tcp y 443/tcp en IPv4 e IPv6.
- Gunicorn: activo como usuario `prislab`, escuchando en `127.0.0.1:8000`.
- Nginx: activo como proxy frontal.
- Docker: servicio `inactive` y binario no instalado (`docker: command not found`).

## Conclusion operativa

El timeout inicial de SSH fue transitorio durante el arranque; actualmente SSH responde y la clave `prislabprod` autentica correctamente. No se necesita modificar el firewall ni `sshd`.

El VPS usa una instalacion directa de Gunicorn/Nginx, no Docker. No debe ejecutarse un despliegue Docker Compose en este servidor hasta definir y aprobar una estrategia compatible con el servicio actualmente activo. El acceso SSH por clave permite continuar con inspeccion y despliegue controlado.

## Verificacion externa posterior

Desde el equipo local, el `2026-09-13`:

- `https://prislab.labcorecloud.com/health/`: HTTP 200; base de datos y cache en estado `ok`.
- `https://prislab.labcorecloud.com/ready/`: HTTP 200; base de datos y cache en estado `ok`.

La verificacion confirma disponibilidad basica de produccion. No equivale a una prueba funcional completa de Farmacia/LIMS ni autoriza por si sola un despliegue.

## Reconciliacion de aplicacion productiva

- Ruta activa: `/opt/prislab/app`.
- El directorio productivo no contiene `.git`; no fue posible identificar un SHA desplegado desde el servidor.
- Todas las migraciones reportadas por `showmigrations --plan` estan aplicadas; no se observaron migraciones pendientes.
- La unidad productiva es `prislab-gunicorn.service` con `EnvironmentFile=/opt/prislab/app/.env`.
- `manage.py check --deploy` en el perfil efectivo de produccion reporto cuatro advertencias: HSTS en cero, redireccion SSL desactivada, cookies de sesion no seguras y cookie CSRF no segura.
- No se leyeron valores del `.env` ni secretos durante esta comprobacion.

## Revalidacion posterior

Se consulto el perfil efectivo mediante el comando de gestion, sin imprimir
secretos ni leer valores sensibles del archivo `.env`:

- `DEPLOYMENT_ENV=production`
- `DEBUG=False`
- `IS_PRODUCTION=True`
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECURE_HSTS_SECONDS=31536000`
- `manage.py check --deploy`: `System check identified no issues (0 silenced)`

La advertencia anterior sobre SSL/HSTS queda desactualizada para el proceso
actual y no se modifico la configuracion productiva en esta revalidacion.

## Decision

No se considera correcto declarar el VPS completamente alineado con el checkout local ni listo para desplegar sin una reconciliacion controlada. El siguiente paso tecnico es obtener un artefacto o SHA verificable del despliegue, comparar el paquete local contra el productivo y corregir la configuracion HTTPS mediante un cambio versionado y reversible.
