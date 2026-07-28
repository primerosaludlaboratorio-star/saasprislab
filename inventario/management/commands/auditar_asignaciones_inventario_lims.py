"""Audita la asignación BOM de inventario contra el catálogo LIMS humano."""

from django.core.management.base import BaseCommand

from inventario.models import ConsumoEstudioReactivo
from lims.veterinary_catalog import is_veterinary_catalog_text


class Command(BaseCommand):
    help = 'Audita fórmulas de consumo LIMS: analito, equipo, reactivo, empresa y aplicación.'

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, default=None)
        parser.add_argument('--strict', action='store_true', help='Falla también por advertencias clínicas.')

    def handle(self, *args, **options):
        qs = ConsumoEstudioReactivo.objects.select_related('analito', 'reactivo', 'equipo', 'empresa')
        if options.get('empresa_id'):
            qs = qs.filter(empresa_id=options['empresa_id'])

        errores = []
        advertencias = []
        for formula in qs.iterator():
            if formula.cantidad_por_prueba <= 0:
                errores.append(f'#{formula.pk}: cantidad_por_prueba debe ser mayor que cero')
            if formula.aplicacion == 'MUESTRA' and formula.analito_id is not None:
                errores.append(f'#{formula.pk}: MUESTRA no puede tener analito')
            if formula.aplicacion == 'ANALITO' and formula.analito_id is None:
                errores.append(f'#{formula.pk}: ANALITO requiere analito')
            if formula.analito_id and formula.analito.empresa_id != formula.empresa_id:
                errores.append(f'#{formula.pk}: analito de otra empresa')
            if formula.reactivo.empresa_id != formula.empresa_id:
                errores.append(f'#{formula.pk}: reactivo de otra empresa')
            if formula.activo and not formula.reactivo.activo:
                errores.append(f'#{formula.pk}: fórmula activa con reactivo inactivo')
            if formula.analito and is_veterinary_catalog_text(
                formula.analito.codigo,
                formula.analito.abreviatura,
                formula.analito.nombre,
                formula.analito.departamento,
            ):
                errores.append(f'#{formula.pk}: analito veterinario')
            if formula.analito and not formula.analito.activo:
                errores.append(f'#{formula.pk}: fórmula ligada a analito inactivo')
            if formula.analito and formula.analito.es_calculado and formula.activo:
                advertencias.append(
                    f'#{formula.pk}: analito calculado con fórmula física; no consumirá por diseño'
                )

        self.stdout.write(f'Fórmulas auditadas: {qs.count()}')
        if errores:
            for item in errores[:100]:
                self.stdout.write(self.style.ERROR('ERROR ' + item))
            if len(errores) > 100:
                self.stdout.write(self.style.ERROR(f'... y {len(errores) - 100} errores más'))
        if advertencias:
            for item in advertencias[:100]:
                self.stdout.write(self.style.WARNING('WARN ' + item))
        self.stdout.write(
            f'Resultado: errores={len(errores)} advertencias={len(advertencias)}'
        )
        if errores or (options.get('strict') and advertencias):
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS('Asignaciones de inventario/LIMS coherentes.'))
