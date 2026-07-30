from django.contrib import admin
from core.admin.tenant import TenantScopedAdmin
from .models import Kiosco, VerificacionKiosco


@admin.register(Kiosco)
class KioscoAdmin(TenantScopedAdmin):
    list_display = ('nombre', 'ubicacion', 'ip_address', 'activo', 'ultima_conexion')
    list_filter = ('activo',)
    search_fields = ('nombre', 'ubicacion')


@admin.register(VerificacionKiosco)
class VerificacionKioscoAdmin(TenantScopedAdmin):
    list_display = ('orden', 'kiosco', 'estado', 'fecha_creacion', 'fecha_confirmacion')
    list_filter = ('estado', 'kiosco')
    date_hierarchy = 'fecha_creacion'
