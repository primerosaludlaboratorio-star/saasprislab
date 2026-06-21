# Fix LAB-H2-001 - Analitos por empresa en recepcion laboratorio - 2026-06-21

## Hallazgo

Cascada reporto que `recepcion_lab` construia las categorias/departamentos desde:

```python
Analito.objects.filter(activo=True).exclude(departamento='')
```

`lims.Analito` tiene FK `empresa`, por lo que esa consulta podia incluir departamentos de analitos pertenecientes a otra empresa.

## Clasificacion

CONFIRMADO / ALTO / CROSS-TENANT.

## Fix aplicado

Archivo:

```text
core/views/laboratorio.py
```

Cambio:

```python
Analito.objects.filter(empresa=empresa, activo=True).exclude(departamento='')
```

## Prueba agregada

Archivo:

```text
core/tests/test_laboratorio_recepcion_tenant.py
```

Test:

```text
test_recepcion_lab_no_expone_departamentos_analitos_de_otra_empresa
```

La prueba crea:

- Analito de la empresa del usuario con departamento `QUIMICA PRISLAB`.
- Analito de otra empresa con departamento `SECRETO OTRO TENANT`.

Valida que `recepcion_lab` incluya solo el departamento de la empresa del usuario.

## Validacion local

```text
python manage.py check
System check identified no issues (0 silenced).
```

Validacion directa de la consulta tenant:

```text
deps=set(Analito.objects.filter(empresa=e, activo=True).exclude(departamento='').values_list('departamento', flat=True))
print('QUIMICA PRISLAB' in deps, 'SECRETO OTRO TENANT' in deps)
True False
```

Tambien se agrego prueba automatizada focalizada en `core/tests/test_laboratorio_recepcion_tenant.py`.

Nota: en este entorno Windows el runner de test puntual quedo en timeout preparando BD de prueba, sin traceback de fallo de codigo. La validacion directa de query y `manage.py check` pasaron.

## Estado

Listo para commit, push, deploy y smoke productivo.
