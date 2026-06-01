from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
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

@admin.register(Sucursal)
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


# ==============================================================================
# OPERACIONES DE LABORATORIO
# ==============================================================================

@admin.register(TomaMuestra)
class TomaMuestraAdmin(admin.ModelAdmin):
    list_display = ('orden', 'tomada_por', 'fecha_toma', 'empresa')
    list_filter = ('empresa',)
    search_fields = ('orden__folio_orden',)
    date_hierarchy = 'fecha_toma'


@admin.register(BitacoraTemperatura)
class BitacoraTemperaturaAdmin(admin.ModelAdmin):
    list_display = ('area', 'temperatura_c', 'registrada_por', 'empresa')
    list_filter = ('empresa', 'area')
    search_fields = ('area',)


@admin.register(MantenimientoEquipo)
class MantenimientoEquipoAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'tipo', 'realizada_por', 'empresa')
    list_filter = ('tipo', 'empresa')
    search_fields = ('equipo',)


@admin.register(PreOrdenLaboratorio)
class PreOrdenLaboratorioAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico_solicitante', 'empresa')
    list_filter = ('empresa',)
    search_fields = ('paciente__nombre_completo',)


# ==============================================================================
# FISCAL Y DEVOLUCIONES
# ==============================================================================

@admin.register(FacturaSAT)
class FacturaSATAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'usuario', 'paciente', 'folio', 'uuid', 'estatus')
    list_filter = ('empresa', 'estatus')
    search_fields = ('uuid', 'folio', 'paciente__nombre_completo')
    readonly_fields = ('uuid', 'fecha_creacion', 'fecha_actualizacion')


@admin.register(DatosFiscales)
class DatosFiscalesAdmin(admin.ModelAdmin):
    list_display = ('razon_social', 'rfc', 'regimen_fiscal', 'empresa')
    list_filter = ('empresa', 'regimen_fiscal')
    search_fields = ('razon_social', 'rfc')


@admin.register(DevolucionVenta)
class DevolucionVentaAdmin(admin.ModelAdmin):
    list_display = ('venta_original', 'cantidad_devuelta', 'monto_devuelto', 'razon')
    list_filter = ('razon',)
    search_fields = ('venta_original__folio_operacion',)
    readonly_fields = ('monto_devuelto',)


@admin.register(DiscountPolicy)
class DiscountPolicyAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'porcentaje_descuento', 'requiere_autorizacion', 'activa')
    list_filter = ('empresa', 'activa', 'requiere_autorizacion')
    search_fields = ('nombre',)


# ==============================================================================
# EXPEDIENTE CLÍNICO Y CONSULTA MÉDICA
# ==============================================================================

@admin.register(HistoriaClinica)
class HistoriaClinicaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'numero_expediente', 'empresa')
    list_filter = ('empresa',)
    search_fields = ('paciente__nombre_completo', 'numero_expediente')
    readonly_fields = ('numero_expediente',)


@admin.register(ConsultaMedica)
class ConsultaMedicaCoreAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'empresa', 'fecha_creacion')
    list_filter = ('empresa',)
    search_fields = ('paciente__nombre_completo', 'medico__nombre_completo')
    date_hierarchy = 'fecha_creacion'
    readonly_fields = ('fecha_creacion',)


@admin.register(ConsentimientoInformado)
class ConsentimientoInformadoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'orden', 'empresa', 'acepta_privacidad', 'fecha_firma')
    list_filter = ('empresa', 'acepta_privacidad')
    search_fields = ('paciente__nombre_completo',)
    readonly_fields = ('hash_firma', 'ip_address', 'user_agent', 'fecha_firma')


# ==============================================================================
# ASISTENCIA, AUDITORÍA Y COMUNICACIÓN
# ==============================================================================

