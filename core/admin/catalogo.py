"""
Admin: 2. CATÁLOGO MAESTRO E INVENTARIO
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


# 2. CATÁLOGO MAESTRO E INVENTARIO (Rigor Nancy y COFEPRIS)
# ==============================================================================
class LoteInline(admin.TabularInline):
    """Muestra los lotes actuales dentro de la ficha del producto."""
    model = Lote
    extra = 0
    fields = ('numero_lote', 'fecha_caducidad', 'cantidad', 'ubicacion_fisica')
    readonly_fields = ('fecha_registro',)
    can_delete = True

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    """Ficha Técnica Detallada con agrupación lógica de campos."""
    save_on_top = True
    
    fieldsets = (
        ('Identificación Detallada (Marca/Línea)', {
            'fields': (('marca_laboratorio', 'linea', 'sublinea'), 'nombre', 'sustancia_activa', 'codigo_barras')
        }),
        ('Ficha Técnica Farmacéutica', {
            'fields': (('forma_farmaceutica', 'concentracion', 'presentacion'), 'clasificacion_sanitaria')
        }),
        ('Control de Precios y Cumplimiento', {
            'fields': (('precio_publico', 'iva_porcentaje'), 'stock', ('es_antibiotico', 'es_servicio'))
        }),
    )
    
    list_display = ('codigo_barras', 'nombre', 'sustancia_activa', 'marca_laboratorio', 'stock', 'precio_publico', 'clasificacion_sanitaria')
    list_filter = ('empresa', 'clasificacion_sanitaria', 'es_antibiotico', 'marca_laboratorio')
    search_fields = ('nombre', 'sustancia_activa', 'codigo_barras', 'marca_laboratorio')
    inlines = [LoteInline]

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    """Control de activos y trazabilidad de caducidades (PEPS)."""
    list_display = ('numero_lote', 'producto', 'fecha_caducidad', 'cantidad', 'ubicacion_fisica')
    list_filter = ('fecha_caducidad', 'ubicacion_fisica', 'producto__empresa')
    search_fields = ('numero_lote', 'producto__nombre', 'producto__codigo_barras')
    date_hierarchy = 'fecha_caducidad' # Barra de tiempo para caducidades

