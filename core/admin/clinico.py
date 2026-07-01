"""
Admin: 4-8. CONTROL MÉDICO, LABORAL, LIMS
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.exceptions import AlreadyRegistered
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
# 4. CONTROL MÉDICO Y EGRESOS
# ==============================================================================
@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    """Administración de pacientes."""
    list_display = ('nombre_completo', 'telefono', 'email', 'tipo', 'fecha_registro', 'empresa')
    list_filter = ('tipo', 'fecha_registro', 'empresa')
    search_fields = (
        'nombre_completo', 'telefono', 'email',
        'curp', 'primer_nombre', 'primer_apellido', 'segundo_apellido',
    )
    date_hierarchy = 'fecha_registro'
    readonly_fields = ('fecha_registro',)
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre_completo', 'telefono', 'email', 'tipo')
        }),
        ('Datos Institucionales', {
            'fields': ('empresa', 'sucursal', 'fecha_registro')
        }),
        ('Datos Fiscales (Opcional)', {
            'fields': ('datos_fiscales',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'cedula_profesional', 'especialidad')
    list_filter = ('especialidad',)
    search_fields = ('nombre_completo', 'cedula_profesional')

@admin.register(Receta)
class RecetaAdmin(admin.ModelAdmin):
    list_display = ('folio_receta', 'medico', 'fecha_emision')
    list_filter = ('fecha_emision', 'medico')
    search_fields = ('folio_receta', 'medico__nombre_completo')

@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'concepto', 'monto', 'usuario')
    list_filter = ('fecha', 'empresa')
    search_fields = ('concepto',)

# ==============================================================================
# 5. MÓDULO DE LABORATORIO CLÍNICO (catalogo LIMS en app lims)
# ==============================================================================
@admin.register(OrdenDeServicio)
class OrdenDeServicioAdmin(admin.ModelAdmin):
    """Administración de órdenes de servicio de laboratorio."""
    list_display = ('folio_orden', 'paciente', 'fecha_creacion', 'estado', 'total', 'responsable_ingreso', 'empresa')
    list_filter = ('estado', 'fecha_creacion', 'empresa', 'tipo_servicio', 'estado_pago')
    search_fields = ('folio_orden', 'paciente__nombre_completo', 'notas_internas', 'diagnostico')
    date_hierarchy = 'fecha_creacion'
    readonly_fields = ('folio_orden', 'fecha_creacion')
    fieldsets = (
        ('Información de la Orden', {
            'fields': ('empresa', 'sucursal', 'paciente', 'responsable_ingreso', 'folio_orden', 'fecha_creacion', 'estado', 'tipo_servicio')
        }),
        ('Datos Clínicos', {
            'fields': ('diagnostico', 'notas_internas', 'hora_toma_muestra', 'hora_entrega_prometida')
        }),
        ('Liquidación', {
            'fields': ('total', 'total_original', 'descuento_monto', 'anticipo', 'estado_pago', 'tarifa')
        }),
        ('Cortesía / Beca', {
            'fields': ('es_cortesia', 'motivo_cortesia', 'autorizado_por_cortesia'),
            'classes': ('collapse',)
        }),
        ('Geolocalización (Opcional)', {
            'fields': ('latitud', 'longitud'),
            'classes': ('collapse',)
        }),
        ('Soft Delete', {
            'fields': ('deleted_at', 'motivo_eliminacion'),
            'classes': ('collapse',)
        }),
    )

class DetalleOrdenInline(admin.TabularInline):
    """Muestra los detalles dentro de la orden."""
    model = DetalleOrden
    extra = 0
    fields = (
        'analito', 'perfil_lims', 'paquete_lims', 'descripcion_linea',
        'estado_procesamiento', 'precio_momento', 'resultado', 'validado_por', 'fecha_validacion',
    )
    readonly_fields = ('precio_momento',)

class PagoOrdenInline(admin.TabularInline):
    """Muestra los pagos dentro de la orden."""
    model = PagoOrden
    extra = 0
    fields = ('monto_efectivo', 'monto_tarjeta', 'monto_transferencia', 'referencia_pago', 'fecha_pago', 'usuario_registro')
    readonly_fields = ('fecha_pago',)

OrdenDeServicioAdmin.inlines = [DetalleOrdenInline, PagoOrdenInline]

@admin.register(DetalleOrden)
class DetalleOrdenAdmin(admin.ModelAdmin):
    """Administración de detalles de órdenes de laboratorio."""
    list_display = ('orden', 'descripcion_linea', 'analito', 'perfil_lims', 'paquete_lims', 'estado_procesamiento', 'validado_por', 'fecha_validacion')
    list_filter = ('estado_procesamiento', 'valor_critico_confirmado', 'orden__estado')
    search_fields = ('orden__folio_orden', 'descripcion_linea', 'resultado')
    readonly_fields = ('orden', 'precio_momento')

@admin.register(PagoOrden)
class PagoOrdenAdmin(admin.ModelAdmin):
    """Administración de pagos de órdenes."""
    def monto_total(self, obj):
        """Calcula el monto total del pago."""
        return obj.monto_efectivo + obj.monto_tarjeta + obj.monto_transferencia
    monto_total.short_description = 'Monto Total'
    
    list_display = ('orden', 'monto_total', 'monto_efectivo', 'monto_tarjeta', 'monto_transferencia', 'fecha_pago', 'usuario_registro')
    list_filter = ('fecha_pago', 'usuario_registro')
    search_fields = ('orden__folio_orden', 'referencia_pago')
    date_hierarchy = 'fecha_pago'
    readonly_fields = ('fecha_pago',)
    fieldsets = (
        ('Orden', {
            'fields': ('orden',)
        }),
        ('Montos', {
            'fields': ('monto_efectivo', 'monto_tarjeta', 'monto_transferencia', 'referencia_pago')
        }),
        ('Metadatos', {
            'fields': ('fecha_pago', 'usuario_registro')
        }),
    )

# ==============================================================================
# MÓDULO MÉDICO: ULTRASONIDO Y NOTARIO DIGITAL (IA)
# ==============================================================================
# Modelos ReporteUltrasonido, ImagenUltrasonido y BitacoraConsultaIA no existen en core/models.py
# Comentados hasta que se implementen

# ==============================================================================
# ERP ADMINISTRATIVO: PROVEEDORES, INSUMOS Y GASTOS
# ==============================================================================
# Modelos Proveedor, CategoriaInsumo, Insumo, PrecioProveedor y RecetaEstudio no existen en core/models.py
# Comentados hasta que se implementen

@admin.register(GastoOperativo)
class GastoOperativoAdmin(admin.ModelAdmin):
    """Administración de gastos operativos."""
    list_display = ('categoria', 'monto', 'descripcion', 'usuario', 'fecha', 'empresa')
    list_filter = ('categoria', 'fecha', 'empresa', 'sucursal')
    search_fields = ('descripcion', 'categoria')
    date_hierarchy = 'fecha'
    fieldsets = (
        ('Información del Gasto', {
            'fields': ('empresa', 'sucursal', 'usuario', 'categoria', 'monto', 'descripcion', 'evidencia_foto')
        }),
        ('Metadatos', {
            'fields': ('fecha',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('fecha',)

@admin.register(MetaVenta)
class MetaVentaAdmin(admin.ModelAdmin):
    """Administración de metas de venta diarias por sucursal."""
    list_display = ('empresa', 'sucursal', 'fecha', 'monto_objetivo', 'creado_por', 'fecha_creacion')
    list_filter = ('empresa', 'sucursal', 'fecha', 'fecha_creacion')
    search_fields = ('sucursal', 'empresa__nombre')
    date_hierarchy = 'fecha'
    fieldsets = (
        ('Información de la Meta', {
            'fields': ('empresa', 'sucursal', 'fecha', 'monto_objetivo', 'creado_por')
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('fecha_creacion',)


# ==============================================================================
# CONVENIOS Y CUENTAS POR COBRAR
# ==============================================================================

class ConvenioPrecioInline(admin.TabularInline):
    model = ConvenioPrecioLims
    extra = 1
    fk_name = 'convenio'
    fields = ('analito', 'perfil_lims', 'paquete_lims', 'precio_convenio')


@admin.register(Convenio)
class ConvenioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'dias_credito', 'descuento_porcentaje', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre', 'rfc')
    inlines = [ConvenioPrecioInline]


class PagoCxCInline(admin.TabularInline):
    model = PagoCuentaPorCobrar
    extra = 0
    readonly_fields = ('fecha_pago',)


@admin.register(CuentaPorCobrar)
class CuentaPorCobrarAdmin(admin.ModelAdmin):
    list_display = ('folio', 'convenio', 'monto_total', 'saldo_pendiente', 'estado', 'fecha_vencimiento')
    list_filter = ('estado', 'convenio')
    search_fields = ('folio', 'concepto')
    inlines = [PagoCxCInline]
    date_hierarchy = 'fecha_emision'


@admin.register(NotaCredito)
class NotaCreditoAdmin(admin.ModelAdmin):
    list_display = ('folio', 'monto', 'motivo', 'aplicada', 'fecha_emision')
    list_filter = ('motivo', 'aplicada')
    search_fields = ('folio', 'descripcion')


# ==============================================================================
# INFRAESTRUCTURA Y CONFIGURACIÓN
# ==============================================================================

class SucursalAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'empresa', 'codigo_sucursal', 'telefono', 'activa',
        'gestion_inventario_activa',
    )
    list_filter = ('empresa', 'activa', 'gestion_inventario_activa')
    search_fields = ('nombre', 'codigo_sucursal', 'direccion')
    fieldsets = (
        (None, {
            'fields': (
                'empresa', 'nombre', 'codigo_sucursal', 'activa',
                'gestion_inventario_activa',
            ),
        }),
        ('Contacto', {
            'fields': ('direccion', 'telefono', 'email', 'responsable'),
        }),
    )

try:
    admin.site.register(Sucursal, SucursalAdmin)
except AlreadyRegistered:
    pass


@admin.register(ConfiguracionModulos)
class ConfiguracionModulosAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'modulo_laboratorio', 'modulo_farmacia',
                    'modulo_expediente_clinico', 'modulo_consulta_externa')
    list_filter = ('empresa',)


# ==============================================================================
# INVENTARIO Y CAJA
# ==============================================================================

@admin.register(GastoCaja)
class GastoCajaAdmin(admin.ModelAdmin):
    list_display = ('concepto', 'monto', 'usuario', 'fecha', 'empresa')
    list_filter = ('empresa', 'fecha')
    search_fields = ('concepto',)
    date_hierarchy = 'fecha'
    readonly_fields = ('fecha',)


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    list_display = ('caja_nombre', 'empresa', 'tipo_movimiento', 'concepto', 'monto', 'fecha_movimiento')
    list_filter = ('tipo_movimiento', 'empresa')
    search_fields = ('concepto', 'caja_nombre')


@admin.register(AjusteInventario)
class AjusteInventarioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'cantidad', 'tipo_movimiento', 'fecha', 'usuario')
    list_filter = ('tipo_movimiento',)
    search_fields = ('producto__nombre', 'observacion')


@admin.register(RecetaItem)
class RecetaItemAdmin(admin.ModelAdmin):
    list_display = ('receta', 'medicamento', 'texto_libre', 'cantidad')
    search_fields = ('medicamento__nombre', 'texto_libre')
    readonly_fields = ('precio_momento',)


# ==============================================================================
# NÓMINA Y RECURSOS HUMANOS
# ==============================================================================

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'puesto', 'fecha_ingreso', 'activo')
    list_filter = ('empresa', 'activo', 'puesto')
    search_fields = ('usuario__username', 'usuario__first_name', 'puesto')


@admin.register(HorarioTrabajo)
class HorarioTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'empleado', 'dia_semana', 'hora_entrada', 'hora_salida', 'activo')
    list_filter = ('empresa', 'dia_semana', 'activo')
    search_fields = ('nombre', 'empleado__usuario__username')


@admin.register(IncidenciaAsistencia)
class IncidenciaAsistenciaAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'tipo', 'estado', 'fecha_inicio', 'fecha_fin', 'dias')
    list_filter = ('tipo', 'estado', 'empresa')
    search_fields = ('empleado__usuario__username',)
    date_hierarchy = 'fecha_solicitud'


@admin.register(PeriodoNomina)
class PeriodoNominaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'frecuencia', 'fecha_inicio', 'fecha_fin', 'estado')
    list_filter = ('empresa', 'frecuencia', 'estado')
    search_fields = ('nombre',)
    date_hierarchy = 'fecha_inicio'


@admin.register(ReciboNomina)
class ReciboNominaAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'periodo', 'sueldo_base', 'neto_pagar', 'pagado')
    list_filter = ('pagado', 'periodo__empresa')
    search_fields = ('empleado__usuario__username',)
    readonly_fields = ('neto_pagar', 'creado', 'actualizado')


# ==============================================================================
# AUTORIZACIONES Y SEGURIDAD
# ==============================================================================

@admin.register(SolicitudAutorizacion)
class SolicitudAutorizacionAdmin(admin.ModelAdmin):
    list_display = ('usuario_solicita', 'tipo_accion', 'estado', 'fecha_solicitud', 'fecha_resolucion')
    list_filter = ('estado', 'tipo_accion')
    search_fields = ('usuario_solicita__username', 'descripcion')
    readonly_fields = ('token_aprobacion', 'fecha_solicitud')
    date_hierarchy = 'fecha_solicitud'


@admin.register(VoiceAuditLog)
class VoiceAuditLogAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'timestamp', 'intencion_detectada', 'tipo_comando', 'estado')
    list_filter = ('empresa', 'tipo_comando', 'estado')
    search_fields = ('usuario__username', 'intencion_detectada')
    readonly_fields = ('timestamp', 'usuario', 'empresa', 'url_actual', 'datos_pantalla',
                       'intencion_detectada', 'tipo_comando', 'estado')
    date_hierarchy = 'timestamp'


# ==============================================================================
# CAPACITACIÓN Y BIENESTAR
# ==============================================================================

@admin.register(DocumentoCapacitacion)
class DocumentoCapacitacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'empresa', 'version', 'activo', 'fecha_creacion')
    list_filter = ('tipo', 'empresa', 'activo')
    search_fields = ('titulo', 'descripcion')
    readonly_fields = ('contenido_texto', 'fecha_creacion', 'fecha_actualizacion')


@admin.register(CapsulaSabiduria)
class CapsulaSabiduriAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'empresa', 'documento_fuente', 'fecha_creacion')
    list_filter = ('empresa',)
    search_fields = ('titulo', 'contenido', 'tags')