@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'tipo_registro', 'empresa', 'fecha_hora')
    list_filter = ('tipo_registro', 'empresa')
    search_fields = ('empleado__usuario__username',)
    date_hierarchy = 'fecha_hora'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'accion', 'empresa', 'ip_address', 'fecha_cierta')
    list_filter = ('accion', 'empresa')
    search_fields = ('usuario__username', 'modelo_afectado')
    readonly_fields = ('usuario', 'accion', 'empresa', 'ip_address', 'fecha_cierta',
                       'modelo_afectado', 'objeto_id', 'datos_anteriores', 'datos_nuevos',
                       'hash_verificacion')
    date_hierarchy = 'fecha_cierta'

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ForenseAcceso)
class ForenseAccesoAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'accion', 'empresa_id', 'paciente_id', 'orden_id', 'usuario_id', 'es_publico', 'ip_address')
    list_filter = ('accion', 'es_publico', 'empresa')
    search_fields = ('paciente_id', 'orden_id', 'usuario_id', 'token_prefix')
    readonly_fields = (
        'empresa', 'paciente_id', 'orden_id', 'usuario_id', 'accion', 'ip_address',
        'user_agent', 'token_prefix', 'es_publico', 'metadata', 'created_at',
    )
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificacionSistema)
class NotificacionSistemaAdmin(admin.ModelAdmin):
    list_display = ('destinatario', 'remitente', 'tipo', 'leida', 'empresa')
    list_filter = ('tipo', 'leida', 'empresa')
    search_fields = ('destinatario__username', 'mensaje')


@admin.register(MensajeInterno)
class MensajeInternoAdmin(admin.ModelAdmin):
    list_display = ('remitente', 'destinatario', 'tipo', 'leido', 'fecha')
    list_filter = ('tipo', 'leido')
    search_fields = ('remitente__username', 'destinatario__username', 'mensaje')
    readonly_fields = ('fecha',)


@admin.register(IncidenciaOperativa)
class IncidenciaOperativaAdmin(admin.ModelAdmin):
    list_display = ('tipo_incidencia', 'usuario_responsable', 'empresa', 'estado_revision', 'fecha_hora')
    list_filter = ('tipo_incidencia', 'estado_revision', 'empresa')
    search_fields = ('justificacion', 'usuario_responsable__username')


@admin.register(BuzonQuejas)
class BuzonQuejasAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'nombre_remitente', 'empresa', 'estado', 'fecha_creacion')
    list_filter = ('tipo', 'estado', 'empresa')
    search_fields = ('nombre_remitente', 'mensaje')
    readonly_fields = ('fecha_creacion',)


# ==============================================================================
# BIENESTAR (CONVERSACIONES Y ALERTAS)
# ==============================================================================

@admin.register(ConversacionBienestar)
class ConversacionBienestarAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'rol', 'estado_salud', 'privado', 'fecha_creacion')
    list_filter = ('rol', 'estado_salud', 'privado', 'empresa')
    search_fields = ('usuario__username',)
    readonly_fields = ('mensaje', 'fecha_creacion')
    date_hierarchy = 'fecha_creacion'

    def has_add_permission(self, request):
        return False


@admin.register(AlertaBienestar)
class AlertaBienestarAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'nivel', 'estado', 'fecha_alerta')
    list_filter = ('nivel', 'estado', 'empresa')
    search_fields = ('usuario__username',)
    readonly_fields = ('fecha_alerta', 'fecha_vista')


# ==============================================================================
# CERTIFICADOS, NOTAS CLÍNICAS Y ANTECEDENTES
# ==============================================================================

@admin.register(CertificadoMedico)
class CertificadoMedicoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'empresa')
    list_filter = ('empresa',)
    search_fields = ('paciente__nombre_completo', 'medico__nombre_completo')


@admin.register(NotaClinicaSOAP)
class NotaClinicaSOAPAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'empresa', 'fecha_creacion')
    list_filter = ('empresa',)
    search_fields = ('paciente__nombre_completo',)
    date_hierarchy = 'fecha_creacion'
    readonly_fields = ('fecha_creacion',)


@admin.register(Antecedente)
class AntecedenteAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'tipo', 'fecha_registro')
    list_filter = ('tipo',)
    search_fields = ('paciente__nombre_completo', 'descripcion')
    readonly_fields = ('fecha_registro',)


