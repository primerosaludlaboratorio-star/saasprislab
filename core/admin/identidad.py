"""
Admin: 1. GESTIÓN DE IDENTIDAD SaaS
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from core.models import (
    Empresa, Usuario, Producto, Lote, Venta, DetalleVenta, Pago, Medico, Receta, Gasto,
    DetalleOrden, GastoOperativo,
    Paciente, OrdenDeServicio, PagoOrden, MetaVenta,
    Convenio, ConvenioPrecioLims, CuentaPorCobrar, PagoCuentaPorCobrar, NotaCredito,
    # Nuevos modelos
    Sucursal, ConfiguracionModulos,
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

# ==============================================================================
