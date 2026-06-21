# Cierre Canonico Codex - Auditoria Tenant 2026-06-21

## Estado Canonico

El cierre final correcto NO es `c5572bb`.

El cierre final correcto es:

```text
a1d8913 fix: restaurar acceso gerencial a precios LIMS
c5572bb fix: estandarizar roles en precios.py - quitar GERENTE inconsistente
59f5ea0 refactor: centralizar empresa usuario en permisos tenant
b82334a fix: endurecer scoping tenant en LIMS y reportes
```

## Produccion

Validado por Codex en VPS:

```text
HEAD VPS: a1d8913
HEAD origin/release/v1.0-local: a1d8913
HEAD local release/v1.0-local: a1d8913
```

## Correccion a reportes de otros agentes

Reportes que indiquen:

- `c5572bb` como HEAD final
- "GERENTE eliminado" como veredicto final
- "GERENCIA eliminada" como veredicto final

estan desactualizados.

## Regla final aprobada

### Global tenant-sensitive

- Empresa obligatoria siempre.
- Staff/superuser solo operan si tienen empresa valida.
- Objetos deben filtrarse por empresa.

### LIMS catalogo tecnico

Aplica a:

- `lims/views/analitos.py`
- `lims/views/perfiles.py`
- `lims/views/paquetes.py`

Roles permitidos:

- `ADMIN`
- `ADMINISTRADOR`
- `LABORATORIO`
- `LIMS`
- staff/superuser con empresa

### LIMS precios

Aplica a:

- `lims/views/precios.py`

Roles permitidos:

- `ADMIN`
- `ADMINISTRADOR`
- `LABORATORIO`
- `LIMS`
- `GERENTE`
- grupo `GERENCIA`
- staff/superuser con empresa

Motivo: precios LIMS es flujo financiero/comercial, no solamente catalogo tecnico.

## Validacion ejecutada

- `python manage.py check`: OK
- Servicios VPS:
  - `prislab-gunicorn`: active
  - `prislab-celery`: active
  - `prislab-celerybeat`: active
- Home produccion: HTTP 200
- Smoke autenticado:
  - `/laboratorio/recepcion/`: 200
  - `/lims/api/parametros/buscar/?q=Glucosa`: 200 JSON
- PostgreSQL: `active|1`

## Instruccion para siguientes reportes

Usar este documento como fuente canonica para el cierre tenant/security.

No repetir `c5572bb` como estado final.
