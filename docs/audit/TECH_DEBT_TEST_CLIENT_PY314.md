# Deuda técnica: parche test client / Python 3.14 + Django 5.0.x

**Ubicación:** `farmacia/tests.py` (sustitución de `django.test.client.store_rendered_templates`).

**Síntoma:** `copy.copy()` sobre el contexto de plantilla en el signal `template_rendered` lanza  
`AttributeError: 'super' object has no attribute 'dicts'`  
en ciertas combinaciones Python 3.14 + Django 5.0.x, lo que antes interactuaba con Sentinel (302 / SQLite locked).

**Mitigación actual:** al importar `farmacia.tests`, se reemplaza `store_rendered_templates` por una versión que, si falla `copy(context)` y el contexto es `BaseContext`, almacena la referencia sin copiar.

**Plan de remoción (formal):**

1. Cuando el runtime de producción/CI use **Django ≥ 5.1** (o la versión documentada como compatible con Python 3.14), ejecutar `python manage.py test farmacia.tests` **sin** el parche.
2. Si los tests pasan, eliminar el bloque de monkeypatch en `farmacia/tests.py` y este archivo.
3. Si el proyecto fija Python ≤ 3.12 en CI, priorizar alinear el runtime de desarrollo con CI antes de retirar el parche.

**Autor/IA:** Cursor (registro vinculado a `DOCS_AUDIT_MAESTRO.md` §9, 2026-04-02).
