from django.contrib import admin
from core.admin.tenant import TenantScopedAdmin
from django.utils.html import format_html
from django.db.models import Q
from .models import DiarioEmocional, RecursoCrecimiento


@admin.register(DiarioEmocional)
class DiarioEmocionalAdmin(TenantScopedAdmin):
    """
    Administración de diario emocional.
    Solo lectura para usuarios no superusuarios.
    Oculta contenido si el usuario no es superusuario.
    """
    list_display = ('usuario', 'fecha', 'nivel_riesgo_display', 'sentimiento_ia', 'alerta_enviada', 'fecha_creacion')
    list_filter = ('nivel_riesgo', 'alerta_enviada', 'fecha', 'fecha_creacion')
    search_fields = ('usuario__username', 'usuario__email', 'sentimiento_ia')
    date_hierarchy = 'fecha'
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'contenido_privado_display')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        empresa_id = getattr(request.user, 'empresa_id', None)
        if not empresa_id:
            return queryset.none()
        return queryset.filter(empresa_id=empresa_id, usuario__empresa_id=empresa_id)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('usuario', 'fecha', 'nivel_riesgo', 'sentimiento_ia')
        }),
        ('Contenido', {
            'fields': ('contenido_privado_display',),
            'description': 'El contenido solo es visible para superusuarios.'
        }),
        ('Metadatos', {
            'fields': ('alerta_enviada', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def nivel_riesgo_display(self, obj):
        """Muestra el nivel de riesgo con icono."""
        riesgo_icon = {
            'VERDE': '🟢',
            'AMARILLO': '🟡',
            'ROJO_VIDA': '🔴',
            'ROJO_VIOLENCIA': '🔴',
            'ROJO_ACOSO': '🔴',
            'ROJO_SUSTANCIAS': '🔴',
        }
        icon = riesgo_icon.get(obj.nivel_riesgo, '⚪')
        return format_html('{} {}', icon, obj.get_nivel_riesgo_display())
    nivel_riesgo_display.short_description = 'Nivel de Riesgo'
    
    def contenido_privado_display(self, obj):
        """Nunca expone texto emocional sensible desde el panel administrativo."""
        return format_html(
            '<div style="color: #999; font-style: italic;">'
            '[Contenido cifrado - no se muestra en el panel administrativo]'
            '</div>'
        )
    contenido_privado_display.short_description = 'Contenido Privado'
    
    def get_readonly_fields(self, request, obj=None):
        """Hace todos los campos de solo lectura si el usuario no es superusuario."""
        if not request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields
    
    def has_add_permission(self, request):
        """Solo superusuarios pueden agregar entradas desde el admin."""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Solo superusuarios pueden modificar entradas desde el admin."""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Solo superusuarios pueden eliminar entradas desde el admin."""
        return request.user.is_superuser


@admin.register(RecursoCrecimiento)
class RecursoCrecimientoAdmin(TenantScopedAdmin):
    """Administración de recursos de crecimiento."""
    list_display = ('titulo', 'categoria', 'activo', 'fecha_creacion')
    list_filter = ('categoria', 'activo', 'fecha_creacion')
    search_fields = ('titulo', 'descripcion', 'url_contenido')
    fieldsets = (
        ('Información del Recurso', {
            'fields': ('empresa', 'titulo', 'categoria', 'url_contenido', 'descripcion', 'activo')
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('fecha_creacion',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        empresa_id = getattr(request.user, 'empresa_id', None)
        if not empresa_id:
            return queryset.none()
        return queryset.filter(Q(empresa_id=empresa_id) | Q(empresa__isnull=True))

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.empresa_id is None and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.empresa_id is None and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)
