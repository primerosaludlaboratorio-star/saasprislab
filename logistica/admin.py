"""
Admin para el módulo de Logística.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import TransferenciaInventario, DetalleTransferencia, LogTransferencia, RutaRecoleccion, VisitaDomicilio


class DetalleTransferenciaInline(admin.TabularInline):
    """Inline para detalles de transferencia."""
    model = DetalleTransferencia
    extra = 0
    readonly_fields = ('cantidad_enviada', 'cantidad_recibida', 'costo_unitario')
    fields = ('producto', 'lote', 'cantidad_solicitada', 'cantidad_enviada', 'cantidad_recibida', 'costo_unitario', 'observaciones', 'orden')


class LogTransferenciaInline(admin.TabularInline):
    """Inline para logs de transferencia."""
    model = LogTransferencia
    extra = 0
    readonly_fields = ('fecha', 'usuario', 'estado_anterior', 'estado_nuevo', 'comentario', 'ip_address')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TransferenciaInventario)
class TransferenciaInventarioAdmin(admin.ModelAdmin):
    """Admin para transferencias de inventario."""
    list_display = (
        'folio',
        'estado_badge',
        'sucursal_origen',
        'sucursal_destino',
        'solicitado_por',
        'fecha_creacion',
        'fecha_envio_display',
        'fecha_recepcion_display'
    )
    list_filter = ('estado', 'fecha_creacion', 'sucursal_origen', 'sucursal_destino')
    search_fields = ('folio', 'motivo', 'observaciones_origen', 'observaciones_destino', 'solicitado_por__nombre_completo')
    readonly_fields = (
        'folio',
        'token_rastreo',
        'fecha_creacion',
        'fecha_envio',
        'enviado_por',
        'fecha_recepcion',
        'recibido_por',
        'total_productos_display'
    )
    date_hierarchy = 'fecha_creacion'
    inlines = [DetalleTransferenciaInline, LogTransferenciaInline]
    
    fieldsets = (
        ('Información General', {
            'fields': ('folio', 'token_rastreo', 'estado', 'empresa', 'sucursal_origen', 'sucursal_destino')
        }),
        ('Creación', {
            'fields': ('solicitado_por', 'fecha_creacion', 'motivo', 'observaciones_origen')
        }),
        ('Envío', {
            'fields': ('fecha_envio', 'enviado_por', 'transportista', 'guia_transporte')
        }),
        ('Recepción', {
            'fields': ('fecha_recepcion', 'recibido_por', 'fecha_completado', 'observaciones_destino')
        }),
        ('Totales', {
            'fields': ('total_productos_display',)
        })
    )
    
    def estado_badge(self, obj):
        """Muestra el estado con un badge de color."""
        colors = {
            'BORRADOR': 'secondary',
            'ENVIADO': 'primary',
            'EN_TRANSITO': 'info',
            'RECIBIDO': 'success',
            'CANCELADO': 'danger'
        }
        color = colors.get(obj.estado, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def fecha_envio_display(self, obj):
        """Muestra la fecha de envío formateada."""
        return obj.fecha_envio.strftime('%d/%m/%Y %H:%M') if obj.fecha_envio else '-'
    fecha_envio_display.short_description = 'Fecha Envío'
    
    def fecha_recepcion_display(self, obj):
        """Muestra la fecha de recepción formateada."""
        return obj.fecha_recepcion.strftime('%d/%m/%Y %H:%M') if obj.fecha_recepcion else '-'
    fecha_recepcion_display.short_description = 'Fecha Recepción'
    
    def total_productos_display(self, obj):
        """Muestra el total de productos."""
        total = obj.detalles.count()
        return format_html('<strong>{} productos</strong>', total)
    total_productos_display.short_description = 'Total Productos'
    
    def has_delete_permission(self, request, obj=None):
        """No permite eliminar transferencias ya enviadas."""
        if obj and obj.estado != 'BORRADOR':
            return False
        return super().has_delete_permission(request, obj)


@admin.register(DetalleTransferencia)
class DetalleTransferenciaAdmin(admin.ModelAdmin):
    """Admin para detalles de transferencia."""
    list_display = (
        'transferencia',
        'producto',
        'cantidad_solicitada',
        'cantidad_enviada',
        'cantidad_recibida',
        'lote'
    )
    list_filter = ('transferencia__estado',)
    search_fields = (
        'transferencia__folio',
        'producto__nombre',
        'lote__numero_lote'
    )
    readonly_fields = ('cantidad_recibida', 'cantidad_enviada', 'costo_unitario')
    
    def has_add_permission(self, request):
        """No permite agregar detalles directamente."""
        return False


@admin.register(LogTransferencia)
class LogTransferenciaAdmin(admin.ModelAdmin):
    """Admin para logs de transferencia (solo lectura)."""
    list_display = (
        'transferencia',
        'fecha',
        'usuario',
        'estado_anterior',
        'estado_nuevo',
        'ip_address'
    )
    list_filter = ('fecha', 'estado_nuevo')
    search_fields = (
        'transferencia__folio',
        'usuario__nombre_completo',
        'comentario'
    )
    readonly_fields = (
        'transferencia',
        'fecha',
        'usuario',
        'estado_anterior',
        'estado_nuevo',
        'comentario',
        'ip_address'
    )
    
    def has_add_permission(self, request):
        """No permite agregar logs manualmente."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permite eliminar logs."""
        return False


class VisitaDomicilioInline(admin.TabularInline):
    model = VisitaDomicilio
    extra = 0
    fields = ('orden', 'cita', 'direccion', 'estado', 'hora_programada')


@admin.register(RutaRecoleccion)
class RutaRecoleccionAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'chofer', 'sucursal_origen', 'sucursal_destino', 'hora_salida', 'fecha_creacion')
    list_filter = ('empresa',)
    search_fields = ('vehiculo', 'chofer')
    inlines = [VisitaDomicilioInline]


@admin.register(VisitaDomicilio)
class VisitaDomicilioAdmin(admin.ModelAdmin):
    list_display = ('ruta', 'orden', 'direccion', 'estatus', 'fecha_creacion')
    list_filter = ('estatus',)
    search_fields = ('direccion',)
