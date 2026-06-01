# -*- coding: utf-8 -*-
"""
Amnistía de datos LIMS — asignar empresa a filas huérfanas (empresa_id NULL).

Tablas afectadas (misma lógica que lims.0008):
  - lims_analito
  - lims_perfillims
  - lims_paquetelims
  - lims_precioitem

Orden operativo (multi-tenant, si partes la migración manualmente):
  Las columnas nullable se crean al inicio de lims 0008; 0007b es un shim vacío tras 0008.
  1) Tras existir columnas empresa NULL en LIMS (inicio de 0008, antes del NOT NULL)
  2) python manage.py lims_amnistia_empresa --dry-run
  3) python manage.py lims_amnistia_empresa --confirmar-multi-tenant  # si aplica
  En despliegue normal, migrate aplica 0008 completo (AddField + backfill + NOT NULL) solo.

Usa objects_all para ver todas las filas sin filtro de tenant en el request.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Empresa
from core.utils.default_empresa import resolve_default_empresa_sistema
from lims.models import Analito, PaqueteLims, PerfilLims, PrecioItem


class Command(BaseCommand):
    help = (
        'Asigna empresa principal (o --empresa-id) a registros LIMS con empresa_id NULL. '
        'Ejecutar con columnas empresa nullable en LIMS, antes del NOT NULL de 0008 (operación manual).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            default=None,
            help='PK de core.Empresa destino (recomendado si hay varias empresas activas).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar conteos; no escribir.',
        )
        parser.add_argument(
            '--confirmar-multi-tenant',
            action='store_true',
            help=(
                'Obligatorio si hay más de una empresa activa y no pasó --empresa-id. '
                'Confirma que desea usar resolve_default_empresa_sistema() (PRISLAB_DEFAULT_EMPRESA_ID / reglas canónicas).'
            ),
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        explicit_eid = options['empresa_id']
        confirm_multi = options['confirmar_multi_tenant']

        activas = Empresa.objects.filter(activa=True).order_by('id')
        n_activas = activas.count()
        if n_activas == 0:
            raise CommandError('No hay empresas activas en core.Empresa.')

        if explicit_eid is not None:
            empresa = Empresa.objects.filter(pk=explicit_eid, activa=True).first()
            if not empresa:
                raise CommandError(f'Empresa id={explicit_eid} no existe o no está activa.')
        else:
            if n_activas > 1 and not confirm_multi and not dry:
                raise CommandError(
                    'Hay varias empresas activas. Indique --empresa-id N '
                    'o repita con --confirmar-multi-tenant para usar la empresa por defecto del sistema '
                    '(ver core.utils.default_empresa.resolve_default_empresa_sistema). '
                    'Con --dry-run puede omitir --confirmar-multi-tenant para solo ver conteos.'
                )
            empresa = resolve_default_empresa_sistema()
            if not empresa:
                raise CommandError(
                    'No se pudo resolver empresa por defecto. Defina PRISLAB_DEFAULT_EMPRESA_ID '
                    'o use --empresa-id.'
                )

        eid = empresa.pk
        self.stdout.write(self.style.NOTICE(f'Empresa destino: id={eid} — {empresa.nombre}'))

        stats = self._counts()
        self.stdout.write('Huérfanos (empresa_id NULL):')
        for k, v in stats.items():
            self.stdout.write(f'  {k}: {v}')
        if sum(stats.values()) == 0:
            self.stdout.write(self.style.SUCCESS('Nada que corregir.'))
            return

        if dry:
            self.stdout.write(self.style.WARNING('Dry-run: no se aplicaron cambios.'))
            return

        with transaction.atomic():
            self._apply(eid)
            stats_after = self._counts()
        if sum(stats_after.values()) != 0:
            raise CommandError(f'Aún quedan huérfanos: {stats_after}')

        self.stdout.write(self.style.SUCCESS('Amnistía completada. Puede ejecutar: python manage.py migrate lims'))

    def _counts(self):
        return {
            'Analito': Analito.objects_all.filter(empresa_id__isnull=True).count(),
            'PerfilLims': PerfilLims.objects_all.filter(empresa_id__isnull=True).count(),
            'PaqueteLims': PaqueteLims.objects_all.filter(empresa_id__isnull=True).count(),
            'PrecioItem': PrecioItem.objects_all.filter(empresa_id__isnull=True).count(),
        }

    def _apply(self, eid: int):
        Analito.objects_all.filter(empresa_id__isnull=True).update(empresa_id=eid)
        PerfilLims.objects_all.filter(empresa_id__isnull=True).update(empresa_id=eid)
        PaqueteLims.objects_all.filter(empresa_id__isnull=True).update(empresa_id=eid)

        for precio in PrecioItem.objects_all.filter(empresa_id__isnull=True).iterator():
            new_eid = None
            if precio.analito_id:
                new_eid = (
                    Analito.objects_all.filter(pk=precio.analito_id)
                    .values_list('empresa_id', flat=True)
                    .first()
                )
            elif precio.perfil_id:
                new_eid = (
                    PerfilLims.objects_all.filter(pk=precio.perfil_id)
                    .values_list('empresa_id', flat=True)
                    .first()
                )
            elif precio.paquete_id:
                new_eid = (
                    PaqueteLims.objects_all.filter(pk=precio.paquete_id)
                    .values_list('empresa_id', flat=True)
                    .first()
                )
            if not new_eid:
                new_eid = eid
            PrecioItem.objects_all.filter(pk=precio.pk).update(empresa_id=new_eid)
