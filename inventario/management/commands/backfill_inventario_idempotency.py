"""
Backfill de idempotency_key en SalidaAnaliticaLab (reparación puntual).

La migración 0003 ya rellena históricos; este comando sirve si aparecen filas huérfanas
(p. ej. restore parcial de BD).

Uso:
    python manage.py backfill_inventario_idempotency --dry-run
    python manage.py backfill_inventario_idempotency --apply
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q

from inventario.models import SalidaAnaliticaLab


class Command(BaseCommand):
    help = 'Rellena idempotency_key faltante en SalidaAnaliticaLab (inventario federado).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Persistir cambios (sin esto solo cuenta)',
        )
        parser.add_argument('--empresa', type=int, default=None)

    def handle(self, *args, **options):
        apply_changes = options['apply']
        empresa_id = options.get('empresa')

        qs = SalidaAnaliticaLab.objects.filter(
            Q(idempotency_key__isnull=True) | Q(idempotency_key='')
        )
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)

        n = qs.count()
        self.stdout.write(self.style.MIGRATE_HEADING('BACKFILL idempotency_key — SalidaAnaliticaLab'))
        self.stdout.write(f'Filas sin clave: {n} | apply={apply_changes}')

        if not n:
            return

        if not apply_changes:
            self.stdout.write(self.style.WARNING('Dry-run: no se escribió nada. Use --apply.'))
            return

        updated = 0
        for row in qs.iterator():
            aid = row.analito_id or 0
            fid = row.formula_consumo_id or 0
            base = f'lab_backfill_o{row.orden_id}_a{aid}_f{fid}_l{row.lote_id}_p{row.pk}'
            row.idempotency_key = base[:190]
            row.save(update_fields=['idempotency_key'])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'Actualizadas: {updated}'))
