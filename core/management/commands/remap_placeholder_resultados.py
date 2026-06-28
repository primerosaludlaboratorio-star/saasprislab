"""
Remapea ResultadoParametro aún ligados al analito placeholder de core.0058.

Tras `python manage.py ensamblar_lims_v75`, los `DetalleOrden` suelen apuntar a
analitos reales (o perfiles/paquetes expandibles). Este comando infiere destinos
por orden y alinea cada fila placeholder con el analito correspondiente.

Orden sugerido:
  1. ensamblar_lims_v75
  2. remap_placeholder_resultados --dry-run
  3. remap_placeholder_resultados

Código placeholder: __PRISLAB_MIG_0058__
"""
from __future__ import annotations

import logging
from typing import List, Sequence, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from lims.models import Analito

logger = logging.getLogger(__name__)

PLACEHOLDER_CODIGO = '__PRISLAB_MIG_0058__'


def _is_placeholder(analito: Analito | None) -> bool:
    return bool(analito and analito.codigo == PLACEHOLDER_CODIGO)


def _analitos_desde_detalle(detalle, placeholder_pk: int) -> List[Analito]:
    """Expande un DetalleOrden a analitos concretos (excluye placeholder)."""
    out: List[Analito] = []
    if detalle.analito_id:
        a = detalle.analito
        if a and a.pk != placeholder_pk and not _is_placeholder(a):
            out.append(a)
        return out
    if detalle.perfil_lims_id:
        for a in detalle.perfil_lims.analitos.all().order_by('codigo'):
            if a.pk != placeholder_pk and not _is_placeholder(a):
                out.append(a)
        return out
    if detalle.paquete_lims_id:
        for a in detalle.paquete_lims.get_todos_analitos().order_by('codigo'):
            if a.pk != placeholder_pk and not _is_placeholder(a):
                out.append(a)
    return out


def _dedupe_preserve_order(analitos: Sequence[Analito]) -> List[Analito]:
    seen: set[int] = set()
    res: List[Analito] = []
    for a in analitos:
        if a.pk not in seen:
            seen.add(a.pk)
            res.append(a)
    return res


