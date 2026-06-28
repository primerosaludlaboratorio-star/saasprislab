# Apéndice — Fórmulas y validación LIMS (PRISLAB v7.5, Punto 10)

**Motor:** `core/services/clinical_math.py` — AST seguro (sin `eval()`).

**Variables:** coinciden con **código** o **abreviatura** del analito en la orden (insensible a mayúsculas en la expresión).

**Operadores:** `+`, `-`, `*`, `/`, `//`, `%`, `**`.

**Funciones permitidas:** `sqrt`, `log`, `log10`, `log1p`, `exp`, `sin`, `cos`, `tan`, `pow`, `min`, `max`, `abs`, `round`.

**Ejemplos (configurar en `lims.Analito` campo `formula` y `es_calculado=True`):**

- Friedewald LDL aproximado: `COL - (TRIG / 5) - HDL` (validar regla TRIG &lt; 400 en procedimiento).
- Cociente: `COL / HDL`

**API:** `POST /laboratorio/api/preview-formulas/<orden_id>/` con `{"overrides":{"<analito_id>":"valor"}}`.

**Persistencia:** `api_guardar_resultados` ignora valores cliente en `es_calculado`; recalcula y valida rangos / escudo.

**Tests:** `python manage.py test core.tests.test_clinical_math`
