# Fix P2 Analizadores + H3 Expediente - 2026-06-21

## Resumen

Se revisaron dos hallazgos reportados por auditoria externa:

- P2 Director Analizadores: filtros por `empresa` sobre `laboratorio.Equipo`.
- H3 Loop medico/expediente: rol `DIRECTOR` recibia 403 en expediente clinico.

Ambos eran relevantes porque las rutas estan cableadas en `config/urls.py`.

## P2 - Director Analizadores

### Estado

CONFIRMADO / CORREGIDO.

### Causa raiz

`laboratorio.models.Equipo` no tiene campo `empresa`.

Sin embargo, `core.views.director` filtraba:

```python
Equipo.objects.filter(empresa=empresa)
CodigoParametroEquipo.objects.filter(equipo__empresa=empresa)
get_object_or_404(Equipo, id=equipo_id, empresa=empresa)
Equipo.objects.create(empresa=empresa, ...)
```

Eso podia producir `FieldError` / `TypeError` en:

- `/director/analizadores/`
- `/director/analizadores/crear/`
- `/director/analizadores/<id>/toggle/`
- `/director/analizadores/<id>/mapeos/`
- `/director/analizadores/mapeo/<id>/eliminar/`

### Decision

Como el modelo actual es global, se corrigio el bloque para tratar analizadores como infraestructura global protegida por RBAC (`_require_director`).

No se agrego migracion `empresa` en esta ronda porque eso es una decision multitenant mayor y requiere asignacion historica de equipos.

### Fix aplicado

- `Equipo.objects.all()`
- `CodigoParametroEquipo.objects.select_related(...)`
- `get_object_or_404(Equipo, id=equipo_id)`
- `Equipo.objects.create(...)` sin `empresa`
- Se elimino un import local de `redirect` que generaba `UnboundLocalError` en POST.

## H3 - Expediente Clinico DIRECTOR

### Estado

CONFIRMADO / CORREGIDO.

### Causa raiz

`core.views.expediente.expediente_clinico` solo permitia:

```python
request.user.rol == 'MEDICO' or request.user.is_superuser
```

Un usuario `DIRECTOR` no superuser recibia 403. En auditorias con Sentinel, esto podia aparentar loop de reparacion/autofix.

### Fix aplicado

Se permite expediente completo a:

- superuser
- staff
- `MEDICO`
- `DIRECTOR`
- `ADMIN`
- `ADMINISTRADOR`
- `GERENTE`
- grupos `MEDICOS`, `GERENCIA`, `GERENCIA_OPERATIVA`, `DIRECTOR`

## Pruebas

Suite focalizada:

```text
python manage.py test core.tests.test_auditoria_funcional_20260621 --keepdb -v 1
```

Resultado:

```text
Ran 7 tests in 13.598s
OK
```

Cobertura agregada:

- `test_director_analizadores_carga_sin_filtrar_empresa_inexistente`
- `test_director_analizadores_crear_y_toggle_equipo_global`
- `test_director_puede_ver_expediente_clinico_sin_loop_403`

## Estado final

Listo para commit, push y deploy.
