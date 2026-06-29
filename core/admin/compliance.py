"""
Admin — Compliance (COFEPRIS + LGPD)
"""
from django.contrib import admin
from core.models import (
    ResponsableSanitario, FirmaDigitalResultado,
    ConsentimientoLGPD, DerechoOlvido, RegistroAccesoDatos
)


@admin.register(ResponsableSanitario)
class ResponsableSanitarioAdmin(admin.ModelAdmin):
    """Gestión de Responsables Sanitarios (COFEPRIS)."""
    list_display = ('usuario', 'empresa', 'cedula_profesional', 'esta_vigente', 'activo')
    list_filter = ('empresa', 'activo', 'fecha_vigencia_inicio')
    search_fields = ('usuario__first_name', 'usuario__last_name', 'cedula_profesional', 'numero_registro_cofepris')
    readonly_fields = ('usuario',)
    fieldsets = (
        ('Identidad', {
            'fields': ('usuario', 'empresa')
        }),
        ('Credenciales', {
            'fields': ('cedula_profesional', 'numero_registro_cofepris')
        }),
        ('Vigencia', {
            'fields': ('fecha_vigencia_inicio', 'fecha_vigencia_fin', 'activo')
        }),
        ('Certificado Digital', {
            'fields': ('certificado_digital',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        eid = getattr(request.user, 'empresa_id', None)
        if eid:
            return qs.filter(empresa_id=eid)
        return qs.none()


@admin.register(FirmaDigitalResultado)
class FirmaDigitalResultadoAdmin(admin.ModelAdmin):
    """Auditoría de firmas digitales de resultados."""
    list_display = ('paciente', 'responsable_sanitario', 'fecha_firma', 'verificada', 'modelo_referencia')
    list_filter = ('verificada', 'fecha_firma', 'responsable_sanitario__empresa')
    search_fields = ('paciente__nombre_completo', 'responsable_sanitario__usuario__last_name', 'hash_contenido')
    readonly_fields = ('fecha_firma', 'hash_contenido', 'firma_hexadecimal')
    fieldsets = (
        ('Referencia', {
            'fields': ('paciente', 'responsable_sanitario', 'modelo_referencia', 'objeto_id')
        }),
        ('Firma Digital', {
            'fields': ('hash_contenido', 'firma_hexadecimal', 'certificado_usado', 'verificada'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('fecha_firma', 'ip_address'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        eid = getattr(request.user, 'empresa_id', None)
        if eid:
            return qs.filter(responsable_sanitario__empresa_id=eid)
        return qs.none()


@admin.register(ConsentimientoLGPD)
class ConsentimientoLGPDAdmin(admin.ModelAdmin):
    """Gestión de consentimientos de datos (LGPD)."""
    list_display = ('paciente', 'tipo', 'otorgado', 'es_vigente', 'fecha_otorgamiento')
    list_filter = ('tipo', 'otorgado', 'fecha_otorgamiento', 'fecha_revocacion')
    search_fields = ('paciente__nombre_completo', 'paciente__email')
    readonly_fields = ('fecha_otorgamiento', 'fecha_revocacion')
    fieldsets = (
        ('Consentimiento', {
            'fields': ('paciente', 'tipo', 'otorgado')
        }),
        ('Trazabilidad', {
            'fields': ('fecha_otorgamiento', 'fecha_revocacion', 'usuario_registro', 'ip_address'),
            'classes': ('collapse',)
        }),
        ('Documento', {
            'fields': ('documento_consentimiento',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        eid = getattr(request.user, 'empresa_id', None)
        if eid:
            return qs.filter(paciente__empresa_id=eid)
        return qs.none()


@admin.register(DerechoOlvido)
class DerechoOlvidoAdmin(admin.ModelAdmin):
    """Solicitudes de Derecho al Olvido (LGPD Art. 17)."""
    list_display = ('paciente', 'estado', 'fecha_solicitud', 'fecha_respuesta', 'usuario_responsable')
    list_filter = ('estado', 'fecha_solicitud', 'fecha_respuesta')
    search_fields = ('paciente__nombre_completo', 'razon', 'datos_a_eliminar')
    readonly_fields = ('fecha_solicitud',)
    fieldsets = (
        ('Solicitud', {
            'fields': ('paciente', 'estado', 'razon', 'datos_a_eliminar')
        }),
        ('Procesamiento', {
            'fields': ('usuario_responsable', 'notas_procesamiento', 'fecha_solicitud', 'fecha_respuesta'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        eid = getattr(request.user, 'empresa_id', None)
        if eid:
            return qs.filter(paciente__empresa_id=eid)
        return qs.none()


@admin.register(RegistroAccesoDatos)
class RegistroAccesoDatosAdmin(admin.ModelAdmin):
    """Auditoría de acceso a datos personales (LGPD)."""
    list_display = ('usuario', 'paciente', 'tipo_datos', 'accion', 'fecha_acceso')
    list_filter = ('accion', 'tipo_datos', 'fecha_acceso')
    search_fields = ('usuario__username', 'paciente__nombre_completo', 'motivo')
    readonly_fields = ('fecha_acceso', 'usuario', 'paciente')
    fieldsets = (
        ('Acceso', {
            'fields': ('usuario', 'paciente', 'tipo_datos', 'accion')
        }),
        ('Auditoría', {
            'fields': ('fecha_acceso', 'ip_address', 'motivo'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # RegistroAccesoDatos se crea automáticamente, no se añade manual
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        eid = getattr(request.user, 'empresa_id', None)
        if eid:
            return qs.filter(paciente__empresa_id=eid)
        return qs.none()
