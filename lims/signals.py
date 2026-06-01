"""
Sincronización catálogo LIMS (costo_lista) ↔ Nivel 4 (PrecioItem.precio_venta).

Si solo se actualiza `precio_venta` en PrecioItem, el cobro en recepción ya lo usa.
Si el usuario edita `costo_lista` en Analito/Perfil/Paquete y existe fila PrecioItem,
antes quedaba un `precio_venta` > 0 que tapaba el nuevo costo (_precio_venta_o_lista).
"""
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from lims.models import Analito, PaqueteLims, PerfilLims


def _cache_costo_lista_prev(sender, instance):
    if not instance.pk:
        instance._costo_lista_prev = None
        return
    row = (
        sender.objects_all.filter(pk=instance.pk)
        .values_list('costo_lista', flat=True)
        .first()
    )
    instance._costo_lista_prev = row


@receiver(pre_save, sender=Analito)
def analito_precio_cache_prev(sender, instance, **kwargs):
    _cache_costo_lista_prev(sender, instance)


@receiver(pre_save, sender=PerfilLims)
def perfil_precio_cache_prev(sender, instance, **kwargs):
    _cache_costo_lista_prev(sender, instance)


@receiver(pre_save, sender=PaqueteLims)
def paquete_precio_cache_prev(sender, instance, **kwargs):
    _cache_costo_lista_prev(sender, instance)


def _decimal_q(v):
    return Decimal(str(v or 0)).quantize(Decimal('0.01'))


def _costo_lista_cambio(instance) -> bool:
    prev = getattr(instance, '_costo_lista_prev', Ellipsis)
    if prev is Ellipsis:
        return True
    if prev is None:
        return True
    return _decimal_q(prev) != _decimal_q(instance.costo_lista)


def _sync_precioitem_desde_catalogo(instance) -> None:
    if not instance.pk or not _costo_lista_cambio(instance):
        return
    try:
        pi = instance.precio
    except ObjectDoesNotExist:
        return
    nuevo = _decimal_q(instance.costo_lista)
    if pi.precio_venta == nuevo:
        return
    pi.precio_venta = nuevo
    pi.save(update_fields=['precio_venta', 'fecha_actualiz'])


@receiver(post_save, sender=Analito)
def analito_sync_precioitem(sender, instance, **kwargs):
    _sync_precioitem_desde_catalogo(instance)


@receiver(post_save, sender=PerfilLims)
def perfil_sync_precioitem(sender, instance, **kwargs):
    _sync_precioitem_desde_catalogo(instance)


@receiver(post_save, sender=PaqueteLims)
def paquete_sync_precioitem(sender, instance, **kwargs):
    _sync_precioitem_desde_catalogo(instance)
