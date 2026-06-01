"""
Rescate masivo multi-tenant (PRISLAB): asigna empresa principal a filas huérfanas
y sincroniza Producto.stock desde lotes vigentes.

Ejecutar solo en mantenimiento (management command / Cloud Run Job) con tenant_bypass().
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from django.db import transaction

from core.models.base import Empresa
from core.models.catalogos import Lote, Producto
from core.models.laboratorio import OrdenDeServicio
from core.models.pacientes import Paciente
from core.tenant import tenant_bypass
from lims.models import Analito, PaqueteLims, PerfilLims, PrecioItem


def run_rescate_total(
    empresa_id: int = 1,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Con tenant_bypass: cuenta/actualiza filas con empresa_id NULL y recalcula stock.

    Retorna dict con conteos por modelo y métricas de stock (sin escribir si dry_run).
    """
    out: dict[str, Any] = {
        'empresa_id': empresa_id,
        'dry_run': dry_run,
        'empresa_nombre': None,
        'antes': {},
        'actualizados': {},
        'stock': {},
    }

    with tenant_bypass():
        emp = Empresa.objects.filter(pk=empresa_id).first()
        if not emp:
            out['error'] = f'No existe Empresa pk={empresa_id}'
            return out
        out['empresa_nombre'] = str(emp)

        specs = [
            ('analitos', Analito),
            ('perfiles_lims', PerfilLims),
            ('paquetes_lims', PaqueteLims),
            ('precio_items', PrecioItem),
            ('productos', Producto),
            ('lotes', Lote),
            ('pacientes', Paciente),
            ('ordenes_servicio', OrdenDeServicio),
        ]

        for key, Model in specs:
            n = Model.objects_all.filter(empresa_id__isnull=True).count()
            out['antes'][key] = n

        if dry_run:
            hoy = date.today()
            agg: defaultdict[int, int] = defaultdict(int)
            for pid, cant in (
                Lote.objects_all.filter(cantidad__gt=0, fecha_caducidad__gte=hoy)
                .values_list('producto_id', 'cantidad')
            ):
                if pid:
                    agg[int(pid)] += int(cant or 0)
            out['stock']['productos_con_suma_lotes_positiva'] = sum(1 for v in agg.values() if v > 0)
            return out

        with transaction.atomic():
            for key, Model in specs:
                upd = Model.objects_all.filter(empresa_id__isnull=True).update(empresa_id=empresa_id)
                out['actualizados'][key] = upd

            hoy = date.today()
            agg = defaultdict(int)
            for pid, cant in (
                Lote.objects_all.filter(cantidad__gt=0, fecha_caducidad__gte=hoy)
                .values_list('producto_id', 'cantidad')
            ):
                if pid:
                    agg[int(pid)] += int(cant or 0)

            stock_pos = 0
            for pid in Producto.objects_all.values_list('pk', flat=True):
                total = int(agg.get(int(pid), 0))
                Producto.objects_all.filter(pk=pid).update(stock=total)
                if total > 0:
                    stock_pos += 1
            out['stock']['productos_actualizados'] = Producto.objects_all.count()
            out['stock']['productos_con_stock_positivo'] = stock_pos

    return out
