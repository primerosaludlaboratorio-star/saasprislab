"""
Fusiona todas las empresas de desarrollo en una sola (PRISLAB) y elimina las demás.

Uso (desarrollo / datos de prueba):
    python manage.py unificar_empresa_prislab
    python manage.py unificar_empresa_prislab --dry-run
"""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import ForeignKey, OneToOneField

from core.models import Empresa, Sucursal, ConfiguracionModulos
import logging


def _resolve_target_empresa():
    """Prioriza PRISLAB S.A. de C.V. o nombre que contenga PRISLAB."""
    for qs in (
        Empresa.objects.filter(nombre__icontains='PRISLAB S.A').order_by('id'),
        Empresa.objects.filter(nombre__iexact='PRISLAB').order_by('id'),
        Empresa.objects.filter(nombre__icontains='PRISLAB').order_by('id'),
    ):
        e = qs.first()
        if e:
            return e
    return Empresa.objects.order_by('id').first()


class Command(BaseCommand):
    help = 'Unifica todas las empresas en PRISLAB y elimina Laboratorio del Valle / duplicados de prueba.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué haría, sin escribir en la base de datos.',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        target = _resolve_target_empresa()
        if not target:
            self.stdout.write(self.style.ERROR('No hay ninguna empresa en la base de datos.'))
            return

        sources = list(Empresa.objects.exclude(pk=target.pk).order_by('id'))
        if not sources:
            self.stdout.write(self.style.SUCCESS(f'Solo existe una empresa: {target.nombre} (id={target.pk}). Nada que hacer.'))
            return

        self.stdout.write(f'Empresa destino: [{target.pk}] {target.nombre}')
        self.stdout.write('Orígenes a fusionar: ' + ', '.join(f'[{e.pk}] {e.nombre}' for e in sources))

        matriz = (
            Sucursal.objects.filter(empresa=target)
            .order_by('id')
            .first()
        )
        if not matriz:
            self.stdout.write(self.style.ERROR('La empresa destino no tiene sucursal. Ejecuta: python manage.py inicializar_pris_valle'))
            return

        source_ids = [e.pk for e in sources]
        source_suc_ids = list(
            Sucursal.objects.filter(empresa_id__in=source_ids).values_list('pk', flat=True)
        )

        def do_merge():
            # 1) MotivoAjuste: unique (empresa, codigo)
            try:
                from farmacia.models import MotivoAjuste
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en do_merge (unificar_empresa_prislab.py)")
                MotivoAjuste = None
            if MotivoAjuste:
                for src in sources:
                    for ma in MotivoAjuste.objects.filter(empresa=src):
                        if MotivoAjuste.objects.filter(empresa=target, codigo=ma.codigo).exists():
                            ma.delete()
                        else:
                            ma.empresa = target
                            ma.save()

            # 2) ConfiguracionModulos: OneToOne por empresa
            for src in sources:
                cfg = ConfiguracionModulos.objects.filter(empresa=src).first()
                if not cfg:
                    continue
                if ConfiguracionModulos.objects.filter(empresa=target).exists():
                    cfg.delete()
                else:
                    cfg.empresa = target
                    cfg.save()

            # 3) Reasignar todas las FK a Sucursal de empresas fuente → Matriz
            for model in apps.get_models():
                for field in model._meta.fields:
                    if not isinstance(field, (ForeignKey, OneToOneField)):
                        continue
                    if field.remote_field.model is not Sucursal:
                        continue
                    if model is Sucursal:
                        continue
                    if not source_suc_ids:
                        break
                    fname = field.name
                    updated = model.objects.filter(**{f'{fname}_id__in': source_suc_ids}).update(
                        **{f'{fname}_id': matriz.pk}
                    )
                    if updated:
                        self.stdout.write(f'  {model._meta.label}.{fname}: {updated} filas → sucursal Matriz')

            # 4) Borrar sucursales de empresas fuente (FKs ya apuntan a Matriz; no reasignar Sucursal.empresa)
            deleted_s, _ = Sucursal.objects.filter(empresa_id__in=source_ids).delete()
            self.stdout.write(f'  Sucursales eliminadas: {deleted_s}')

            # 5) Reasignar todas las FK a Empresa (excepto Empresa y Sucursal)
            for model in apps.get_models():
                if model in (Empresa, Sucursal):
                    continue
                for field in model._meta.fields:
                    if not isinstance(field, (ForeignKey, OneToOneField)):
                        continue
                    if field.remote_field.model is not Empresa:
                        continue
                    fname = field.name
                    updated = model.objects.filter(**{f'{fname}_id__in': source_ids}).update(
                        **{f'{fname}_id': target.pk}
                    )
                    if updated:
                        self.stdout.write(f'  {model._meta.label}.{fname}: {updated} filas → empresa destino')

            # 6) Borrar empresas fuente
            deleted_e, _ = Empresa.objects.filter(pk__in=source_ids).delete()
            self.stdout.write(f'  Empresas eliminadas: {deleted_e}')

        if dry:
            self.stdout.write(self.style.WARNING('[DRY-RUN] No se aplicaron cambios.'))
            self.stdout.write(f'Se reasignarían sucursales {source_suc_ids} → Matriz id={matriz.pk}')
            self.stdout.write(f'Se fusionarían empresas {source_ids} → {target.pk}')
            return

        with transaction.atomic():
            do_merge()

        self.stdout.write(self.style.SUCCESS('Listo: una sola empresa (PRISLAB) y sucursales unificadas en Matriz.'))