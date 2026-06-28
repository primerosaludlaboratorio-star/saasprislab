"""
PRISLAB V6.0 - SIGNALS: AUDITORÍA Y TENANT
Auditoría forense en borrado crítico + auto-etiquetado de tenant.
"""
import logging

from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver


logger = logging.getLogger('signals')


# ==============================================================================
# CICLO 11: AUDITORÍA FORENSE EN BORRADO CRÍTICO (Paciente / Orden)
# ==============================================================================

@receiver(pre_delete, sender='core.Paciente', dispatch_uid='audit_log_paciente_delete')
def audit_log_paciente_delete(sender, instance, **kwargs):
    """Registra en AuditLog cuando se elimina un paciente (quién/cuándo desde vista; qué desde signal)."""
    try:
        from core.models import AuditLog
        empresa = getattr(instance, 'empresa', None)
        if not empresa:
            return  # Multi-tenant: no usar Empresa.objects.first(); solo auditar cuando hay empresa
        snapshot = {
            'id': instance.id,
            'nombre_completo': getattr(instance, 'nombre_completo', None) or getattr(instance, 'nombre', ''),
            'curp': getattr(instance, 'curp', None),
            'folio_expediente': getattr(instance, 'numero_expediente', None),
        }
        AuditLog.objects.create(
            empresa=empresa,
            usuario=None,
            accion='DELETE',
            modelo_afectado='Paciente',
            objeto_id=str(instance.id),
            datos_anteriores=snapshot,
            datos_nuevos=None,
        )
        logger.info(f"[AUDIT] Paciente eliminado (signal): #{instance.id} - {snapshot.get('nombre_completo', '')}")
    except Exception as e:
        logger.error(f"[AUDIT] Error en audit_log_paciente_delete: {e}")


@receiver(pre_delete, sender='core.OrdenDeServicio', dispatch_uid='audit_log_orden_delete')
def audit_log_orden_delete(sender, instance, **kwargs):
    """Registra en AuditLog cuando se elimina una orden de servicio."""
    try:
        from core.models import AuditLog
        empresa = getattr(instance, 'empresa', None)
        if not empresa:
            return  # Multi-tenant: no usar Empresa.objects.first(); solo auditar cuando hay empresa
        snapshot = {
            'id': instance.id,
            'folio_orden': getattr(instance, 'folio_orden', None),
            'estado': getattr(instance, 'estado', None),
            'total': str(instance.total) if getattr(instance, 'total', None) is not None else None,
            'paciente_id': instance.paciente_id if hasattr(instance, 'paciente_id') else None,
        }
        AuditLog.objects.create(
            empresa=empresa,
            usuario=None,
            accion='DELETE',
            modelo_afectado='OrdenDeServicio',
            objeto_id=str(instance.id),
            datos_anteriores=snapshot,
            datos_nuevos=None,
        )
        logger.info(f"[AUDIT] OrdenDeServicio eliminada (signal): #{instance.id} - {snapshot.get('folio_orden', '')}")
    except Exception as e:
        logger.error(f"[AUDIT] Error en audit_log_orden_delete: {e}")


# ==============================================================================
# SIGNAL: AUTO-ETIQUETADO DE TENANT (PILAR 1 — PRISLAB V6.0)
# ==============================================================================
# Garantiza que NINGÚN objeto se cree sin empresa cuando hay un usuario en sesión.
# Esto elimina el vector de "escape de tenant" por omisión de empresa en vistas.

# Lista de modelos que DEBEN tener empresa asignada automáticamente.
# Excluimos modelos globales (ConfiguracionModulos se crea manualmente, etc.)
_MODELOS_TENANT_AWARE = {
    'core.Paciente', 'core.OrdenDeServicio', 'core.Venta', 'core.Lote',
    'core.Producto', 'core.Empleado', 'core.Medico', 'core.Receta',
    'core.HistoriaClinica', 'core.ConsultaMedica', 'core.DetalleOrden',
    'core.DetalleVenta', 'core.Pago', 'core.Gasto', 'core.GastoOperativo',
    'core.MovimientoCaja', 'core.GastoCaja', 'core.TomaMuestra',
    'core.BitacoraEntregaResultados', 'core.ResultadoParametro',
    'laboratorio.Resultado',
    'farmacia.MovimientoInventario', 'farmacia.MermaFarmacia',
}


@receiver(pre_save, dispatch_uid='auto_etiquetado_tenant_v6')
def auto_assign_empresa(sender, instance, **kwargs):
    """
    SIGNAL UNIVERSAL: Si un objeto de un modelo tenant-aware se está guardando
    sin empresa, la asigna automáticamente desde el contexto del hilo.

    REGLAS:
    1. Solo actúa sobre modelos en _MODELOS_TENANT_AWARE.
    2. Solo asigna si empresa_id es None (respeta asignación manual).
    3. Solo asigna si hay empresa en el contexto del hilo actual.
    4. No actúa en objetos ya existentes (pk is not None and empresa_id set).
    """
    model_label = f'{sender._meta.app_label}.{sender.__name__}'
    if model_label not in _MODELOS_TENANT_AWARE:
        return

    if getattr(instance, 'empresa_id', None):
        return  # Ya tiene empresa, no sobrescribir

    try:
        from core.tenant import get_current_empresa
        empresa = get_current_empresa()
        if empresa:
            instance.empresa = empresa
            logger.debug(
                '[TENANT] Auto-etiquetado: %s → empresa=%s',
                model_label, empresa.pk
            )
    except Exception as exc:
        logger.warning('[TENANT] auto_assign_empresa falló: %s', exc)


@receiver(post_save, sender='core.Usuario', dispatch_uid='auto_empresa_nuevo_usuario_v6')
def auto_assign_empresa_nuevo_usuario(sender, instance, created, **kwargs):
    """
    Cuando se crea un nuevo usuario desde el Admin de un tenant,
    lo vincula automáticamente a la empresa del creador (hilo activo).

    Esto previene que un admin-cliente pueda crear usuarios sin empresa
    o asignarlos a otra empresa.
    """
    if not created:
        return

    if getattr(instance, 'empresa_id', None):
        return  # Ya tiene empresa

    # No tocar al superusuario PRISLAB
    if instance.is_superuser:
        return

    try:
        from core.tenant import get_current_empresa
        empresa = get_current_empresa()
        if empresa:
            instance.empresa = empresa
            # Guardamos solo el campo empresa para evitar recursión
            type(instance).objects.filter(pk=instance.pk).update(empresa=empresa)
            logger.info(
                '[TENANT] Nuevo usuario %s vinculado a empresa %s',
                instance.username, empresa.pk
            )
    except Exception as exc:
        logger.warning('[TENANT] auto_assign_empresa_nuevo_usuario falló: %s', exc)