@admin.register(LogAccesoExpediente)
class LogAccesoExpedienteAdmin(admin.ModelAdmin):
    list_display = ('historia_clinica', 'usuario', 'fecha_acceso', 'ip_origen')
    list_filter = ('usuario',)
    search_fields = ('historia_clinica__paciente__nombre_completo', 'usuario__username')
    readonly_fields = ('historia_clinica', 'usuario', 'fecha_acceso', 'ip_origen')
    date_hierarchy = 'fecha_acceso'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ==============================================================================
# EVALUACIÓN DE DESEMPEÑO Y DESARROLLO
# ==============================================================================

@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'activa')
    list_filter = ('tipo', 'activa')
    search_fields = ('nombre',)


class DetalleEvaluacionInline(admin.TabularInline):
    model = DetalleEvaluacion
    extra = 0
    fields = ('competencia', 'calificacion', 'observacion')


@admin.register(EvaluacionDesempeno)
class EvaluacionDesempenoAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'evaluador', 'fecha', 'periodo', 'estado')
    list_filter = ('periodo', 'estado')
    search_fields = ('empleado__usuario__username', 'evaluador__username')
    inlines = [DetalleEvaluacionInline]
    date_hierarchy = 'fecha'


@admin.register(PlanDesarrollo)
class PlanDesarrolloAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'evaluacion_origen', 'fecha_creacion', 'fecha_limite', 'estado')
    list_filter = ('estado',)
    search_fields = ('empleado__usuario__username',)


@admin.register(Bitacora39A)
class Bitacora39AAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'periodo_semanal', 'fecha_inicio', 'fecha_fin')
    list_filter = ('periodo_semanal',)
    search_fields = ('empleado__usuario__username',)


# ==============================================================================
# MAQUILA, IMÁGENES Y PLANTILLAS
# ==============================================================================

from .models import (
    SalesReturn, EnvioMaquila, EstudioImagen, PlantillaNotaClinica,
)


@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    list_display = ('venta_original', 'empresa', 'tipo_devolucion', 'monto_reembolsado')
    list_filter = ('tipo_devolucion', 'empresa')
    search_fields = ('venta_original__folio_operacion',)


@admin.register(EnvioMaquila)
class EnvioMaquilaAdmin(admin.ModelAdmin):
    list_display = ('laboratorio_externo', 'empresa', 'guia_rastreo')
    list_filter = ('empresa',)
    search_fields = ('laboratorio_externo', 'guia_rastreo')


@admin.register(EstudioImagen)
class EstudioImagenAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico_interpretador', 'empresa')
    list_filter = ('empresa',)
    search_fields = ('paciente__nombre_completo',)


@admin.register(PlantillaNotaClinica)
class PlantillaNotaClinicaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre', 'descripcion')


# ==============================================================================
# MODELOS HUÉRFANOS RESCATADOS — CON DATOS REALES (PRISLAB V5.4)
# ==============================================================================

from .models import ResultadoParametro, DetalleVenta, DetalleVentaLote, Pago


class DetalleVentaLoteInline(admin.TabularInline):
    model = DetalleVentaLote
    extra = 0
    readonly_fields = ("lote", "cantidad_extraida")
    can_delete = False


@admin.register(ResultadoParametro)
class ResultadoParametroAdmin(admin.ModelAdmin):
    """Resultados por analito LIMS v7.5."""
    list_display  = ('orden', 'analito', 'valor', 'es_critico', 'fuera_rango',
                     'validado', 'fecha_captura')
    list_filter   = ('es_critico', 'fuera_rango', 'validado', 'metodo_captura')
    search_fields = ('analito__nombre', 'orden__folio_orden')
    readonly_fields = ('fecha_captura', 'fecha_validacion')
    date_hierarchy  = 'fecha_captura'
    ordering        = ('-fecha_captura',)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    """Detalle línea a línea de cada venta — 4 registros activos."""
    list_display  = ('venta', 'producto', 'cantidad', 'precio_unitario', 'subtotal')
    list_filter   = ('venta__empresa',)
    search_fields = ('producto__nombre', 'venta__folio_operacion')
    readonly_fields = ('subtotal',)
    inlines = (DetalleVentaLoteInline,)


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    """Pagos registrados — 4 registros activos."""
    list_display  = ('venta', 'metodo', 'monto', 'monto_efectivo', 'fecha_pago', 'referencia_pago')
    list_filter   = ('metodo', 'venta__empresa')
    search_fields = ('venta__folio_operacion', 'referencia_pago')
    date_hierarchy = 'fecha_pago'
    ordering       = ('-fecha_pago',)


