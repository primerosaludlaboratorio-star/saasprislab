"""Controles comunes de tenant para el Django Admin."""

from django.contrib import admin
from django.core.exceptions import FieldError


def _tenant_lookups(model, prefix='', seen=None, depth=0):
    """Descubre rutas FK/OneToOne hacia empresa sin mantener otro mapa manual."""
    seen = set() if seen is None else seen
    if depth > 3 or model in seen:
        return []
    seen = seen | {model}
    lookups = []
    for field in model._meta.get_fields():
        if not getattr(field, 'concrete', False) or not getattr(field, 'is_relation', False):
            continue
        name = f'{prefix}{field.name}'
        if field.name == 'empresa':
            lookups.append(f'{prefix}empresa_id')
        elif not getattr(field, 'many_to_many', False) and getattr(field, 'remote_field', None):
            lookups.extend(_tenant_lookups(field.remote_field.model, f'{name}__', seen, depth + 1))
    return lookups


class TenantScopedAdminMixin:
    """Limita el Admin al tenant del usuario y falla cerrado si no puede aislar."""

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset

        empresa_id = getattr(request.user, 'empresa_id', None)
        if not empresa_id:
            return queryset.none()

        if queryset.model._meta.model_name == 'empresa':
            return queryset.filter(pk=empresa_id)

        for lookup in _tenant_lookups(queryset.model):
            try:
                scoped = queryset.filter(**{lookup: empresa_id})
                # Compila la ruta para detectar relaciones inexistentes sin
                # ejecutar una consulta adicional por cada listado del Admin.
                str(scoped.query)
            except (FieldError, TypeError):
                continue
            return scoped

        # Nunca exponer un modelo cuyo vínculo tenant no sea demostrable.
        return queryset.none()


class TenantScopedAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    """ModelAdmin base para registros operativos multi-tenant."""
