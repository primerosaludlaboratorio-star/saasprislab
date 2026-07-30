"""
core.admin - Administracion Django dividida por dominio.
"""
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group

from .tenant import TenantScopedAdminMixin

from .identidad import *  # noqa: F401,F403
from .catalogo import *  # noqa: F401,F403
from .ventas import *  # noqa: F401,F403
from .clinico import *  # noqa: F401,F403
from .bienestar import *  # noqa: F401,F403
from .rrhh import *  # noqa: F401,F403


# El grupo de Django es global, no tenant-aware. Solo el superusuario puede
# gestionarlo; un Director de empresa no debe administrar permisos globales.
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


class TenantGroupAdmin(TenantScopedAdminMixin, GroupAdmin):
    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset(request)
        return self.model._default_manager.none()


admin.site.register(Group, TenantGroupAdmin)
