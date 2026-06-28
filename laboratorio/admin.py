from django.contrib import admin

from .models import (
    CategoriaExamen, Equipo, Estudio, InsumoEstudio,
    Resultado, Parametro, RangoReferenciaParametro,
    # Modelos rescatados V5.4
    ValorReferencia, PerfilLaboratorio, NotificacionPanico, ControlCalidad,
    CodigoParametroEquipo, ResultadoHL7, ResultadoHL7Huerfano, BitacoraMantenimiento,
    HistorialResultados, ResponsableSanitario,
)


@admin.register(CategoriaExamen)
class CategoriaExamenAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)


class ParametroInline(admin.TabularInline):
    model = Parametro
    extra = 1
    fields = ('nombre', 'codigo_interfaz', 'valor_ref_min', 'valor_ref_max', 'unidades')


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'marca', 'protocolo', 'ip_address', 'puerto', 'activo')
    list_filter = ('protocolo', 'activo', 'marca')
    search_fields = ('nombre', 'marca')
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'marca', 'activo')
        }),
        ('Configuración de Interfaz', {
            'fields': ('protocolo', 'ip_address', 'puerto')
        }),
        ('Notas', {
            'fields': ('notas',),
            'classes': ('collapse',)
        }),
    )


class InsumoEstudioInline(admin.TabularInline):
    model = InsumoEstudio
    extra = 1
    autocomplete_fields = ['producto']


