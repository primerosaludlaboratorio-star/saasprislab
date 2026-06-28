"""
Admin: 12-14. RRHH, EVALUACIÓN, GOBERNANZA
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

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


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

from core.models import (
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

from core.models import ResultadoParametro, DetalleVenta, DetalleVentaLote, Pago


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

