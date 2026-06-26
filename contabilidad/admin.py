from django.contrib import admin
from .models import ClienteFacturacion, FacturaCFDI, ConceptoFactura, ImpuestoConcepto


@admin.register(ClienteFacturacion)
class ClienteFacturacionAdmin(admin.ModelAdmin):
    list_display = ('rfc', 'razon_social', 'email', 'regimen_fiscal', 'activo')
    search_fields = ('rfc', 'razon_social', 'email')
    list_filter = ('regimen_fiscal', 'activo')
    readonly_fields = ('fecha_creacion',)


class ConceptoFacturaInline(admin.TabularInline):
    model = ConceptoFactura
    extra = 1
    fields = ('numero_linea', 'descripcion', 'cantidad', 'valor_unitario')
    readonly_fields = ('importe',)


@admin.register(FacturaCFDI)
class FacturaCFDIAdmin(admin.ModelAdmin):
    list_display = ('folio_interno', 'empresa', 'cliente', 'fecha_emision', 'total', 'estado')
    list_filter = ('estado', 'tipo_comprobante', 'metodo_pago', 'fecha_emision', 'empresa')
    search_fields = ('folio_interno', 'uuid_sat', 'cliente__rfc', 'cliente__razon_social', 'empresa__nombre')
    readonly_fields = ('uuid', 'folio_interno', 'fecha_timbrado', 'uuid_sat', 'fecha_creacion')
    inlines = [ConceptoFacturaInline]
    date_hierarchy = 'fecha_emision'

    fieldsets = (
        ('Información General', {
            'fields': (
                'empresa',
                'cliente',
                'tipo_comprobante',
                'serie',
                'folio',
                'folio_interno',
                'orden_laboratorio',
                'pago_orden',
                'venta_farmacia',
            )
        }),
        ('Fechas', {
            'fields': ('fecha_emision', 'fecha_timbrado', 'fecha_creacion')
        }),
        ('Forma y Método de Pago', {
            'fields': ('forma_pago', 'metodo_pago')
        }),
        ('Montos', {
            'fields': ('subtotal', 'total_impuestos_trasladados', 'total')
        }),
        ('Estado', {
            'fields': ('estado', 'ultimo_error_pac', 'usuario_creo')
        }),
    )


@admin.register(ConceptoFactura)
class ConceptoFacturaAdmin(admin.ModelAdmin):
    list_display = ('factura', 'numero_linea', 'descripcion', 'cantidad', 'valor_unitario', 'importe')
    search_fields = ('factura__folio_interno', 'descripcion')
