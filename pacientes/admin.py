"""
Admin para el módulo de Pacientes.
"""
from django.contrib import admin
from django.core.exceptions import ValidationError
from core.admin.tenant import TenantScopedAdmin
from core.models import Paciente
from django.utils.html import format_html
from django.urls import reverse

from .portal_models import UsuarioPaciente, SolicitudAccesoPortal, AccesoExpedientePortal


@admin.register(UsuarioPaciente)
class UsuarioPacienteAdmin(TenantScopedAdmin):
    """Admin para usuarios del portal de pacientes."""
    list_display = (
        'email',
        'paciente',
        'activo_display',
        'email_verificado_display',
        'fecha_registro',
        'ultimo_acceso'
    )
    list_filter = ('is_active', 'email_verificado', 'fecha_registro', 'ultimo_acceso')
    search_fields = (
        'email',
        'telefono',
        'paciente__nombres',
        'paciente__apellidos'
    )
    readonly_fields = (
        'fecha_registro',
        'ultimo_acceso',
        'token_verificacion'
    )
    date_hierarchy = 'fecha_registro'
    
    fieldsets = (
        ('Paciente', {
            'fields': ('paciente', 'email', 'telefono')
        }),
        ('Estado', {
            'fields': ('is_active', 'email_verificado')
        }),
        ('Seguridad', {
            'fields': ('password', 'token_verificacion', 'token_recuperacion', 'token_recuperacion_expira')
        }),
        ('Notificaciones', {
            'fields': ('notificaciones_email', 'notificaciones_sms')
        }),
        ('Auditoría', {
            'fields': ('fecha_registro', 'ultimo_acceso')
        })
    )
    
    def activo_display(self, obj):
        """Muestra el estado con un badge."""
        if obj.is_active:
            return format_html('<span class="badge bg-success">✓ Activo</span>')
        else:
            return format_html('<span class="badge bg-danger">✗ Inactivo</span>')
    activo_display.short_description = 'Estado'
    activo_display.admin_order_field = 'is_active'
    
    def email_verificado_display(self, obj):
        """Muestra si el email está verificado."""
        if obj.email_verificado:
            return format_html('<span class="badge bg-success">✓ Verificado</span>')
        else:
            return format_html('<span class="badge bg-warning">⏸ Pendiente</span>')
    email_verificado_display.short_description = 'Email'
    email_verificado_display.admin_order_field = 'email_verificado'


@admin.register(SolicitudAccesoPortal)
class SolicitudAccesoPortalAdmin(TenantScopedAdmin):
    """Admin para solicitudes de acceso al portal."""
    list_display = (
        'nombre_completo',
        'email',
        'telefono',
        'empresa',
        'estado_display',
        'fecha_solicitud',
        'fecha_respuesta'
    )
    list_filter = ('estado', 'fecha_solicitud', 'fecha_respuesta')
    search_fields = (
        'nombre_completo',
        'email',
        'telefono',
        'numero_identificacion'
    )
    readonly_fields = (
        'empresa',
        'fecha_solicitud',
        'fecha_respuesta',
        'ip_solicitud'
    )
    date_hierarchy = 'fecha_solicitud'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        empresa_id = getattr(request.user, 'empresa_id', None)
        return queryset.filter(empresa_id=empresa_id) if empresa_id else queryset.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'paciente' and not request.user.is_superuser:
            empresa_id = getattr(request.user, 'empresa_id', None)
            kwargs['queryset'] = Paciente.objects.filter(
                empresa_id=empresa_id, activo=True
            ) if empresa_id else Paciente.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            empresa_id = getattr(request.user, 'empresa_id', None)
            if not empresa_id:
                raise ValidationError('El usuario no tiene empresa asignada.')
            obj.empresa_id = empresa_id
            if obj.paciente_id and obj.paciente.empresa_id != empresa_id:
                raise ValidationError('El paciente seleccionado pertenece a otra empresa.')
        super().save_model(request, obj, form, change)
    
    fieldsets = (
        ('Información del Solicitante', {
            'fields': (
                'nombre_completo',
                'email',
                'telefono',
                'fecha_nacimiento',
                'numero_identificacion'
            )
        }),
        ('Vinculación', {
            'fields': ('paciente',)
        }),
        ('Estado', {
            'fields': ('estado', 'motivo_rechazo')
        }),
        ('Auditoría', {
            'fields': (
                'fecha_solicitud',
                'fecha_respuesta',
                'respondido_por',
                'ip_solicitud'
            )
        })
    )
    
    def estado_display(self, obj):
        """Muestra el estado con un badge."""
        colors = {
            'PENDIENTE': 'warning',
            'APROBADA': 'success',
            'RECHAZADA': 'danger'
        }
        color = colors.get(obj.estado, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_display.short_description = 'Estado'
    estado_display.admin_order_field = 'estado'


@admin.register(AccesoExpedientePortal)
class AccesoExpedientePortalAdmin(TenantScopedAdmin):
    """Admin para logs de acceso al expediente (solo lectura)."""
    list_display = (
        'usuario_portal',
        'seccion_consultada',
        'fecha_acceso',
        'ip_address'
    )
    list_filter = ('fecha_acceso', 'seccion_consultada')
    search_fields = (
        'usuario_portal__email',
        'usuario_portal__paciente__nombres',
        'usuario_portal__paciente__apellidos',
        'ip_address'
    )
    readonly_fields = (
        'usuario_portal',
        'fecha_acceso',
        'seccion_consultada',
        'ip_address',
        'user_agent'
    )
    date_hierarchy = 'fecha_acceso'
    
    def has_add_permission(self, request):
        """No permite crear logs manualmente."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permite eliminar logs."""
        return False
