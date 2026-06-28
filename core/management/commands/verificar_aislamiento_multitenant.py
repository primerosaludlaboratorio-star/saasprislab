from django.core.management.base import BaseCommand, CommandError

from core.tenant import set_current_empresa, clear_current_empresa
from core.models import Empresa, Paciente, Producto, Lote, Venta, PagoOrden, OrdenDeServicio


class Command(BaseCommand):
    help = 'Verifica aislamiento multi-tenant row-level. Debe reportar 0 registros cross-tenant visibles.'

    @staticmethod
    def _count_cross_tenant_pagooren(origen_id, destino_id):
        return PagoOrden.objects_all.filter(
            orden__empresa_id=origen_id,
        ).filter(
            orden__empresa_id=destino_id,
        ).count()

    def add_arguments(self, parser):
        parser.add_argument('--empresa-origen', type=int, required=True)
        parser.add_argument('--empresa-destino', type=int, required=True)

    def handle(self, *args, **options):
        origen_id = options['empresa_origen']
        destino_id = options['empresa_destino']
        if origen_id == destino_id:
            raise CommandError('empresa-origen y empresa-destino deben ser distintos.')

        empresa_origen = Empresa.objects.filter(pk=origen_id).first()
        empresa_destino = Empresa.objects.filter(pk=destino_id).first()
        if not empresa_origen or not empresa_destino:
            raise CommandError('Una o ambas empresas no existen.')

        set_current_empresa(empresa_origen)
        try:
            resultados = {
                'Paciente': Paciente.objects.filter(empresa_id=destino_id).count(),
                'Producto': Producto.objects.filter(empresa_id=destino_id).count(),
                'Lote': Lote.objects.filter(empresa_id=destino_id).count(),
                'Venta': Venta.objects.filter(empresa_id=destino_id).count(),
                'OrdenDeServicio': OrdenDeServicio.objects.filter(empresa_id=destino_id).count(),
                'PagoOrden': self._count_cross_tenant_pagooren(origen_id, destino_id),
            }
        finally:
            clear_current_empresa()

        fuga_total = sum(resultados.values())
        self.stdout.write(self.style.NOTICE(f'Empresa origen: {empresa_origen.id} | Empresa destino: {empresa_destino.id}'))
        for modelo, total in resultados.items():
            self.stdout.write(f'{modelo}: {total}')

        if fuga_total != 0:
            raise CommandError(f'FUGA DETECTADA: {fuga_total} registros cross-tenant visibles.')

        self.stdout.write(self.style.SUCCESS('OK: 0 registros cross-tenant visibles con TenantManager row-level.'))
