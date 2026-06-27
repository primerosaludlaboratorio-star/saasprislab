"""
Admin: 3. VENTAS, FINANZAS Y AUDITORÍA
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
# 3. VENTAS, FINANZAS Y AUDITORÍA (Rigor SAT/Fiscal)
# ==============================================================================
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ('producto', 'lote_vendido', 'cantidad', 'precio_unitario', 'iva_aplicado', 'subtotal')
    can_delete = False

class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    readonly_fields = ('metodo', 'monto')
    can_delete = False

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    """Módulo de auditoría de ventas con sello digital y línea de captura."""
    # Bloqueamos edición de folios y sellos para integridad fiscal
    readonly_fields = ('linea_captura', 'sello_digital', 'fecha', 'folio_operacion')
    
    list_display = ('folio_operacion', 'fecha', 'paciente_nombre', 'total', 'usuario', 'estado')
    list_filter = ('fecha', 'estado', 'usuario__empresa', 'usuario')
    search_fields = ('folio_operacion', 'linea_captura', 'paciente_nombre', 'usuario__username')
    list_filter   = ('fecha', 'estado', 'usuario__empresa', 'usuario', 'sucursal')
    inlines = [DetalleVentaInline, PagoInline]
    
    fieldsets = (
        ('Encabezado Institucional', {
            'fields': ('empresa', 'usuario', ('folio_operacion', 'linea_captura'), 'fecha')
        }),
        ('Seguridad y Post-Venta', {
            'classes': ('collapse',), # Se oculta por defecto para limpieza visual
            'fields': ('sello_digital', 'poliza_aclaracion')
        }),
        ('Datos del Cliente y Control Normado', {
            'fields': ('paciente_nombre', 'receta', 'observaciones')
        }),
        ('Liquidación Financiera', {
            'fields': (('subtotal', 'impuestos_iva', 'redondeo'), 'total', 'estado')
        }),
    )