@admin.register(Estudio)
class EstudioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'codigo', 'equipo_default', 'precio_base', 'unidades')
    list_filter = ('categoria', 'equipo_default', 'es_perfil')
    search_fields = ('nombre', 'codigo')
    inlines = [ParametroInline, InsumoEstudioInline]
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'codigo', 'categoria', 'precio_base', 'es_perfil')
        }),
        ('Integración con Equipos', {
            'fields': ('equipo_default',),
            'description': 'Equipo de laboratorio por defecto para envío automático a Worklist.'
        }),
        ('Rangos de Referencia', {
            'fields': ('valor_minimo', 'valor_maximo', 'unidades')
        }),
        ('Información Adicional', {
            'fields': ('dias_entrega', 'muestra_requerida', 'indicaciones', 'descripcion_interna'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Resultado)
class ResultadoAdmin(admin.ModelAdmin):
    list_display = ('orden', 'estudio', 'valor_obtenido', 'es_anormal')
    list_filter = ('es_anormal', 'estudio')
    search_fields = ('orden__id', 'estudio__nombre')
    fieldsets = (
        ('Información Básica', {
            'fields': ('orden', 'estudio', 'valor_obtenido', 'valor', 'es_anormal')
        }),
        ('Análisis de IA', {
            'fields': ('notas_ia',),
            'description': 'Observaciones específicas generadas por inteligencia artificial para este parámetro.',
            'classes': ('collapse',)
        }),
    )


@admin.register(RangoReferenciaParametro)
class RangoReferenciaParametroAdmin(admin.ModelAdmin):
    list_display = ('parametro', 'sexo', 'edad_min_anios', 'edad_max_anios', 'valor_minimo', 'valor_maximo', 'valor_critico_bajo', 'valor_critico_alto', 'unidad', 'fuente', 'activo')
    list_filter = ('sexo', 'fuente', 'activo')
    search_fields = ('parametro__nombre', 'parametro__codigo_interfaz')
    list_editable = ('activo',)
    ordering = ('parametro__nombre', 'sexo', 'edad_min_anios')
    fieldsets = (
        ('Parámetro y Segmentación', {
            'fields': ('parametro', 'sexo', 'edad_min_anios', 'edad_max_anios')
        }),
        ('Rangos de Referencia (ISO 15189)', {
            'fields': ('valor_minimo', 'valor_maximo', 'unidad'),
            'description': 'Rango de referencia normal (verde en el semáforo).'
        }),
        ('Valores Críticos (Semáforo Rojo)', {
            'fields': ('valor_critico_bajo', 'valor_critico_alto'),
            'description': 'Valores de pánico — activan el semáforo rojo de PRIS y bloquean la validación.'
        }),
        ('Metadatos y Trazabilidad', {
            'fields': ('fuente', 'referencia_bibliografica', 'fecha_verificacion', 'activo'),
            'classes': ('collapse',)
        }),
    )


# ==============================================================================
# MODELOS RESCATADOS V5.4 — "OPERACIÓN TRANSPARENTE"
# ==============================================================================

@admin.register(Parametro)
class ParametroAdmin(admin.ModelAdmin):
    """494 parámetros de laboratorio — fuente maestra para HL7 y rangos ISO."""
    list_display   = ('nombre', 'estudio', 'codigo_interfaz', 'unidades', 'valor_ref_min', 'valor_ref_max')
    list_filter    = ('estudio__categoria',)
    search_fields  = ('nombre', 'codigo_interfaz', 'estudio__nombre')
    ordering       = ('estudio__nombre', 'nombre')
    autocomplete_fields = ['estudio']


@admin.register(ValorReferencia)
class ValorReferenciaAdmin(admin.ModelAdmin):
    """219 rangos de referencia por estudios — segmentados por sexo y edad."""
    list_display  = ('estudio', 'sexo', 'edad', 'valor_minimo', 'valor_maximo', 'unidades')
    list_filter   = ('sexo',)
    search_fields = ('estudio__nombre',)
    ordering      = ('estudio__nombre', 'sexo', 'edad')


@admin.register(PerfilLaboratorio)
class PerfilLaboratorioAdmin(admin.ModelAdmin):
    """17 perfiles de laboratorio — paquetes de estudios agrupados."""
    list_display   = ('nombre', 'precio', 'area_pertenencia', 'activo')
    list_filter    = ('activo', 'area_pertenencia')
    search_fields  = ('nombre',)
    list_editable  = ('activo',)


@admin.register(NotificacionPanico)
class NotificacionPanicoAdmin(admin.ModelAdmin):
    """Registro de notificaciones de valores de pánico (ISO 15189 §7.4.3)."""
    list_display   = ('orden', 'medico_notificado', 'cargo_receptor', 'medio_notificacion',
                      'fecha_hora_notificacion')
    list_filter    = ('medio_notificacion',)
    search_fields  = ('medico_notificado', 'orden__id')
    date_hierarchy = 'fecha_hora_notificacion'
    readonly_fields = ('fecha_hora_notificacion',)

    def has_add_permission(self, request):
        return False


@admin.register(ControlCalidad)
class ControlCalidadAdmin(admin.ModelAdmin):
    """Controles de calidad manuales — base para gráficas Levey-Jennings."""
    list_display  = ('empresa', 'equipo', 'parametro', 'valor', 'fecha_registro')
    list_filter   = ('empresa', 'equipo')
    search_fields = ('parametro',)
    date_hierarchy = 'fecha_registro'
    ordering      = ('-fecha_registro',)


@admin.register(CodigoParametroEquipo)
class CodigoParametroEquipoAdmin(admin.ModelAdmin):
    """Mapeo códigos analizador ↔ parámetros PRISLAB para HL7/ASTM."""
    list_display  = ('equipo', 'codigo_equipo', 'parametro', 'factor_conversion', 'activo')
    list_filter   = ('equipo', 'activo')
    search_fields = ('codigo_equipo', 'parametro__nombre')
    list_editable = ('activo',)
    autocomplete_fields = ['parametro']


@admin.register(ResultadoHL7)
class ResultadoHL7Admin(admin.ModelAdmin):
    """Mensajes HL7/ASTM crudos recibidos de analizadores — trazabilidad total."""
    list_display   = ('orden', 'parametro', 'valor_raw', 'unidad_raw', 'estado')
    list_filter    = ('estado',)
    search_fields  = ('orden__id', 'valor_raw', 'codigo_parametro_equipo__codigo_equipo')
    readonly_fields = ('mensaje_crudo',)

    def has_add_permission(self, request):
        return False


@admin.register(ResultadoHL7Huerfano)
class ResultadoHL7HuerfanoAdmin(admin.ModelAdmin):
    """Cola de cuarentena HL7 (Punto 13) — revisión QC."""
    list_display = ('creado', 'motivo', 'codigo_equipo', 'empresa', 'estado_revision', 'ip_equipo')
    list_filter = ('motivo', 'estado_revision', 'protocolo')
    search_fields = ('codigo_equipo', 'valor_raw', 'mensaje_contexto')
    readonly_fields = ('item_json', 'mensaje_contexto', 'creado')
    ordering = ('-creado',)

    def has_add_permission(self, request):
        return False


@admin.register(BitacoraMantenimiento)
class BitacoraMantenimientoAdmin(admin.ModelAdmin):
    """Bitácora de mantenimiento de equipos de laboratorio."""
    list_display   = ('equipo', 'empresa', 'descripcion', 'fecha_registro')
    list_filter    = ('empresa', 'equipo')
    search_fields  = ('equipo__nombre', 'descripcion')
    date_hierarchy = 'fecha_registro'
    ordering       = ('-fecha_registro',)


@admin.register(HistorialResultados)
class HistorialResultadosAdmin(admin.ModelAdmin):
    """Auditoría de cambios en resultados — trazabilidad forense."""
    list_display   = ('resultado_asociado', 'valor_anterior', 'valor_nuevo',
                      'usuario_responsable', 'fecha_hora_cambio', 'resultado_validado_previamente')
    list_filter    = ('resultado_validado_previamente',)
    search_fields  = ('motivo_cambio', 'usuario_responsable__username')
    date_hierarchy = 'fecha_hora_cambio'
    readonly_fields = tuple(HistorialResultados._meta.fields[f.name]
                            for f in HistorialResultados._meta.fields
                            if f.name != 'id') if False else ()

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(ResponsableSanitario)
class ResponsableSanitarioAdmin(admin.ModelAdmin):
    """Directores técnicos / responsables sanitarios del laboratorio (COFEPRIS)."""
    list_display  = ('usuario', 'cedula_profesional', 'especialidad',
                     'numero_autorizacion_sanitaria', 'activo')
    list_filter   = ('activo', 'especialidad')
    search_fields = ('usuario__username', 'cedula_profesional',
                     'numero_autorizacion_sanitaria')
