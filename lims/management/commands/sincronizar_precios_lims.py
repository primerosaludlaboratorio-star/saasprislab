"""
LIMS v7.5 — Nivel 4: PrecioItem

Puebla / actualiza precio_venta desde costo_lista de cada entidad:

  - Analito con es_vendible_individualmente=True y activo
  - Todos los PerfilLims activos
  - Todos los PaqueteLims activos

Uso:
  python manage.py sincronizar_precios_lims
  python manage.py sincronizar_precios_lims --dry-run
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from lims.models import Analito, PaqueteLims, PerfilLims, PrecioItem


class Command(BaseCommand):
    help = 'Nivel 4: sincroniza PrecioItem desde costo_lista (CSV).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry = options['dry_run']
        if dry:
            self.stdout.write(self.style.WARNING('[DRY-RUN]\n'))

        na = np = nq = 0

        def precio_de(obj) -> Decimal:
            v = getattr(obj, 'costo_lista', None)
            if v is None:
                return Decimal('0.00')
            return Decimal(v).quantize(Decimal('0.01'))

        with transaction.atomic():
            for a in Analito.objects.filter(es_vendible_individualmente=True, activo=True):
                co = precio_de(a)
                if dry:
                    na += 1
                    continue
                PrecioItem.objects.update_or_create(
                    analito=a,
                    defaults={
                        'tipo': 'A',
                        'precio_venta': co,
                        'activo': True,
                        'perfil': None,
                        'paquete': None,
                    },
                )
                na += 1

            for p in PerfilLims.objects.filter(activo=True):
                co = precio_de(p)
                if dry:
                    np += 1
                    continue
                PrecioItem.objects.update_or_create(
                    perfil=p,
                    defaults={
                        'tipo': 'P',
                        'precio_venta': co,
                        'activo': True,
                        'analito': None,
                        'paquete': None,
                    },
                )
                np += 1

            for q in PaqueteLims.objects.filter(activo=True):
                co = precio_de(q)
                if dry:
                    nq += 1
                    continue
                PrecioItem.objects.update_or_create(
                    paquete=q,
                    defaults={
                        'tipo': 'Q',
                        'precio_venta': co,
                        'activo': True,
                        'analito': None,
                        'perfil': None,
                    },
                )
                nq += 1

        if dry:
            self.stdout.write(
                f'  [DRY] Analitos PDV: {na} | Perfiles: {np} | Paquetes: {nq}\n'
            )
            self.stdout.write(self.style.WARNING('[DRY-RUN] Sin cambios.'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'\n=== Nivel 4 (precios) ===\n'
            f'  PrecioItem tipo A (analito venta directa): {na}\n'
            f'  PrecioItem tipo P (perfil): {np}\n'
            f'  PrecioItem tipo Q (paquete): {nq}\n'
            f'  Total filas PrecioItem: {PrecioItem.objects.count()}\n'
        ))
