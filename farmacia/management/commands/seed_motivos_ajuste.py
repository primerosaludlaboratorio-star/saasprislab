"""
Comando para sembrar motivos de ajuste predeterminados en todas las empresas.
Idempotente: safe to run multiple times.
"""
from django.core.management.base import BaseCommand
from core.models import Empresa
from farmacia.models import MotivoAjuste

MOTIVOS_DEFAULT = [
    {
        'codigo': 'CORRECCION_ERROR',
        'descripcion': 'Corrección de error de captura',
        'requiere_autorizacion_gerente': False,
        'es_responsabilidad_empleado': False,
    },
    {
        'codigo': 'MERMA_CADUCIDAD',
        'descripcion': 'Merma por caducidad de producto',
        'requiere_autorizacion_gerente': True,
        'es_responsabilidad_empleado': False,
    },
    {
        'codigo': 'MERMA_ROTURA',
        'descripcion': 'Merma por rotura o daño físico',
        'requiere_autorizacion_gerente': False,
        'es_responsabilidad_empleado': True,
    },
    {
        'codigo': 'AJUSTE_INVENTARIO',
        'descripcion': 'Ajuste de inventario físico (recuento)',
        'requiere_autorizacion_gerente': False,
        'es_responsabilidad_empleado': False,
    },
    {
        'codigo': 'DONACION',
        'descripcion': 'Donación o uso interno',
        'requiere_autorizacion_gerente': False,
        'es_responsabilidad_empleado': False,
    },
    {
        'codigo': 'DEVOLUCION_PROVEEDOR',
        'descripcion': 'Devolución a proveedor',
        'requiere_autorizacion_gerente': False,
        'es_responsabilidad_empleado': False,
    },
    {
        'codigo': 'ROBO_FALTANTE',
        'descripcion': 'Robo o faltante no justificado',
        'requiere_autorizacion_gerente': True,
        'es_responsabilidad_empleado': True,
    },
    {
        'codigo': 'REINGRESO_DEVOLUCION',
        'descripcion': 'Reingreso por devolución de cliente',
        'requiere_autorizacion_gerente': False,
        'es_responsabilidad_empleado': False,
    },
    {
        'codigo': 'AJUSTE_GENERAL',
        'descripcion': 'Ajuste general de inventario',
        'requiere_autorizacion_gerente': False,
        'es_responsabilidad_empleado': False,
    },
]


class Command(BaseCommand):
    help = 'Siembra motivos de ajuste predeterminados para todas las empresas activas.'

    def handle(self, *args, **options):
        empresas = Empresa.objects.all()
        total_creados = 0
        for empresa in empresas:
            for motivo_data in MOTIVOS_DEFAULT:
                obj, created = MotivoAjuste.objects.get_or_create(
                    empresa=empresa,
                    codigo=motivo_data['codigo'],
                    defaults={
                        'descripcion': motivo_data['descripcion'],
                        'requiere_autorizacion_gerente': motivo_data['requiere_autorizacion_gerente'],
                        'es_responsabilidad_empleado': motivo_data['es_responsabilidad_empleado'],
                        'requiere_evidencia_fotografica': False,
                        'activo': True,
                    }
                )
                if created:
                    total_creados += 1
                    self.stdout.write(f'  [+] {empresa.nombre}: {obj.codigo}')
        self.stdout.write(
            self.style.SUCCESS(
                f'seed_motivos_ajuste: {total_creados} motivos creados '
                f'en {empresas.count()} empresa(s).'
            )
        )
