"""
PRISLAB V5.0 - SIGNALS: FOLIOS
Generación automática de folios para órdenes de servicio.
"""
import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver


logger = logging.getLogger('signals')


# ==============================================================================
# SIGNAL: GENERAR FOLIO AUTOMÁTICO PARA ÓRDEN DE LABORATORIO
# ==============================================================================

@receiver(pre_save, sender='core.OrdenDeServicio', dispatch_uid='generar_folio_orden_unico')
def generar_folio_orden_automatico(sender, instance, **kwargs):
    """
    Genera automáticamente el folio de una orden de laboratorio si no existe.
    
    Formato: LAB-SUCURSAL-AÑO-CONSECUTIVO
    Ejemplo: LAB-001-2026-00123
    
    pre_save: Se ejecuta ANTES de guardar (para asignar el folio antes de insertar en DB)
    """
    from datetime import datetime
    from core.models import OrdenDeServicio
    
    # Solo si no tiene folio asignado
    if not instance.folio_orden:
        from django.utils import timezone as _tz
        año = _tz.localtime(_tz.now()).year
        sucursal_codigo = instance.empresa.codigo_sucursal if hasattr(instance.empresa, 'codigo_sucursal') else '001'
        
        # Contar órdenes existentes este año
        ultimas_ordenes = OrdenDeServicio.objects.filter(
            empresa=instance.empresa,
            fecha_creacion__year=año
        ).count()
        
        consecutivo = str(ultimas_ordenes + 1).zfill(5)
        instance.folio_orden = f"LAB-{sucursal_codigo}-{año}-{consecutivo}"
        
        logger.info(f"✓ Folio generado automáticamente: {instance.folio_orden}")