class Command(BaseCommand):
    help = (
        'Remapea ResultadoParametro del placeholder 0058 (__PRISLAB_MIG_0058__) '
        'según DetalleOrden de cada orden (analito directo o expansión perfil/paquete).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo listar acciones; no escribe en la base de datos.',
        )
        parser.add_argument(
            '--orden-id',
            type=int,
            default=None,
            help='Limitar el proceso a una OrdenDeServicio (pk).',
        )
        parser.add_argument(
            '--delete-placeholder-if-unused',
            action='store_true',
            help=(
                'Si ningún ResultadoParametro ni DetalleOrden referencia el placeholder, '
                'elimina el registro lims.Analito placeholder (usar con precaución).'
            ),
        )
        parser.add_argument(
            '--fail-on-skip',
            action='store_true',
            help='Salir con código 1 si alguna orden no pudo remapearse (CI / auditoría).',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        orden_filtro = options['orden_id']
        delete_ph = options['delete_placeholder_if_unused']
        fail_on_skip = options['fail_on_skip']

        from core.models import DetalleOrden, ResultadoParametro

        ph = Analito.objects.filter(codigo=PLACEHOLDER_CODIGO).first()
        if not ph:
            self.stdout.write(self.style.WARNING(f'No existe analito con codigo={PLACEHOLDER_CODIGO!r}; nada que remapear.'))
            return

        ph_id = ph.pk
        qs_rp = ResultadoParametro.objects.filter(analito_id=ph_id).select_related('orden')
        if orden_filtro is not None:
            qs_rp = qs_rp.filter(orden_id=orden_filtro)

        total_ph = qs_rp.count()
        if total_ph == 0:
            self.stdout.write(self.style.SUCCESS('No hay ResultadoParametro en el placeholder.'))
            if delete_ph and not dry:
                self._maybe_delete_placeholder(ph, dry=False)
            elif delete_ph:
                self._maybe_delete_placeholder(ph, dry=True)
            return

        orden_ids = list(qs_rp.values_list('orden_id', flat=True).distinct())

        remapped = 0
        merged = 0
        skipped: List[Tuple[int, str]] = []

        for oid in orden_ids:
            rps = list(
                ResultadoParametro.objects.filter(orden_id=oid, analito_id=ph_id).order_by('pk')
            )
            detalles = list(DetalleOrden.objects.filter(orden_id=oid).order_by('pk'))
            targets: List[Analito] = []
            for d in detalles:
                targets.extend(_analitos_desde_detalle(d, ph_id))
            targets = _dedupe_preserve_order(targets)

            if not targets:
                skipped.append((oid, 'sin analitos reales en DetalleOrden (solo placeholder o vacío)'))
                continue
            if len(rps) != len(targets):
                skipped.append(
                    (
                        oid,
                        f'conteo RP placeholder={len(rps)} vs analitos inferidos={len(targets)} '
                        f'(requiere revisión manual o datos inconsistentes)',
                    )
                )
                continue

            pairs = list(zip(rps, targets, strict=True))
            for rp, dest in pairs:
                msg = f"orden={oid} RP pk={rp.pk} -> analito {dest.codigo!r} ({dest.nombre[:60]})"
                if dry:
                    self.stdout.write(f'[dry-run] {msg}')
                    remapped += 1
                    continue
                did_merge = self._apply_one_remap(rp, dest, ph_id)
                if did_merge:
                    merged += 1
                else:
                    remapped += 1
                self.stdout.write(self.style.SUCCESS(msg))

        self.stdout.write('')
        if dry:
            self.stdout.write(self.style.HTTP_INFO(f'[dry-run] Filas que se actualizarían/ fusionarían: {remapped}'))
        else:
            self.stdout.write(
                self.style.HTTP_INFO(
                    f'Actualizaciones directas: {remapped - merged}; fusiones con RP existente: {merged}'
                )
            )

        if skipped:
            self.stdout.write(self.style.WARNING('\nÓrdenes omitidas:'))
            for oid, reason in skipped:
                self.stdout.write(f'  orden_id={oid}: {reason}')

        if delete_ph:
            self._maybe_delete_placeholder(ph, dry=dry)

        if skipped and not dry and fail_on_skip:
            from django.core.management.base import CommandError

            raise CommandError(
                f'Quedaron {len(skipped)} orden(es) sin remapear automático. '
                'Revise la lista y corrija datos o remapee manualmente en admin.'
            )

    def _apply_one_remap(self, rp, dest: Analito, ph_id: int) -> bool:
        """
        Retorna True si se fusionó con un ResultadoParametro existente (y se borró rp).
        """
        from core.models import HistorialResultados, ResultadoParametro

        existing = (
            ResultadoParametro.objects.filter(orden_id=rp.orden_id, analito_id=dest.pk)
            .exclude(pk=rp.pk)
            .first()
        )
        if not existing:
            ResultadoParametro.objects.filter(pk=rp.pk).update(analito_id=dest.pk)
            return False

        with transaction.atomic():
            HistorialResultados.objects.filter(resultado_parametro_id=rp.pk).update(
                resultado_parametro_id=existing.pk
            )
            if (not (existing.valor or '').strip()) and (rp.valor or '').strip():
                existing.valor = rp.valor
                existing.save(update_fields=['valor'])
            rp.delete()
        return True

    def _maybe_delete_placeholder(self, ph: Analito, *, dry: bool) -> None:
        from core.models import DetalleOrden, ResultadoParametro

        n_rp = ResultadoParametro.objects.filter(analito_id=ph.pk).count()
        n_do = DetalleOrden.objects.filter(analito_id=ph.pk).count()
        if n_rp or n_do:
            self.stdout.write(
                self.style.WARNING(
                    f'Placeholder analito pk={ph.pk} aún referenciado '
                    f'(ResultadoParametro={n_rp}, DetalleOrden={n_do}); no se elimina.'
                )
            )
            return
        if dry:
            self.stdout.write(f'[dry-run] Se eliminaría lims.Analito placeholder pk={ph.pk}')
            return
        ph.delete()
        self.stdout.write(self.style.SUCCESS(f'Eliminado lims.Analito placeholder pk={ph.pk}'))
