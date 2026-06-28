"""
Rescate PDV Farmacia: asigna tenant único a Producto/Lote y recalcula stock desde lotes vigentes.

Uso (producción, sin tráfico web):
  python manage.py rescate_farmacia_tenant --empresa-id=1
  python manage.py rescate_farmacia_tenant --empresa-id=1 --dry-run
"""
from collections import defaultdict
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models.catalogos import Lote, Producto
from core.tenant import tenant_bypass


class Command(BaseCommand):
    help = 'Asigna empresa_id a Producto/Lote (objects_all) y sincroniza Producto.stock desde lotes vigentes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            default=1,
            help='PK de core.Empresa (default: 1 PRISLAB).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo imprimir conteos, sin escribir en BD.',
        )

    def handle(self, *args, **options):
        eid = options['empresa_id']
        dry = options['dry_run']

        self.stdout.write(self.style.WARNING(
            f'=== Rescate farmacia tenant (empresa_id={eid}, dry_run={dry}) ===\n'
        ))

        with tenant_bypass():
            n_prod = Producto.objects_all.count()
            n_lote = Lote.objects_all.count()
            prod_sin_empresa = Producto.objects_all.filter(empresa_id__isnull=True).count()
            lote_sin_empresa = Lote.objects_all.filter(empresa_id__isnull=True).count()

            self.stdout.write(
                f'  Productos totales: {n_prod} | sin empresa_id: {prod_sin_empresa}\n'
                f'  Lotes totales:     {n_lote} | sin empresa_id: {lote_sin_empresa}\n'
            )

            if dry:
                hoy = date.today()
                agg = defaultdict(int)
                for pid, cant in (
                    Lote.objects_all.filter(cantidad__gt=0, fecha_caducidad__gte=hoy)
                    .values_list('producto_id', 'cantidad')
                ):
                    if pid:
                        agg[pid] += int(cant or 0)
                con_stock_pos = sum(1 for v in agg.values() if v > 0)
                self.stdout.write(
                    f'  [DRY] Productos con suma lotes vigentes > 0: {con_stock_pos}\n'
                )
                self.stdout.write(self.style.WARNING('[DRY-RUN] Sin cambios en BD.'))
                return

            with transaction.atomic():
                upd_p = Producto.objects_all.update(empresa_id=eid)
                upd_l = Lote.objects_all.update(empresa_id=eid)

                hoy = date.today()
                agg = defaultdict(int)
                for pid, cant in (
                    Lote.objects_all.filter(cantidad__gt=0, fecha_caducidad__gte=hoy)
                    .values_list('producto_id', 'cantidad')
                ):
                    if pid:
                        agg[pid] += int(cant or 0)

                stock_pos = 0
                for pid in Producto.objects_all.values_list('pk', flat=True):
                    total = int(agg.get(pid, 0))
                    Producto.objects_all.filter(pk=pid).update(stock=total)
                    if total > 0:
                        stock_pos += 1

            self.stdout.write(self.style.SUCCESS(
                f'\n=== Rescate aplicado ===\n'
                f'  Filas Producto actualizadas (empresa_id={eid}): {upd_p}\n'
                f'  Filas Lote actualizadas (empresa_id={eid}):     {upd_l}\n'
                f'  Productos con stock > 0 tras sincronizar:      {stock_pos}\n'
            ))
