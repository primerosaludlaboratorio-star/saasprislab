"""
Admin: 1. GESTIÓN DE IDENTIDAD SaaS
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.exceptions import NotRegistered
from core.models import (
    Empresa, Usuario, Producto, Lote, Venta, DetalleVenta, Pago, Medico, Receta, Gasto,
    DetalleOrden, GastoOperativo,
    Paciente, OrdenDeServicio, PagoOrden, MetaVenta,
    Convenio, ConvenioPrecioLims, CuentaPorCobrar, PagoCuentaPorCobrar, NotaCredito,
    # Nuevos modelos
    Sucursal, ConfiguracionModulos, Usuario_Sucursal, Usuario_Permiso_Extra,
    GastoCaja, MovimientoCaja, AjusteInventario, RecetaItem,
    PeriodoNomina, ReciboNomina,
    SolicitudAutorizacion,
    VoiceAuditLog,
    DocumentoCapacitacion, CapsulaSabiduria,
    Empleado, HorarioTrabajo, IncidenciaAsistencia,
    # Operacionales adicionales
    FacturaSAT, TomaMuestra, DatosFiscales, BitacoraTemperatura,
    MantenimientoEquipo, PreOrdenLaboratorio, DevolucionVenta, DiscountPolicy,
    # Clínico, expediente y bienestar
    HistoriaClinica, ConsultaMedica, ConsentimientoInformado,
    RegistroAsistencia, AuditLog, ForenseAcceso, NotificacionSistema,
    ConversacionBienestar, AlertaBienestar,
    MensajeInterno, IncidenciaOperativa, BuzonQuejas,
    # Certificados, notas clínicas, antecedentes
    CertificadoMedico, NotaClinicaSOAP, Antecedente, LogAccesoExpediente,
    # Evaluación y desempeño
    Competencia, EvaluacionDesempeno, DetalleEvaluacion, PlanDesarrollo, Bitacora39A,
    # Gobernanza IA
    UsoRecursosIA, ReglaLocalIA,
)


# ==============================================================================
# 1. GESTIÓN DE IDENTIDAD SaaS (EMPRESAS Y USUARIOS)
# ==============================================================================
@admin.register(Usuario)
class CustomUsuarioAdmin(UserAdmin):
    """Control de acceso por roles y pertenencia a empresa SaaS."""
    fieldsets = UserAdmin.fieldsets + (
        ('Identidad Institucional', {
            'fields': ('empresa', 'rol', 'departamento', 'cedula_interna')
        }),
        ('Permisos de IA', {
            'fields': ('puede_usar_ia', 'nivel_ia'),
            'description': 'Configuración de acceso a funciones de inteligencia artificial'
        }),
    )
    list_display = ('username', 'empresa', 'rol', 'nivel_ia', 'puede_usar_ia', 'departamento', 'is_staff')
    list_filter = ('empresa', 'rol', 'nivel_ia', 'puede_usar_ia', 'is_staff')
    search_fields = ('username', 'email', 'cedula_interna')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        eid = getattr(request.user, 'empresa_id', None)
        if eid:
            return qs.filter(empresa_id=eid)
        return qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and getattr(request.user, 'empresa_id', None):
            obj.empresa_id = request.user.empresa_id
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser and 'empresa' in form.base_fields and getattr(request.user, 'empresa_id', None):
            form.base_fields['empresa'].queryset = Empresa.objects.filter(pk=request.user.empresa_id)
        return form

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    """Configuración de la identidad institucional (PRISLAB, Clínica del Valle)."""
    list_display = ('nombre', 'rfc', 'periodo_vigencia', 'telefono')
    search_fields = ('nombre', 'rfc')


# Limpia una posible registración legacy inválida de Sucursal por Usuario_SucursalAdmin.
_legacy_admin = admin.site._registry.get(Sucursal)
if _legacy_admin and _legacy_admin.__class__.__name__ == 'Usuario_SucursalAdmin':
    try:
        admin.site.unregister(Sucursal)
    except NotRegistered:
        pass


@admin.register(Usuario_Permiso_Extra)
class Usuario_Permiso_ExtraAdmin(admin.ModelAdmin):
    """ABAC: Admin para overrides de permisos granulares (v1.1+)."""
    list_display = ('usuario', 'permiso_key', 'tipo_override', 'sucursal', 'esta_vigente', 'otorgado_por')
    list_filter = ('tipo_override', 'fecha_vencimiento', 'sucursal__empresa', 'otorgado_por')
    search_fields = ('usuario__username', 'permiso_key', 'razon_negocio')
    readonly_fields = ('fecha_inicio', 'otorgado_por')
    fieldsets = (
        ('Override', {
            'fields': ('usuario', 'permiso_key', 'tipo_override')
        }),
        ('Alcance', {
            'fields': ('sucursal',),
            'description': 'Dejar vacío = aplica en todas las sucursales'
        }),
        ('Validez', {
            'fields': ('fecha_inicio', 'fecha_vencimiento'),
            'description': 'Sin fecha de vencimiento = indefinido'
        }),
        ('Auditoría', {
            'fields': ('razon_negocio', 'otorgado_por'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        # Registrar quién otorgó el permiso extra
        if not change:  # Create
            obj.otorgado_por = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Admin de empresa solo ve overrides de su empresa
        eid = getattr(request.user, 'empresa_id', None)
        if eid:
            return qs.filter(usuario__empresa_id=eid)
        return qs.none()

# ==============================================================================
