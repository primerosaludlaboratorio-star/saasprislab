# ADR 0003: ROOT_URLCONF como paquete (`config.urls`)

**Estado:** Aceptado  
**Fecha:** 2026-07-09

## Contexto

El proyecto tiene:
- `config/urls.py`: archivo suelto, legacy, no usado por `ROOT_URLCONF`.
- `config/urls/__init__.py`: paquete Django, es el `ROOT_URLCONF` activo.
- `config/urls/core_views.py`: submódulo con endpoints de health/metrics.

Inicialmente se agregó `/metrics/` a `config/urls.py`, lo cual no tuvo efecto en runtime.

## Decisión

Mantener `ROOT_URLCONF = 'config.urls'` (paquete) y registrar todas las rutas SRE/funcionales en el submódulo apropiado (`config/urls/core_views.py` u otros). El archivo suelto `config/urls.py` se dejó en su estado original para evitar confusión.

## Consecuencias

- Las URLs deben agregarse en el paquete correcto.
- Cualquier modificación de `config/urls/` requiere coordinación porque afecta todo el enrutamiento.
- Se debe documentar claramente para nuevos desarrolladores.

## Alternativas consideradas

- Cambiar `ROOT_URLCONF` a `config.urls.py`: rompería modularidad y requeriría refactor grande.
- Eliminar `config/urls.py`: riesgoso si hay algún import legacy o referencia en documentación.
