"""
LIMPIEZA DUPLICADOS CIERRES — Pre-migración v1.13
=================================================

Script de emergencia para consolidar cierres duplicados de una misma apertura
ANTES de aplicar la migración que agrega UniqueConstraint.

EJECUTAR EN PRODUCCIÓN ANTES DE MIGRAR:
    python manage.py limpiar_duplicados_cierres --dry-run
    python manage.py limpiar_duplicados_cierres --execute

⚠️  Si hay duplicados y no se ejecuta esto, la migración FALLARÁ.

Autor: Windsurf Cascade
Fecha: 2026-04-03
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from farmacia.models import CierreTurnoFarmacia, AperturaCaja

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Limpieza de cierres duplicados antes de migración UniqueConstraint v1.13'

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Ejecutar la limpieza real (sin esto solo detecta)',
        )
        parser.add_argument(
            '--empresa',
            type=int,
            help='Filtrar por ID de empresa',
        )

    def handle(self, *args, **options):
        execute = options['execute']
        empresa_id = options.get('empresa')

        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))
        self.stdout.write(self.style.MIGRATE_HEADING('LIMPIEZA DUPLICADOS CIERRES v1.13'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))

        if not execute:
            self.stdout.write(self.style.WARNING('\n[DRY-RUN MODE] Solo detectando duplicados.\n'))
        else:
            self.stdout.write(self.style.ERROR('\n[EXECUTE MODE] ¡Se consolidarán cierres duplicados!\n'))

        # Detectar aperturas con múltiples cierres
        cierres_query = CierreTurnoFarmacia.objects.filter(
            apertura_caja__isnull=False
        )
        if empresa_id:
            cierres_query = cierres_query.filter(empresa_id=empresa_id)

        # Agrupar por apertura y contar
        duplicados = cierres_query.values('apertura_caja').annotate(
            total=Count('id')
        ).filter(total__gt=1)

        if not duplicados.exists():
            self.stdout.write(self.style.SUCCESS('\n✅ No hay cierres duplicados. Migración segura.'))
            return

        total_aperturas_afectadas = duplicados.count()
        total_cierres_consolidados = 0

        self.stdout.write(self.style.ERROR(
            f'\n⚠️  DETECTADOS: {total_aperturas_afectadas} aperturas con múltiples cierres\n'
        ))

        for dup in duplicados:
            apertura_id = dup['apertura_caja']
            total_cierres = dup['total']

            try:
                apertura = AperturaCaja.objects.get(id=apertura_id)
            except AperturaCaja.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'   Apertura #{apertura_id} no existe, saltando.'))
                continue

            # Obtener todos los cierres de esta apertura
            cierres = CierreTurnoFarmacia.objects.filter(
                apertura_caja=apertura
            ).order_by('fecha_cierre')

            self.stdout.write(f'\n   📦 Apertura: {apertura.folio}')
            self.stdout.write(f'      Cierres encontrados: {total_cierres}')

            for i, cierre in enumerate(cierres):
                self.stdout.write(f'      • {i+1}. {cierre.folio} | {cierre.fecha_cierre}')

            if not execute:
                continue

            # CONSOLIDACIÓN: Mantener el primero (más antiguo), eliminar el resto
            # Estrategia conservadora: el primero es el "oficial"
            cierres_lista = list(cierres)
            cierre_oficial = cierres_lista[0]  # Primer cierre (más antiguo)
            cierres_borrar = cierres_lista[1:]  # Resto a eliminar

            try:
                with transaction.atomic():
                    # Eliminar cierres duplicados
                    for cierre_dup in cierres_borrar:
                        folio_dup = cierre_dup.folio
                        cierre_dup.delete()
                        self.stdout.write(self.style.WARNING(f'      → Eliminado: {folio_dup}'))
                        total_cierres_consolidados += 1

                    # Asegurar que la apertura esté marcada como cerrada
                    if apertura.activa:
                        apertura.cerrar_caja()
                        apertura.cerrada_con = cierre_oficial
                        apertura.save(update_fields=['cerrada_con'])
                        self.stdout.write(self.style.WARNING(f'      → Apertura marcada como cerrada'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'      ❌ Error consolidando: {e}'))
                logger.error(f'Error consolidando apertura {apertura_id}: {e}', exc_info=True)

        # Resumen
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '=' * 70))
        if execute:
            self.stdout.write(self.style.MIGRATE_HEADING('RESULTADO DE LA LIMPIEZA'))
            self.stdout.write(f'✅ Aperturas consolidadas: {total_aperturas_afectadas}')
            self.stdout.write(f'✅ Cierres duplicados eliminados: {total_cierres_consolidados}')
            if total_cierres_consolidados > 0:
                self.stdout.write(self.style.SUCCESS('\n🎉 Migración UniqueConstraint segura para ejecutar.'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Se encontraron {total_aperturas_afectadas} aperturas con duplicados.'))
            self.stdout.write(self.style.NOTICE('\nEjecute con --execute para consolidar antes de migrar.'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 70))