# ─────────────────────────────────────────────────────────────────────────────
# GOBERNANZA DE IA
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(UsoRecursosIA)
class UsoRecursosIAAdmin(admin.ModelAdmin):
    """Log forense de consumo de tokens IA por empresa."""
    list_display  = (
        'empresa', 'fecha', 'get_tipo_display', 'tokens_total',
        'fuente_key', 'modelo_usado', 'latencia_ms', 'timestamp',
    )
    list_filter   = ('empresa', 'tipo_proceso', 'fuente_key', 'fecha')
    search_fields = ('empresa__nombre', 'referencia', 'modelo_usado')
    date_hierarchy = 'fecha'
    ordering       = ('-timestamp',)
    readonly_fields = (
        'empresa', 'fecha', 'tipo_proceso', 'tokens_entrada', 'tokens_salida',
        'tokens_total', 'fuente_key', 'modelo_usado', 'latencia_ms',
        'usuario_id', 'referencia', 'timestamp',
    )

    @admin.display(description='Proceso')
    def get_tipo_display(self, obj):
        return obj.get_tipo_proceso_display()

    def has_add_permission(self, request):
        return False  # Solo lectura — los registros los crea el sistema


@admin.register(ReglaLocalIA)
class ReglaLocalIAAdmin(admin.ModelAdmin):
    """Caché de reglas aprobadas por el QFB — aquí se aprueban o rechazan."""
    list_display  = (
        'empresa', 'get_ambito_display', 'clave', 'get_estado_display',
        'confianza', 'veces_usada', 'tokens_ahorrados',
        'aprobado_por', 'fecha_aprobacion',
    )
    list_filter   = ('empresa', 'ambito', 'estado')
    search_fields = ('clave', 'contexto_original', 'respuesta_ia', 'empresa__nombre')
    ordering       = ('-fecha_modificacion',)
    readonly_fields = (
        'contexto_original', 'respuesta_ia', 'veces_usada',
        'tokens_ahorrados', 'fecha_creacion', 'fecha_modificacion',
    )
    fieldsets = (
        ('Identificación', {'fields': ('empresa', 'ambito', 'clave', 'confianza')}),
        ('Contenido IA', {'fields': ('contexto_original', 'respuesta_ia')}),
        ('Override del QFB', {'fields': ('respuesta_local',)}),
        ('Estado y Aprobación', {
            'fields': ('estado', 'aprobado_por', 'fecha_aprobacion'),
        }),
        ('Estadísticas', {
            'fields': ('veces_usada', 'tokens_ahorrados', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',),
        }),
    )
    actions = ['aprobar_reglas', 'rechazar_reglas', 'marcar_obsoletas']

    @admin.action(description='✅ Aprobar reglas seleccionadas (QFB)')
    def aprobar_reglas(self, request, queryset):
        count = 0
        for regla in queryset.filter(estado=ReglaLocalIA.ESTADO_PROPUESTA):
            regla.aprobar(request.user)
            count += 1
        self.message_user(request, f'{count} regla(s) aprobada(s) y activada(s) en producción.')

    @admin.action(description='❌ Rechazar reglas seleccionadas')
    def rechazar_reglas(self, request, queryset):
        updated = queryset.update(estado=ReglaLocalIA.ESTADO_RECHAZADA)
        self.message_user(request, f'{updated} regla(s) rechazada(s).')

    @admin.action(description='🗄️ Marcar como obsoletas')
    def marcar_obsoletas(self, request, queryset):
        updated = queryset.update(estado=ReglaLocalIA.ESTADO_OBSOLETA)
        self.message_user(request, f'{updated} regla(s) marcada(s) como obsoletas.')

