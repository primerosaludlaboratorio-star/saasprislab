"""
ADMIN V8.0 — SILOS DE INVENTARIO INDEPENDIENTES
Registra todos los modelos del módulo Inventario en el panel de administración.
La organización visual por departamento se define en core/admin.py mediante
AdminSite personalizado.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ProveedorCompras,
    # Silo Laboratorio
    CatalogoReactivoLab,
    ConsumoEstudioReactivo,
    LoteReactivoLab,
    SalidaAnaliticaLab,
    SalidaTecnicaLab,
    # Silo Consultorio
    CatalogoInsumoConsultorio,
    LoteInsumoConsultorio,
    SalidaConsumoConsultorio,
    # Silo Insumos Generales
    CatalogoInsumoGeneral,
    LoteInsumoGeneral,
    ValeRequisicion,
    LineaValeRequisicion,
    # Motor de Compras
    OrdenDeCompra,
    LineaOrdenCompra,
)


# =============================================================================
# PROVEEDOR
# =============================================================================
@admin.register(ProveedorCompras)
class ProveedorComprasAdmin(admin.ModelAdmin):
    list_display  = ["razon_social", "rfc", "tipo", "empresa", "activo", "fecha_alta"]
    list_filter   = ["tipo", "activo", "empresa"]
    search_fields = ["razon_social", "rfc", "nombre_comercial"]
    readonly_fields = ["fecha_alta"]


# =============================================================================
# SILO LABORATORIO
# =============================================================================
class ConsumoEstudioReactivoInline(admin.TabularInline):
    model  = ConsumoEstudioReactivo
    extra  = 0
    fields = ["analito", "cantidad_por_prueba", "unidad", "activo"]


@admin.register(CatalogoReactivoLab)
class CatalogoReactivoLabAdmin(admin.ModelAdmin):
    list_display  = [
        "codigo_interno", "nombre", "tipo", "unidad_medida",
        "stock_minimo", "requiere_cadena_frio", "activo", "empresa",
    ]
    list_filter   = ["tipo", "activo", "requiere_cadena_frio", "empresa"]
    search_fields = ["codigo_interno", "nombre", "fabricante", "referencia_fabricante"]
    inlines       = [ConsumoEstudioReactivoInline]

    def stock_actual(self, obj):
        stock = obj.get_stock_disponible()
        color = "red" if obj.necesita_reorden else "green"
        return format_html('<span style="color:{}">{}</span>', color, stock)
    stock_actual.short_description = "Stock Actual"


@admin.register(LoteReactivoLab)
class LoteReactivoLabAdmin(admin.ModelAdmin):
    list_display  = [
        "reactivo", "numero_lote", "fecha_caducidad",
        "cantidad_actual", "estado", "lote_aprobado_qc", "empresa",
    ]
    list_filter   = ["estado", "lote_aprobado_qc", "empresa"]
    search_fields = ["numero_lote", "reactivo__nombre", "reactivo__codigo_interno"]
    readonly_fields = ["fecha_recepcion", "costo_total_lote"]


@admin.register(SalidaAnaliticaLab)
class SalidaAnaliticaLabAdmin(admin.ModelAdmin):
    list_display  = ["lote", "orden", "cantidad_consumida", "idempotency_key", "validado_por", "fecha"]
    list_filter   = ["empresa", "fecha"]
    search_fields = ["orden__id", "lote__numero_lote", "idempotency_key"]
    readonly_fields = ["fecha", "idempotency_key"]


@admin.register(SalidaTecnicaLab)
class SalidaTecnicaLabAdmin(admin.ModelAdmin):
    list_display  = ["lote", "tipo", "cantidad", "registrado_por", "fecha"]
    list_filter   = ["tipo", "empresa"]
    search_fields = ["lote__numero_lote", "motivo"]
    readonly_fields = ["fecha"]


# =============================================================================
# SILO CONSULTORIO
# =============================================================================
@admin.register(CatalogoInsumoConsultorio)
class CatalogoInsumoConsultorioAdmin(admin.ModelAdmin):
    list_display  = ["codigo_interno", "nombre", "tipo", "unidad_medida", "stock_minimo", "activo", "empresa"]
    list_filter   = ["tipo", "activo", "empresa"]
    search_fields = ["codigo_interno", "nombre"]


@admin.register(LoteInsumoConsultorio)
class LoteInsumoConsultorioAdmin(admin.ModelAdmin):
    list_display  = ["insumo", "numero_lote", "fecha_caducidad", "cantidad_actual", "empresa"]
    list_filter   = ["empresa"]
    search_fields = ["numero_lote", "insumo__nombre"]
    readonly_fields = ["fecha_recepcion"]


@admin.register(SalidaConsumoConsultorio)
class SalidaConsumoConsultorioAdmin(admin.ModelAdmin):
    list_display  = ["lote", "cantidad", "cita", "registrado_por", "fecha"]
    list_filter   = ["empresa"]
    readonly_fields = ["fecha"]


# =============================================================================
# SILO INSUMOS GENERALES
# =============================================================================
@admin.register(CatalogoInsumoGeneral)
class CatalogoInsumoGeneralAdmin(admin.ModelAdmin):
    list_display  = ["codigo_interno", "nombre", "categoria", "area_principal", "stock_minimo", "activo", "empresa"]
    list_filter   = ["categoria", "area_principal", "activo", "empresa"]
    search_fields = ["codigo_interno", "nombre"]


@admin.register(LoteInsumoGeneral)
class LoteInsumoGeneralAdmin(admin.ModelAdmin):
    list_display  = ["insumo", "cantidad_actual", "precio_unitario_compra", "fecha_recepcion", "empresa"]
    list_filter   = ["empresa"]
    readonly_fields = ["fecha_recepcion"]


class LineaValeRequisicionInline(admin.TabularInline):
    model  = LineaValeRequisicion
    extra  = 0
    fields = ["insumo", "cantidad_solicitada", "cantidad_entregada", "lote_entregado", "observaciones"]


@admin.register(ValeRequisicion)
class ValeRequisicionAdmin(admin.ModelAdmin):
    list_display  = [
        "folio", "area_solicitante", "solicitado_por",
        "estado", "fecha_solicitud", "empresa",
    ]
    list_filter   = ["estado", "area_solicitante", "empresa"]
    search_fields = ["folio", "solicitado_por__username"]
    readonly_fields = ["fecha_solicitud"]
    inlines       = [LineaValeRequisicionInline]


# =============================================================================
# MOTOR DE COMPRAS
# =============================================================================
class LineaOrdenCompraInline(admin.TabularInline):
    model   = LineaOrdenCompra
    extra   = 0
    fields  = [
        "silo", "descripcion_snapshot", "cantidad_solicitada",
        "unidad_medida", "precio_unitario_estimado", "subtotal",
        "stock_al_generar", "cantidad_recibida",
    ]
    readonly_fields = ["subtotal"]


@admin.register(OrdenDeCompra)
class OrdenDeCompraAdmin(admin.ModelAdmin):
    list_display  = [
        "folio", "proveedor", "estado", "origen",
        "total", "generada_por", "fecha_generacion", "empresa",
    ]
    list_filter   = ["estado", "origen", "empresa"]
    search_fields = ["folio", "proveedor__razon_social"]
    readonly_fields = ["fecha_generacion", "subtotal", "iva", "total"]
    inlines       = [LineaOrdenCompraInline]
