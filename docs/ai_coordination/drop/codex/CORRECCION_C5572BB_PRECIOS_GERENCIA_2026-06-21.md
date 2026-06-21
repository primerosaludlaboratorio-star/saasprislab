# Correccion Codex - c5572bb Precios LIMS

Fecha: 2026-06-21

## Contexto

Se detecto un commit local `c5572bb` con mensaje:

`fix: estandarizar roles en precios.py - quitar GERENTE inconsistente`

El commit removia acceso de:

- rol `GERENTE`
- grupo `GERENCIA`

en `lims/views/precios.py`.

## Veredicto Codex

No aprobado como criterio general.

La estandarizacion con `analitos.py`, `perfiles.py` y `paquetes.py` no aplica de forma automatica a `precios.py`, porque precios LIMS es un flujo financiero/comercial.

El sistema usa `GERENTE` y `GERENCIA` de forma activa en modulos financieros, farmacia, dashboards, sidebar y PRIS IA.

## Decision aplicada

Se restaura:

- `GERENTE`
- grupo `GERENCIA`

manteniendo:

- empresa obligatoria via `get_empresa_usuario(user)`
- staff/superuser solo con empresa valida

## Validacion

- `python -m py_compile lims/views/precios.py`: OK
- `python manage.py check`: OK

## Regla para siguientes lotes

No eliminar roles de negocio por "consistencia" visual entre modulos. Si un modulo tiene naturaleza financiera/gerencial, debe evaluarse por flujo de negocio, no por copia exacta del permiso tecnico de catalogos.
