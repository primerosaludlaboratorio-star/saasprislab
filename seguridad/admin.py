from django.contrib import admin
from core.admin.tenant import TenantScopedAdmin
from .models import (
    DispositivoTOTP, DispositivoSMS, CodigoBackup2FA,
    SesionActiva, LogAccionSensible, ConfiguracionSeguridad, AlertaPanico
)


@admin.register(DispositivoTOTP)
class DispositivoTOTPAdmin(TenantScopedAdmin):
    list_display = ('usuario', 'nombre', 'activo', 'confirmado', 'fecha_creacion')
    list_filter = ('activo', 'confirmado')
    search_fields = ('usuario__username', 'nombre')
    readonly_fields = ('contador_usos', 'fecha_ultimo_uso')
    exclude = ('llave_secreta',)


@admin.register(CodigoBackup2FA)
class CodigoBackup2FAAdmin(TenantScopedAdmin):
    list_display = ('usuario', 'usado', 'fecha_creacion', 'fecha_uso')
    list_filter = ('usado',)
    search_fields = ('usuario__username',)
    readonly_fields = ('fecha_uso',)
    exclude = ('codigo',)


@admin.register(SesionActiva)
class SesionActivaAdmin(TenantScopedAdmin):
    list_display = ('usuario', 'dispositivo_tipo', 'ip_address', 'activa', 'fecha_inicio')
    list_filter = ('activa', 'es_sospechosa', 'dispositivo_tipo')
    search_fields = ('usuario__username', 'ip_address')
    readonly_fields = ('session_key', 'fecha_inicio')


@admin.register(LogAccionSensible)
class LogAccionSensibleAdmin(TenantScopedAdmin):
    list_display = ('fecha_hora', 'usuario', 'accion', 'ip_address', 'severidad')
    list_filter = ('accion', 'severidad', 'fecha_hora')
    search_fields = ('usuario__username', 'descripcion', 'ip_address')
    readonly_fields = ('fecha_hora',)
    date_hierarchy = 'fecha_hora'


@admin.register(ConfiguracionSeguridad)
class ConfiguracionSeguridadAdmin(TenantScopedAdmin):
    list_display = ('empresa', 'boton_panico_activo')


@admin.register(AlertaPanico)
class AlertaPanicoAdmin(TenantScopedAdmin):
    list_display = ('usuario', 'fecha_activacion', 'estado', 'ubicacion')
    list_filter = ('estado',)
    readonly_fields = ('fecha_activacion',)


@admin.register(DispositivoSMS)
class DispositivoSMSAdmin(TenantScopedAdmin):
    list_display = ('usuario', 'telefono', 'activo', 'confirmado', 'fecha_creacion')
    list_filter = ('activo', 'confirmado')
    search_fields = ('usuario__username', 'telefono')
    readonly_fields = ('fecha_creacion', 'fecha_confirmacion', 'fecha_ultimo_uso')
