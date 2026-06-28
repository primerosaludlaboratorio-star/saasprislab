from django.contrib import admin
from .models import (
    CampanaMarketing,
    CuponMarketing,
    CuponUso,
    MarketingTrackingHit,
    ProspectoCRM,
    SeguimientoCRM,
)


@admin.register(CampanaMarketing)
class CampanaMarketingAdmin(admin.ModelAdmin):
    list_display = ('segmento', 'empresa', 'activa', 'creado_por', 'fecha_creacion')
    list_filter = ('activa', 'empresa')
    search_fields = ('segmento', 'mensaje_whatsapp')


@admin.register(CuponMarketing)
class CuponMarketingAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'empresa', 'porcentaje_descuento', 'paciente', 'fecha_creacion')
    list_filter = ('empresa',)
    search_fields = ('codigo', 'descripcion')


@admin.register(CuponUso)
class CuponUsoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cupon', 'empresa', 'paciente', 'orden', 'venta', 'creado_en')
    list_filter = ('empresa',)
    search_fields = ('idempotency_key', 'cupon__codigo')
    raw_id_fields = ('cupon', 'paciente', 'orden', 'venta')


class SeguimientoCRMInline(admin.TabularInline):
    model = SeguimientoCRM
    extra = 0
    fields = ('tipo', 'descripcion', 'realizado_por', 'fecha')
    readonly_fields = ('fecha',)


@admin.register(MarketingTrackingHit)
class MarketingTrackingHitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "creado_en",
        "event_key",
        "empresa",
        "campana",
        "paciente_id",
        "prospecto_id",
    )
    list_filter = ("event_key", "empresa")
    search_fields = ("event_key", "ip_hash", "user_agent_hash")
    readonly_fields = (
        "empresa",
        "campana",
        "paciente",
        "prospecto",
        "event_key",
        "meta",
        "user_agent_hash",
        "ip_hash",
        "creado_en",
    )
    date_hierarchy = "creado_en"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ProspectoCRM)
class ProspectoCRMAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "empresa",
        "asignado_a",
        "estado",
        "consentimiento_comunicaciones",
        "valor_estimado",
        "creado",
    )
    list_filter = ('empresa', 'estado', 'origen')
    search_fields = ('nombre', 'email', 'telefono')
    inlines = [SeguimientoCRMInline]
    date_hierarchy = 'creado'


@admin.register(SeguimientoCRM)
class SeguimientoCRMAdmin(admin.ModelAdmin):
    list_display = ('prospecto', 'tipo', 'realizado_por', 'fecha')
    list_filter = ('tipo',)
    search_fields = ('descripcion', 'prospecto__nombre')
