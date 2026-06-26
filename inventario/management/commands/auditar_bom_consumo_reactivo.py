"""
Auditoría de BOM / fórmulas ConsumoEstudioReactivo (ISO 15189).

Detecta concentración sospechosa en un mismo lims.Analito (p. ej. todo apuntando al PK 1
tras una migración mal resuelta), útil pre–Día D y post–inventario.0004.

  python manage.py auditar_bom_consumo_reactivo
  python manage.py auditar_bom_consumo_reactivo --analito-id 1
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import connection, OperationalError, ProgrammingError
from django.db.models import Count

from inventario.models import ConsumoEstudioReactivo


def _columna_analito_disponible():
    table = ConsumoEstudioReactivo._meta.db_table
    with connection.cursor() as cursor:
        try:
            cols = connection.introspection.get_table_description(cursor, table)
        except (OperationalError, ProgrammingError):
            # Tabla no existe aún (pre-migración) — DB introspection falla.
            return False
    return any(getattr(c, 'name', c[0]) == 'analito_id' for c in cols)


class Command(BaseCommand):
    help = 'Audita distribución de analitos en ConsumoEstudioReactivo (riesgo de mapeo incorrecto).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analito-id',
            type=int,
            default=None,
            help='Listar solo filas con este analito_id (ej. 1 para revisar el “parche PK1”).',
        )

    def handle(self, *args, **options):
        aid_filter = options.get('analito_id')
        if not _columna_analito_disponible():
            self.stdout.write(
                self.style.ERROR(
                    'La tabla aún no tiene analito_id. Ejecute: python manage.py migrate inventario'
                )
            )
            return

        qs = ConsumoEstudioReactivo.objects.all()
        if aid_filter is not None:
            qs = qs.filter(analito_id=aid_filter)

        total = ConsumoEstudioReactivo.objects.count()
        self.stdout.write(f'Total fórmulas ConsumoEstudioReactivo: {total}')

        if aid_filter is not None:
            n = qs.count()
            self.stdout.write(f'Filas con analito_id={aid_filter}: {n}')
            for row in qs.select_related('analito', 'empresa', 'reactivo').order_by('pk')[:200]:
                self.stdout.write(
                    f'  pk={row.pk} empresa={row.empresa_id} reactivo={row.reactivo_id} '
                    f'analito={row.analito_id} ({row.analito})'
                )
            if n > 200:
                self.stdout.write(self.style.WARNING('(mostrando primeras 200)'))
            return

        dist = Counter(
            ConsumoEstudioReactivo.objects.values_list('analito_id', flat=True)
        )
        top = dist.most_common(15)
        self.stdout.write('Top analito_id por número de fórmulas:')
        for analito_id, cnt in top:
            self.stdout.write(f'  analito_id={analito_id}: {cnt}')

        dup = (
            ConsumoEstudioReactivo.objects.values('empresa_id', 'analito_id', 'reactivo_id')
            .annotate(n=Count('id'))
            .filter(n__gt=1)
        )
        if dup.exists():
            self.stdout.write(self.style.ERROR(f'Duplicados (empresa, analito, reactivo): {dup.count()} grupos'))
        else:
            self.stdout.write(self.style.SUCCESS('Sin duplicados (empresa, analito, reactivo).'))

        first_id = min(dist.keys(), default=None)
        if first_id is not None and dist[first_id] == total and total > 3:
            self.stdout.write(
                self.style.ERROR(
                    'ALERTA: Todas las fórmulas comparten el mismo analito_id — revisar mapeo estudio→analito.'
                )
            )
