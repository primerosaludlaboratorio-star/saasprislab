"""
FARMACIA - Registro en Django Admin
====================================
"""
from django.contrib import admin
from core.admin.tenant import TenantScopedAdmin
from .models import (
    Proveedor, MotivoAjuste, MovimientoInventario,
    MermaFarmacia, CierreTurnoFarmacia, AperturaCaja,
    DevolucionVenta, RegistroAntibiotico,
    LecturaCompraFarmacia,
)


@admin.register(Proveedor)
class ProveedorAdmin(TenantScopedAdmin):
    list_display = ('razon_social', 'nombre_comercial', 'rfc', 'categoria', 'telefono', 'dias_credito')
    list_filter = ('categoria', 'empresa')
    search_fields = ('razon_social', 'nombre_comercial', 'rfc')
    ordering = ('razon_social',)


@admin.register(MotivoAjuste)
class MotivoAjusteAdmin(TenantScopedAdmin):
    list_display = ('codigo', 'descripcion', 'requiere_autorizacion_gerente', 'activo')
    list_filter = ('requiere_autorizacion_gerente', 'activo')


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(TenantScopedAdmin):
    list_display = ('folio', 'tipo_movimiento', 'producto', 'cantidad', 'costo_unitario', 'usuario_responsable', 'fecha_movimiento')
    list_filter = ('tipo_movimiento', 'empresa', 'fecha_movimiento')
    search_fields = ('folio', 'producto__nombre', 'observaciones')
    date_hierarchy = 'fecha_movimiento'
    readonly_fields = ('folio', 'stock_anterior', 'stock_resultante', 'costo_total', 'costo_promedio_anterior', 'costo_promedio_nuevo', 'fecha_movimiento')
    ordering = ('-fecha_movimiento',)

    def has_change_permission(self, request, obj=None):
        return False  # Kardex es inmutable

    def has_delete_permission(self, request, obj=None):
        return False  # Kardex es inmutable


@admin.register(MermaFarmacia)
class MermaFarmaciaAdmin(TenantScopedAdmin):
    list_display = ('producto', 'cantidad', 'motivo', 'usuario_reporta', 'fecha_reporte')
    list_filter = ('motivo', 'empresa', 'fecha_reporte')
    search_fields = ('producto__nombre',)
    date_hierarchy = 'fecha_reporte'


@admin.register(CierreTurnoFarmacia)
class CierreTurnoFarmaciaAdmin(TenantScopedAdmin):
    list_display = ('folio', 'usuario_responsable', 'cerrado_por', 'fecha_cierre', 'efectivo_declarado', 'tarjeta_declarado')
    list_filter = ('empresa',)
    search_fields = ('folio',)


@admin.register(AperturaCaja)
class AperturaCajaAdmin(TenantScopedAdmin):
    list_display = ('folio', 'usuario_responsable', 'fecha_apertura', 'fondo_efectivo', 'activa')
    list_filter = ('activa', 'empresa')
    search_fields = ('folio',)


@admin.register(DevolucionVenta)
class DevolucionVentaAdmin(TenantScopedAdmin):
    list_display = ('folio', 'venta_original', 'tipo', 'motivo', 'monto_devolucion', 'autorizado', 'procesada', 'fecha_devolucion')
    list_filter = ('tipo', 'motivo', 'autorizado', 'procesada')
    search_fields = ('folio',)
    date_hierarchy = 'fecha_devolucion'


@admin.register(RegistroAntibiotico)
class RegistroAntibioticoAdmin(TenantScopedAdmin):
    list_display = ('folio', 'producto', 'cantidad_vendida', 'medico_nombre', 'medico_cedula', 'fecha_venta')
    list_filter = ('empresa', 'fecha_venta')
    search_fields = ('folio', 'producto__nombre', 'medico_cedula', 'medico_nombre')
    date_hierarchy = 'fecha_venta'


@admin.register(LecturaCompraFarmacia)
class LecturaCompraFarmaciaAdmin(TenantScopedAdmin):
    list_display = ('id', 'estado', 'empresa', 'usuario', 'confianza', 'creado_en', 'confirmado_en')
    list_filter = ('estado', 'empresa', 'creado_en')
    search_fields = ('id', 'datos_extraidos', 'texto_extraido')
    readonly_fields = ('empresa', 'usuario', 'imagen', 'texto_extraido', 'datos_extraidos', 'sugerencias', 'items_confirmados', 'estado', 'confianza', 'error', 'confirmado_en', 'confirmado_por', 'creado_en')
