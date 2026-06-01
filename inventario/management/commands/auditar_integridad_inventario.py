"""
Auditoría de integridad — inventario federado (lab / consultorio / generales).
No incluye farmacia ni core.Venta.

Uso:
    python manage.py auditar_integridad_inventario
    python manage.py auditar_integridad_inventario --strict
    python manage.py auditar_integridad_inventario --empresa=1
"""

from __future__ import annotations

import sys
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import F, Q, Sum

from inventario.models import (
    LoteReactivoLab,
    LoteInsumoConsultorio,
    LoteInsumoGeneral,
    SalidaAnaliticaLab,
    SalidaTecnicaLab,
    ValeRequisicion,
    LineaTraspasoInventario,
)


class Command(BaseCommand):
    help = 'Auditoría inventario federado (silos). --strict → exit 1 si hay errores críticos.'

    def add_arguments(self, parser):
        parser.add_argument('--empresa', type=int, default=None, help='Filtrar por ID empresa')
        parser.add_argument('--strict', action='store_true', help='Exit code 1 si hay errores')
        parser.add_argument(
            '--exit-code-warnings',
            action='store_true',
            help='Exit code 2 si solo hay advertencias (sin errores)',
        )

    def handle(self, *args, **options):
        empresa_id = options.get('empresa')
        strict = options['strict']
        exit_warnings = options['exit_code_warnings']

        errores = 0
        advertencias = 0

        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))
        self.stdout.write(self.style.MIGRATE_HEADING('AUDITORÍA INTEGRIDAD — Inventario federado'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))

        # --- 1. Idempotencia salidas analíticas ---
        self.stdout.write('\n[1] SalidaAnaliticaLab — idempotency_key obligatorio')
        qs_sal = SalidaAnaliticaLab.objects.all()
        if empresa_id:
            qs_sal = qs_sal.filter(empresa_id=empresa_id)
        sin_key = qs_sal.filter(Q(idempotency_key__isnull=True) | Q(idempotency_key='')).count()
        if sin_key:
            errores += sin_key
            self.stdout.write(
                self.style.ERROR(f'  [ERR] {sin_key} salida(s) analíticas sin idempotency_key')
            )
        else:
            self.stdout.write(self.style.SUCCESS('  [OK] Todas las salidas tienen idempotency_key'))

        # --- 2. Stock negativo (tres silos) ---
        self.stdout.write('\n[2] Lotes — cantidad_actual no negativa')

        def _neg(model, label):
            nonlocal errores
            q = model.objects.filter(cantidad_actual__lt=0)
            if empresa_id:
                q = q.filter(empresa_id=empresa_id)
            n = q.count()
            if n:
                errores += n
                self.stdout.write(self.style.ERROR(f'  [ERR] {label}: {n} lote(s) con stock negativo'))
                for row in q[:15]:
                    self.stdout.write(f'        · #{row.pk} cantidad_actual={row.cantidad_actual}')
                if n > 15:
                    self.stdout.write(f'        … y {n - 15} más')
            else:
                self.stdout.write(self.style.SUCCESS(f'  [OK] {label}'))

        _neg(LoteReactivoLab, 'Laboratorio')
        _neg(LoteInsumoConsultorio, 'Consultorio')
        _neg(LoteInsumoGeneral, 'Insumos generales')

        # --- 3. cantidad_actual > cantidad_inicial (lab) ---
        self.stdout.write('\n[3] Laboratorio — cantidad_actual vs cantidad_inicial')
        q_hi = LoteReactivoLab.objects.filter(cantidad_actual__gt=F('cantidad_inicial'))
        if empresa_id:
            q_hi = q_hi.filter(empresa_id=empresa_id)
        n_hi = q_hi.count()
        if n_hi:
            advertencias += n_hi
            self.stdout.write(
                self.style.WARNING(
                    f'  [WARN] {n_hi} lote(s) lab con cantidad_actual > cantidad_inicial'
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS('  [OK] Sin exceso sobre cantidad_inicial'))

        # --- 4. Kardex sintético lab ---
        self.stdout.write('\n[4] Laboratorio — kardex sintético (inicial − salidas analít./técnicas)')
        qs_trasp = LineaTraspasoInventario.objects.filter(silo='LAB')
        if empresa_id:
            qs_trasp = qs_trasp.filter(
                Q(traspaso__empresa_origen_id=empresa_id)
                | Q(traspaso__empresa_destino_id=empresa_id)
            )
        n_trasp = qs_trasp.count()

        if n_trasp:
            self.stdout.write(
                self.style.WARNING(
                    f'  [INFO] {n_trasp} línea(s) traspaso LAB en alcance; divergencias kardex pueden ser esperadas.'
                )
            )

        q_lotes = LoteReactivoLab.objects.all().select_related('reactivo')
        if empresa_id:
            q_lotes = q_lotes.filter(empresa_id=empresa_id)
        diverge = 0
        tol = Decimal('0.0001')
        for lote in q_lotes.iterator():
            sa = (
                SalidaAnaliticaLab.objects.filter(lote=lote).aggregate(s=Sum('cantidad_consumida'))['s']
                or Decimal('0')
            )
            st = (
                SalidaTecnicaLab.objects.filter(lote=lote).aggregate(s=Sum('cantidad'))['s']
                or Decimal('0')
            )
            ini = lote.cantidad_inicial
            if not isinstance(ini, Decimal):
                ini = Decimal(str(ini))
            cur = lote.cantidad_actual
            if not isinstance(cur, Decimal):
                cur = Decimal(str(cur))
            esperado = ini - sa - st
            if abs(esperado - cur) > tol:
                diverge += 1
                if diverge <= 10:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [WARN] Lote lab #{lote.pk} ({lote.reactivo.codigo_interno}): '
                            f'actual={cur} esperado(sin traspaso)={esperado}'
                        )
                    )
        if diverge > 10:
            self.stdout.write(self.style.WARNING(f'  [WARN] … {diverge - 10} lote(s) más con divergencia'))
        if diverge:
            advertencias += diverge
        else:
            self.stdout.write(self.style.SUCCESS('  [OK] Kardex sintético sin divergencias'))

        # --- 5. Vales ENTREGADO con líneas sin surtir ---
        self.stdout.write('\n[5] Insumos generales — vales ENTREGADO')
        qv = ValeRequisicion.objects.filter(estado='ENTREGADO')
        if empresa_id:
            qv = qv.filter(empresa_id=empresa_id)
        mal = 0
        for v in qv.iterator():
            pend = v.lineas.filter(cantidad_entregada__lt=F('cantidad_solicitada'))
            if pend.exists():
                mal += 1
                if mal <= 8:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [WARN] Vale {v.folio} (#{v.pk}): líneas con entrega < solicitada'
                        )
                    )
        if mal > 8:
            self.stdout.write(self.style.WARNING(f'  [WARN] … {mal - 8} vales más'))
        if mal:
            advertencias += mal
        else:
            self.stdout.write(self.style.SUCCESS('  [OK] Sin vales ENTREGADO con líneas pendientes'))

        # Resumen
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(f'Errores críticos: {errores} | Advertencias: {advertencias}')
        self.stdout.write('=' * 70)

        if errores:
            self.stdout.write(self.style.ERROR('Hay errores críticos (exit 1).'))
            sys.exit(1)
        if strict and advertencias:
            self.stdout.write(
                self.style.ERROR('STRICT: fallo por advertencias (kardex, vales, etc.).')
            )
            sys.exit(1)
        if exit_warnings and advertencias:
            self.stdout.write(self.style.WARNING('Solo advertencias → exit 2'))
            sys.exit(2)
