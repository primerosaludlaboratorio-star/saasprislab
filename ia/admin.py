"""
Administración del Módulo de Inteligencia Artificial.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import CotizacionOCR, TranscripcionVoz


@admin.register(CotizacionOCR)
class CotizacionOCRAdmin(admin.ModelAdmin):
    """
    Administración de cotizaciones procesadas con OCR.
    """
    list_display = [
        'id',
        'fecha_creacion_formateada',
        'usuario_creador',
        'total_calculado',
        'confianza_badge',
        'estudios_count',
        'tiene_orden',
        'ver_imagen'
    ]
    
    list_filter = [
        'fecha_creacion',
        'usuario_creador',
        'confianza_promedio'
    ]
    
    search_fields = [
        'texto_extraido',
        'usuario_creador__username',
        'usuario_creador__first_name',
        'usuario_creador__last_name'
    ]
    
    readonly_fields = [
        'fecha_creacion',
        'texto_extraido',
        'estudios_detectados',
        'total_calculado',
        'confianza_promedio',
        'imagen_preview'
    ]
    
    fieldsets = (
        ('📊 Información General', {
            'fields': ('usuario_creador', 'fecha_creacion')
        }),
        ('📸 Imagen y OCR', {
            'fields': ('imagen_receta', 'imagen_preview', 'texto_extraido')
        }),
        ('🔍 Resultados del Procesamiento', {
            'fields': ('estudios_detectados', 'total_calculado', 'confianza_promedio')
        }),
        ('🔗 Relaciones', {
            'fields': ('orden_asociada',)
        }),
    )
    
    def fecha_creacion_formateada(self, obj):
        return obj.fecha_creacion.strftime('%d/%m/%Y %H:%M')
    fecha_creacion_formateada.short_description = 'Fecha'
    fecha_creacion_formateada.admin_order_field = 'fecha_creacion'
    
    def confianza_badge(self, obj):
        confianza = float(obj.confianza_promedio) * 100
        if confianza >= 80:
            color = 'success'
        elif confianza >= 60:
            color = 'warning'
        else:
            color = 'danger'
        return format_html(
            '<span class="badge badge-{}">{:.1f}%</span>',
            color, confianza
        )
    confianza_badge.short_description = 'Confianza'
    confianza_badge.admin_order_field = 'confianza_promedio'
    
    def estudios_count(self, obj):
        return len(obj.estudios_detectados)
    estudios_count.short_description = 'Estudios'
    
    def tiene_orden(self, obj):
        if obj.orden_asociada:
            return format_html(
                '<span class="badge badge-success">✓ #{}</span>',
                obj.orden_asociada.folio
            )
        return format_html('<span class="badge badge-secondary">Sin orden</span>')
    tiene_orden.short_description = 'Orden'
    
    def ver_imagen(self, obj):
        if obj.imagen_receta:
            return format_html(
                '<a href="{}" target="_blank" class="btn btn-sm btn-primary">Ver</a>',
                obj.imagen_receta.url
            )
        return '-'
    ver_imagen.short_description = 'Imagen'
    
    def imagen_preview(self, obj):
        if obj.imagen_receta:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 400px;" />',
                obj.imagen_receta.url
            )
        return 'Sin imagen'
    imagen_preview.short_description = 'Preview'
    
    def changelist_view(self, request, extra_context=None):
        """
        Agrega estadísticas al listado.
        """
        extra_context = extra_context or {}
        
        # Estadísticas generales
        stats = CotizacionOCR.objects.aggregate(
            total=Count('id'),
            promedio_confianza=Avg('confianza_promedio'),
            con_orden=Count('orden_asociada')
        )
        
        extra_context['stats'] = {
            'total': stats['total'] or 0,
            'promedio_confianza': round(float(stats['promedio_confianza'] or 0) * 100, 1),
            'con_orden': stats['con_orden'] or 0,
            'sin_orden': (stats['total'] or 0) - (stats['con_orden'] or 0)
        }
        
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(TranscripcionVoz)
class TranscripcionVozAdmin(admin.ModelAdmin):
    """
    Administración de transcripciones de audio.
    """
    list_display = [
        'id',
        'fecha_creacion_formateada',
        'usuario_creador',
        'duracion_formateada',
        'confianza_badge',
        'tiene_orden',
        'ver_audio'
    ]
    
    list_filter = [
        'fecha_creacion',
        'usuario_creador',
        'confianza_transcripcion'
    ]
    
    search_fields = [
        'texto_transcrito',
        'usuario_creador__username',
        'usuario_creador__first_name',
        'usuario_creador__last_name'
    ]
    
    readonly_fields = [
        'fecha_creacion',
        'texto_transcrito',
        'entidades_extraidas',
        'confianza_transcripcion',
        'duracion_audio'
    ]
    
    fieldsets = (
        ('📊 Información General', {
            'fields': ('usuario_creador', 'fecha_creacion')
        }),
        ('🎙️ Audio y Transcripción', {
            'fields': ('audio', 'duracion_audio', 'texto_transcrito', 'confianza_transcripcion')
        }),
        ('🔍 Entidades Extraídas', {
            'fields': ('entidades_extraidas',)
        }),
        ('🔗 Relaciones', {
            'fields': ('orden_asociada',)
        }),
    )
    
    def fecha_creacion_formateada(self, obj):
        return obj.fecha_creacion.strftime('%d/%m/%Y %H:%M')
    fecha_creacion_formateada.short_description = 'Fecha'
    fecha_creacion_formateada.admin_order_field = 'fecha_creacion'
    
    def duracion_formateada(self, obj):
        if obj.duracion_audio:
            mins = obj.duracion_audio // 60
            secs = obj.duracion_audio % 60
            return f'{mins}:{secs:02d}'
        return '-'
    duracion_formateada.short_description = 'Duración'
    
    def confianza_badge(self, obj):
        confianza = float(obj.confianza_transcripcion) * 100
        if confianza >= 80:
            color = 'success'
        elif confianza >= 60:
            color = 'warning'
        else:
            color = 'danger'
        return format_html(
            '<span class="badge badge-{}">{:.1f}%</span>',
            color, confianza
        )
    confianza_badge.short_description = 'Confianza'
    confianza_badge.admin_order_field = 'confianza_transcripcion'
    
    def tiene_orden(self, obj):
        if obj.orden_asociada:
            return format_html(
                '<span class="badge badge-success">✓ #{}</span>',
                obj.orden_asociada.folio
            )
        return format_html('<span class="badge badge-secondary">Sin orden</span>')
    tiene_orden.short_description = 'Orden'
    
    def ver_audio(self, obj):
        if obj.audio:
            return format_html(
                '<audio controls style="width: 200px;"><source src="{}" type="audio/mpeg"></audio>',
                obj.audio.url
            )
        return '-'
    ver_audio.short_description = 'Audio'
    
    def changelist_view(self, request, extra_context=None):
        """
        Agrega estadísticas al listado.
        """
        extra_context = extra_context or {}
        
        # Estadísticas generales
        stats = TranscripcionVoz.objects.aggregate(
            total=Count('id'),
            promedio_confianza=Avg('confianza_transcripcion'),
            con_orden=Count('orden_asociada')
        )
        
        extra_context['stats'] = {
            'total': stats['total'] or 0,
            'promedio_confianza': round(float(stats['promedio_confianza'] or 0) * 100, 1),
            'con_orden': stats['con_orden'] or 0,
            'sin_orden': (stats['total'] or 0) - (stats['con_orden'] or 0)
        }
        
        return super().changelist_view(request, extra_context=extra_context)
