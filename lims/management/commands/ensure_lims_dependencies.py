"""Reconcile required calculated-result dependencies for one LIMS tenant.

This command is intentionally explicit: it never resets a catalog and requires
an empresa id. It restores only the authoritative BUN dependency used by UREA.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Empresa
from lims.models import Analito, PerfilAnalito, PerfilLims, ValorReferenciaAnalito


class Command(BaseCommand):
    help = 'Verifica y crea de forma idempotente la dependencia LIMS BUN de UREA.'

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, required=True)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--link-profiles',
            action='store_true',
            help='Agrega BUN a perfiles que ya contienen UREA, sin borrar ni reordenar analitos.',
        )

    def handle(self, *args, **options):
        empresa = Empresa.objects.filter(pk=options['empresa_id']).first()
        if not empresa:
            raise CommandError('La empresa indicada no existe.')

        existing = Analito.objects.filter(codigo='171').first()
        if existing and existing.empresa_id != empresa.id:
            raise CommandError('El codigo 171/BUN pertenece a otra empresa; no se modifica.')

        bun_defaults = {
            'empresa': empresa,
            'id_legacy': 2192,
            'codigo_rastreo_iso': f'BUN-171-{empresa.pk}',
            'abreviatura': 'BUN',
            'nombre': 'BUN',
            'departamento': 'BIOQUIMICA CLINICA',
            'tipo_muestra': 'SUERO',
            'metodologia': 'Enzimatico Automatizado',
            'tipo_resultado': 'NUMERICO',
            'unidades': 'mg/dL',
            'decimales': 2,
            'formula': '',
            'es_calculado': False,
            'es_vendible_individualmente': True,
            'costo_lista': Decimal('0.00'),
            'activo': True,
        }

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                f"BUN existente={bool(existing)}; empresa={empresa.pk}; "
                f"link_profiles={options['link_profiles']}"
            ))
            return

        with transaction.atomic():
            bun, created = Analito.objects.get_or_create(
                codigo='171',
                defaults=bun_defaults,
            )
            if bun.empresa_id != empresa.id:
                raise CommandError('El analito BUN existente no pertenece al tenant indicado.')

            ranges = 0
            for edad_min, edad_max in ((0, 365), (1, 120)):
                _, range_created = ValorReferenciaAnalito.objects.get_or_create(
                    analito=bun,
                    sexo='I',
                    unidad_edad='ANOS' if edad_min == 1 else 'DIAS',
                    edad_minima=edad_min,
                    edad_maxima=edad_max,
                    defaults={
                        'ref_minimo': Decimal('4.9'),
                        'ref_maximo': Decimal('22.6'),
                        'texto_referencia': '4.9 - 22.6 mg/dL',
                    },
                )
                ranges += int(range_created)

            links = 0
            if options['link_profiles']:
                for perfil in PerfilLims.objects.filter(
                    empresa=empresa,
                    activo=True,
                    analitos__codigo='URE',
                ).distinct():
                    if not PerfilAnalito.objects.filter(perfil=perfil, analito=bun).exists():
                        next_order = (PerfilAnalito.objects.filter(perfil=perfil).order_by('-orden').values_list('orden', flat=True).first() or 0) + 1
                        PerfilAnalito.objects.create(
                            empresa=empresa,
                            perfil=perfil,
                            analito=bun,
                            orden=next_order,
                        )
                        links += 1

        self.stdout.write(self.style.SUCCESS(
            f"BUN {'creado' if created else 'ya existente'}; rangos_nuevos={ranges}; perfiles_vinculados={links}."
        ))
