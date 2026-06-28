"""
CMMS V8.2 — Admin de Django
Configurado con inlines para que el Director pueda gestionar
protocolos, pasos, árboles y nodos desde una sola pantalla.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ExpedienteEquipo, ProtocoloEquipo, PasoProtocolo,
    ArbolDiagnostico, NodoDiagnostico, ProcedimientoReparacion, PasoReparacion,
    EjecucionProtocolo, RespuestaPasoProtocolo, BypassChecklistAutorizacion,
    TicketMantenimientoCMMS, SalidaRefaccionMantenimiento, RegistroTCO,
)


# ── Inlines ───────────────────────────────────────────────────────────────────

class PasoProtocoloInline(admin.TabularInline):
    model = PasoProtocolo
    extra = 1
    fields = ('orden', 'titulo', 'tipo_validacion', 'es_critico',
              'tiempo_estimado_seg', 'imagen', 'video_url')
    ordering = ('orden',)


class PasoReparacionInline(admin.TabularInline):
    model = PasoReparacion
    extra = 1
    fields = ('orden', 'instruccion', 'silo_refaccion',
              'refaccion_content_type', 'refaccion_object_id',
              'cantidad_refaccion', 'unidad_refaccion', 'imagen')
    ordering = ('orden',)


class NodoDiagnosticoInline(admin.TabularInline):
    model = NodoDiagnostico
    extra = 1
    fields = ('padre', 'condicion_de_padre', 'tipo_nodo', 'texto',
              'nivel_requerido', 'lleva_a_procedimiento', 'nivel_escalamiento', 'orden')
    ordering = ('padre', 'orden')
    fk_name = 'arbol'


class RespuestaPasoInline(admin.TabularInline):
    model = RespuestaPasoProtocolo
    extra = 0
    readonly_fields = ('paso', 'validado', 'respuesta_texto',
                       'respuesta_valor', 'foto', 'timestamp')
    can_delete = False


class SalidaRefaccionInline(admin.TabularInline):
    model = SalidaRefaccionMantenimiento
    extra = 1
    fields = ('silo_origen', 'lote_content_type', 'lote_object_id',
              'cantidad_usada', 'unidad', 'registrado_por', 'observacion')


# ── ModelAdmins ───────────────────────────────────────────────────────────────

@admin.register(ExpedienteEquipo)
class ExpedienteEquipoAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'empresa', 'tipo_equipo', 'silo_refacciones',
                    'en_servicio', 'garantia_hasta', 'qr_link')
    list_filter  = ('empresa', 'tipo_equipo', 'en_servicio', 'silo_refacciones')
    search_fields = ('equipo__nombre', 'numero_serie', 'fabricante')
    readonly_fields = ('qr_uid', 'qr_link')

    def qr_link(self, obj):
        url = obj.get_qr_url()
        return format_html('<a href="{}" target="_blank">Ver QR ↗</a>', url)
    qr_link.short_description = "QR"


@admin.register(ProtocoloEquipo)
class ProtocoloEquipoAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'tipo_protocolo', 'equipo', 'bloquea_worklist',
                     'aplica_a_perfil', 'activo', 'version')
    list_filter   = ('tipo_protocolo', 'bloquea_worklist', 'activo', 'empresa')
    search_fields = ('nombre', 'modelo_equipo')
    inlines       = [PasoProtocoloInline]


@admin.register(ArbolDiagnostico)
class ArbolDiagnosticoAdmin(admin.ModelAdmin):
    list_display  = ('falla_descripcion', 'falla_codigo', 'expediente',
                     'empresa', 'activo', 'created_at')
    list_filter   = ('empresa', 'activo')
    search_fields = ('falla_descripcion', 'falla_codigo')
    inlines       = [NodoDiagnosticoInline]


@admin.register(ProcedimientoReparacion)
class ProcedimientoReparacionAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'tipo_componente', 'nivel_requerido',
                     'tiempo_estimado_min', 'requiere_paro_equipo', 'activo')
    list_filter   = ('tipo_componente', 'nivel_requerido', 'activo')
    search_fields = ('titulo', 'descripcion_tecnica')
    inlines       = [PasoReparacionInline]


@admin.register(EjecucionProtocolo)
class EjecucionProtocoloAdmin(admin.ModelAdmin):
    list_display  = ('protocolo', 'expediente', 'ejecutado_por',
                     'estado', 'fecha_inicio', 'duracion_real_seg')
    list_filter   = ('estado', 'empresa')
    readonly_fields = ('fecha_inicio', 'fecha_fin', 'duracion_real_seg', 'ip_address')
    inlines       = [RespuestaPasoInline]


@admin.register(BypassChecklistAutorizacion)
class BypassAdmin(admin.ModelAdmin):
    list_display  = ('ejecutado_por', 'autorizado_por', 'pasos_omitidos',
                     'pin_verificado', 'fecha', 'motivo_corto')
    list_filter   = ('pin_verificado',)
    readonly_fields = ('fecha', 'ip_autorizacion', 'pin_verificado')

    def motivo_corto(self, obj):
        return obj.motivo[:80]
    motivo_corto.short_description = "Motivo"


@admin.register(TicketMantenimientoCMMS)
class TicketCMMSAdmin(admin.ModelAdmin):
    list_display  = ('pk', 'titulo', 'expediente', 'estado',
                     'tipo_origen', 'nivel_escalamiento_actual',
                     'creado_por', 'fecha_apertura')
    list_filter   = ('estado', 'tipo_origen', 'nivel_escalamiento_actual', 'empresa')
    search_fields = ('titulo', 'descripcion')
    readonly_fields = ('fecha_apertura', 'fecha_cierre', 'tiempo_resolucion_min')
    inlines       = [SalidaRefaccionInline]


@admin.register(RegistroTCO)
class RegistroTCOAdmin(admin.ModelAdmin):
    list_display  = ('expediente', 'empresa', 'periodo_mes', 'periodo_anio',
                     'costo_refacciones', 'horas_inactividad',
                     'pruebas_procesadas', 'costo_por_prueba')
    list_filter   = ('empresa', 'periodo_anio')
    readonly_fields = ('generado_en', 'costo_por_prueba')
