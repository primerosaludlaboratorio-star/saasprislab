# Fix staticfiles Nginx / PDV - 2026-06-21

## Resumen

Durante la auditoria funcional del PDV de Farmacia en produccion se detecto que la pantalla cargaba, pero los assets estaticos criticos devolvian `403`.

Esto bloqueaba JavaScript como `pdv_farmacia.js`, por lo que el buscador podia verse en pantalla pero no disparaba correctamente las llamadas de UI.

## Causa raiz

Nginx servia `/static/` desde:

```nginx
alias /opt/prislab/app/staticfiles/;
```

El archivo existia y tenia permisos correctos, pero el directorio padre `/opt/prislab` estaba protegido (`750`). Nginx (`www-data`) no podia atravesar el arbol y respondia `403`.

## Solucion aplicada

Se creo una ruta publica dedicada para estaticos:

```text
/var/www/prislab-static/
```

Se sincronizo el contenido de `/opt/prislab/app/staticfiles/` a esa ruta y se actualizo Nginx para servir:

```nginx
location /static/ {
    alias /var/www/prislab-static/;
}

location /favicon.ico {
    alias /var/www/prislab-static/img/favicon.ico;
}
```

Tambien se actualizo `scripts/deploy_vps.sh` para que futuros deploys ejecuten la sincronizacion automaticamente despues de `collectstatic`.

## Validacion en produccion

Commit desplegado en VPS:

```text
cc8c4b2 fix: servir staticfiles desde ruta publica nginx
```

Validaciones:

```text
/static/js/pdv_farmacia.6916cc496f36.js -> HTTP/2 200
/farmacia/pdv/ sin sesion -> HTTP/2 302 a /login/
```

E2E seguro `_e2e_ui_omni.mjs`:

```text
Login jonathan -> OK
PDV -> OK
input buscador -> presente
busqueda "para" -> disparada
/farmacia/api/buscar-producto-pdv/ -> HTTP 200 JSON
console_errors -> []
request_failed -> []
resource_404 -> []
```

Resultado de producto:

```text
PARACETAMOL 500MG TEST
stock_total: 100
precio_venta: 15.0
```

## Estado

CONFIRMADO / CORREGIDO.

El problema no era la herramienta de navegador ni un bug del endpoint. Era configuracion de Nginx/permisos de staticfiles.

## Pendientes relacionados

- Mantener `collectstatic` hacia `/opt/prislab/app/staticfiles`.
- Mantener copia publica Nginx en `/var/www/prislab-static`.
- Si se agregan nuevos assets, ejecutar deploy o sincronizar estaticos antes de validar UI.
