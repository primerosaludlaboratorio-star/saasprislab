"""
CONSULTORIO - Registro en Django Admin
========================================
"""
from django.contrib import admin
from .models import (
    AgendaCita, ConsultaMedica, Somatometria, NotaMedica,
    ConfiguracionMedico, Vademecum, ArchivoAdjuntoConsulta,
    ListaEspera, EncuestaSatisfaccion, SeguimientoTratamiento,
    AnalisisPatron, CajaConsultorio, CobroConsulta,
    ValeLiquidacion, IncidenciaSentinel,
    ReporteUltrasonido, ImagenUltrasonido,
)


@admin.register(AgendaCita)
class AgendaCitaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'fecha', 'hora', 'estatus')
    list_filter = ('estatus', 'fecha')
    search_fields = ('paciente__nombre_completo',)
    date_hierarchy = 'fecha'


@admin.register(ConsultaMedica)
class ConsultaMedicaLegacyAdmin(admin.ModelAdmin):
    """LEGACY - No usar. El modelo activo es core.ConsultaMedica."""
    list_display = ('paciente', 'medico', 'motivo', 'fecha_creacion')
    list_filter = ('empresa',)
    search_fields = ('paciente__nombre_completo',)
    readonly_fields = ('empresa', 'sucursal', 'cita', 'paciente', 'medico',
                       'motivo', 'exploracion_fisica', 'diagnostico_cie10',
                       'diagnostico_texto', 'tratamiento', 'fecha_creacion')


@admin.register(Somatometria)
class SomatometriaAdmin(admin.ModelAdmin):
    list_display = ('consulta', 'peso', 'talla', 'temperatura', 'presion_arterial', 'fecha_registro')
    search_fields = ('consulta__paciente__nombre_completo',)


@admin.register(NotaMedica)
class NotaMedicaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'titulo', 'fecha_creacion')
    search_fields = ('paciente__nombre_completo', 'titulo')


@admin.register(ConfiguracionMedico)
class ConfiguracionMedicoAdmin(admin.ModelAdmin):
    list_display = ('medico', 'agenda_activa', 'modo_cobro', 'precio_consulta_default')
    list_filter = ('agenda_activa', 'modo_cobro')


@admin.register(Vademecum)
class VademecumAdmin(admin.ModelAdmin):
    list_display = ('nombre_generico', 'principio_activo', 'via_administracion', 'embarazo_categoria')
    search_fields = ('nombre_generico', 'principio_activo')
    list_filter = ('via_administracion', 'embarazo_categoria')


@admin.register(ArchivoAdjuntoConsulta)
class ArchivoAdjuntoConsultaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'tipo', 'fecha_subida')
    list_filter = ('tipo',)
    search_fields = ('paciente__nombre_completo',)


@admin.register(ListaEspera)
class ListaEsperaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'prioridad', 'fecha_registro')
    list_filter = ('prioridad',)
    search_fields = ('paciente__nombre_completo', 'motivo')


@admin.register(EncuestaSatisfaccion)
class EncuestaSatisfaccionAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'puntuacion_nps', 'respondida', 'fecha_respuesta')
    list_filter = ('respondida', 'enviada')
    search_fields = ('paciente__nombre_completo',)


@admin.register(SeguimientoTratamiento)
class SeguimientoTratamientoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'tipo', 'canal', 'activo', 'fecha_creacion')
    list_filter = ('tipo', 'canal', 'activo')


@admin.register(AnalisisPatron)
class AnalisisPatronAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'periodo_inicio', 'periodo_fin', 'fecha_generacion')
    list_filter = ('tipo',)


@admin.register(CajaConsultorio)
class CajaConsultorioAdmin(admin.ModelAdmin):
    list_display = ('medico', 'fecha', 'estado', 'total_efectivo', 'total_tarjeta', 'total_transferencia')
    list_filter = ('estado', 'fecha')
    date_hierarchy = 'fecha'


@admin.register(CobroConsulta)
class CobroConsultaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'concepto', 'monto_total', 'metodo_pago', 'estado', 'fecha_cobro')
    list_filter = ('metodo_pago', 'estado')
    search_fields = ('paciente__nombre_completo',)


@admin.register(ValeLiquidacion)
class ValeLiquidacionAdmin(admin.ModelAdmin):
    list_display = ('folio_vale', 'cobro', 'medico', 'monto_adeudado', 'monto_liquidado', 'estado')
    list_filter = ('estado',)
    search_fields = ('folio_vale',)


@admin.register(IncidenciaSentinel)
class IncidenciaSentinelAdmin(admin.ModelAdmin):
    list_display = ('origen', 'url_afectada', 'metodo_http', 'codigo_http', 'severidad', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'severidad', 'codigo_http', 'origen')
    search_fields = ('url_afectada', 'tipo_excepcion', 'traceback_completo')
    date_hierarchy = 'fecha_creacion'
    readonly_fields = ('origen', 'url_afectada', 'metodo_http', 'codigo_http', 'tipo_excepcion',
                       'traceback_completo', 'datos_request', 'analisis_ia', 'fecha_creacion')


class ImagenUltrasonidoInline(admin.TabularInline):
    model = ImagenUltrasonido
    extra = 0
    fields = ('imagen', 'descripcion', 'orden_display')
    readonly_fields = ('fecha_captura',)


@admin.register(ReporteUltrasonido)
class ReporteUltrasonidoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'tipo', 'estado', 'fecha_estudio', 'empresa')
    list_filter = ('tipo', 'estado', 'empresa')
    search_fields = ('paciente__nombre_completo', 'medico__nombre_completo', 'conclusion')
    date_hierarchy = 'fecha_estudio'
    readonly_fields = ('fecha_estudio', 'fecha_firma')
    inlines = [ImagenUltrasonidoInline]
    fieldsets = (
        ('Información General', {
            'fields': ('empresa', 'paciente', 'medico', 'orden', 'tipo', 'estado', 'semanas_gestacion')
        }),
        ('Reporte', {
            'fields': ('hallazgos', 'conclusion', 'recomendaciones')
        }),
        ('Fechas', {
            'fields': ('fecha_estudio', 'fecha_firma'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ImagenUltrasonido)
class ImagenUltrasonidoAdmin(admin.ModelAdmin):
    list_display = ('reporte', 'descripcion', 'orden_display', 'fecha_captura')
    list_filter = ('reporte__tipo',)
    search_fields = ('reporte__paciente__nombre_completo',)
