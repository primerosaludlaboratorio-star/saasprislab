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

## Deploy y smoke productivo

Commit:

```text
97da7c7 fix: aislar departamentos lims por empresa en recepcion
```

VPS:

```text
git pull origin release/v1.0-local
systemctl restart prislab-gunicorn
systemctl restart prislab-celery
systemctl restart prislab-celerybeat
systemctl reload nginx
```

Validacion:

```text
prislab-gunicorn: active
prislab-celery: active
prislab-celerybeat: active
manage.py check: 0 issues
/laboratorio/recepcion/ autenticado como jonathan -> 200 final
```

## Estado

CONFIRMADO / CORREGIDO / DESPLEGADO / VALIDADO EN PRODUCCION.
