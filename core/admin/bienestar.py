"""
Admin: 9-11. EXPEDIENTE, BIENESTAR, COMUNI
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


