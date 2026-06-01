from django.contrib import admin
from .models import ReglaNegocio, EjecucionRegla


@admin.register(ReglaNegocio)
class ReglaNegocioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'categoria', 'tipo', 'activa', 'prioridad')
    list_filter = ('categoria', 'tipo', 'activa')
    search_fields = ('nombre', 'codigo')
    list_editable = ('activa', 'prioridad')


@admin.register(EjecucionRegla)
class EjecucionReglaAdmin(admin.ModelAdmin):
    list_display = ('regla', 'resultado', 'usuario', 'fecha')
    list_filter = ('resultado', 'regla')
    date_hierarchy = 'fecha'
    readonly_fields = ('regla', 'resultado', 'mensaje', 'datos_contexto', 'usuario', 'fecha')
