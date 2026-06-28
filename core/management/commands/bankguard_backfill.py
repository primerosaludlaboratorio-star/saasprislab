"""
Backfill Bankguard v1.14 — idempotency_key histórica y bandera inventario_descontado.

Uso (simulación):
    python manage.py bankguard_backfill --dry-run

Aplicar:
    python manage.py bankguard_backfill --apply

Opcional: solo ventas hasta una fecha (inventario_descontado=True para auditoría limpia):
    python manage.py bankguard_backfill --apply --fecha-corte-ventas=2025-12-31
"""
import logging
import uuid

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

_bankguard_log = logging.getLogger('bankguard')


class Command(BaseCommand):
    help = 'Backfill idempotency_key en MovimientoCaja y opcionalmente inventario_descontado en Ventas históricas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Persistir cambios (sin esto solo cuenta)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo reporte (equivalente a omitir --apply)',
        )
        parser.add_argument(
            '--fecha-corte-ventas',
            type=str,
            default='',
            help='YYYY-MM-DD: marcar inventario_descontado=True en ventas COMPLETADAS con fecha <= corte',
        )

    def handle(self, *args, **options):
        apply_changes = options['apply'] and not options.get('dry_run')
        fecha_corte = (options.get('fecha_corte_ventas') or '').strip()

        self.stdout.write(self.style.MIGRATE_HEADING('BANKGUARD BACKFILL v1.14'))
        _bankguard_log.info(
            'bankguard_backfill inicio apply=%s fecha_corte_ventas=%r',
            apply_changes,
            fecha_corte or None,
        )

        try:
            from core.models import MovimientoCaja, Venta

            sin_idem = MovimientoCaja.objects.filter(Q(idempotency_key__isnull=True) | Q(idempotency_key=''))
            n_mov = sin_idem.count()
            self.stdout.write(f"MovimientoCaja sin idempotency_key: {n_mov}")

            n_ventas = 0
            if fecha_corte:
                from datetime import datetime

                fc = datetime.strptime(fecha_corte, '%Y-%m-%d').date()
                n_ventas = Venta.objects.filter(
                    estado='COMPLETADA',
                    inventario_descontado=False,
                    fecha__date__lte=fc,
                ).count()
                self.stdout.write(
                    f"Ventas COMPLETADAS a marcar inventario_descontado=True (fecha<={fecha_corte}): {n_ventas}"
                )

            _bankguard_log.info(
                'bankguard_backfill conteo movimientos_sin_idem=%s ventas_candidatas=%s',
                n_mov,
                n_ventas,
            )

            if not apply_changes:
                self.stdout.write(self.style.WARNING('Modo simulación. Use --apply para ejecutar.'))
                _bankguard_log.info('bankguard_backfill sin --apply: solo simulacion')
                return

            with transaction.atomic():
                batch = []
                updated_mov = 0
                for mov in sin_idem.iterator(chunk_size=500):
                    mov.idempotency_key = f'backfill-{uuid.uuid4().hex}'
                    batch.append(mov)
                    if len(batch) >= 500:
                        MovimientoCaja.objects.bulk_update(batch, ['idempotency_key'])
                        updated_mov += len(batch)
                        batch = []
                if batch:
                    MovimientoCaja.objects.bulk_update(batch, ['idempotency_key'])
                    updated_mov += len(batch)
                self.stdout.write(self.style.SUCCESS(f"Actualizados MovimientoCaja: {updated_mov}"))

                n_up = 0
                if fecha_corte:
                    from datetime import datetime

                    fc = datetime.strptime(fecha_corte, '%Y-%m-%d').date()
                    n_up = Venta.objects.filter(
                        estado='COMPLETADA',
                        inventario_descontado=False,
                        fecha__date__lte=fc,
                    ).update(inventario_descontado=True)
                    self.stdout.write(self.style.SUCCESS(f"Ventas marcadas inventario_descontado: {n_up}"))

            _bankguard_log.info(
                'bankguard_backfill aplicado movimientos_actualizados=%s ventas_marcadas=%s',
                updated_mov,
                n_up,
            )
            self.stdout.write(self.style.SUCCESS('Backfill finalizado.'))
            _bankguard_log.info('bankguard_backfill fin OK')
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en handle (bankguard_backfill.py)")
            _bankguard_log.exception('bankguard_backfill ERROR: %s', exc)
            raise