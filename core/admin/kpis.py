"""
Admin — Panel Ejecutivo (KPIs)
"""
from django.contrib import admin
from core.models import KPI_Snapshot, KPI_MetaAnual


@admin.register(KPI_Snapshot)
class KPI_SnapshotAdmin(admin.ModelAdmin):
    """Snapshots de KPIs diarios."""
    list_display = ('fecha', 'empresa', 'sucursal', 'ingresos_total', 'ordenes_completadas', 'tasa_cumplimiento')
    list_filter = ('empresa', 'sucursal', 'fecha')
    search_fields = ('empresa__nombre', 'sucursal__nombre')
    readonly_fields = ('calculado_en',)
    fieldsets = (
        ('Periodo', {
            'fields': ('empresa', 'sucursal', 'fecha')
        }),
        ('Ingresos', {
            'fields': ('ingresos_total', 'ingresos_lab', 'ingresos_consultorio', 'ingresos_farmacia'),
            'classes': ('collapse',)
        }),
        ('Órdenes', {
            'fields': ('ordenes_capturadas', 'ordenes_completadas', 'tasa_cumplimiento'),
            'classes': ('collapse',)
        }),
        ('Caja', {
            'fields': ('movimientos_ingreso', 'movimientos_egreso', 'saldo_caja'),
            'classes': ('collapse',)
        }),
        ('Finanzas', {
            'fields': ('cuentas_por_cobrar', 'margen_promedio'),
            'classes': ('collapse',)
        }),
        ('Operacional', {
            'fields': ('pacientes_nuevos', 'pacientes_atendidos', 'inventario_bajo_stock'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('cambios_registrados', 'calculado_en'),
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


@admin.register(KPI_MetaAnual)
class KPI_MetaAnualAdmin(admin.ModelAdmin):
    """Metas anuales de KPIs."""
    list_display = ('anio', 'empresa', 'sucursal', 'meta_ingresos', 'meta_ordenes', 'meta_margen')
    list_filter = ('empresa', 'anio')
    search_fields = ('empresa__nombre', 'sucursal__nombre')
    fieldsets = (
        ('Periodo', {
            'fields': ('empresa', 'sucursal', 'anio')
        }),
        ('Metas', {
            'fields': ('meta_ingresos', 'meta_ordenes', 'meta_margen')
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
