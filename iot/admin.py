from django.contrib import admin
from .models import Kiosco, VerificacionKiosco


@admin.register(Kiosco)
class KioscoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ubicacion', 'ip_address', 'activo', 'ultima_conexion')
    list_filter = ('activo',)
    search_fields = ('nombre', 'ubicacion')


@admin.register(VerificacionKiosco)
class VerificacionKioscoAdmin(admin.ModelAdmin):
    list_display = ('orden', 'kiosco', 'estado', 'fecha_creacion', 'fecha_confirmacion')
    list_filter = ('estado', 'kiosco')
    date_hierarchy = 'fecha_creacion'
