"""
Resolución de la empresa "principal" para auto-tenant y usuarios sin FK empresa.

Prioridad:
  1) settings.PRISLAB_DEFAULT_EMPRESA_ID (env) si existe y está activa
  2) Única Empresa activa en BD
  3) Empresa pk=1 si existe y está activa
  4) Primera Empresa activa por orden de id
"""
from django.apps import apps
from django.conf import settings


def resolve_default_empresa_sistema():
    """
    Retorna la instancia Empresa a usar como tenant por defecto, o None si no hay ninguna.
    """
    Empresa = apps.get_model('core', 'Empresa')

    pk = getattr(settings, 'PRISLAB_DEFAULT_EMPRESA_ID', None)
    if pk is not None:
        e = Empresa.objects.filter(pk=int(pk), activa=True).first()
        if e:
            return e

    qs = Empresa.objects.filter(activa=True)
    if qs.count() == 1:
        return qs.first()

    e = Empresa.objects.filter(pk=1, activa=True).first()
    if e:
        return e

    return qs.order_by('id').first()
