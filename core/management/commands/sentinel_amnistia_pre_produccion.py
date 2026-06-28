"""
PRIS Sentinel — Pizarra limpia pre go-live (Hito v1.55)
=======================================================
Marca como cerradas las incidencias técnicas y bandejas relacionadas
para que operación arranque con conteo en cero (sin borrar histórico).

Cubre:
  - consultorio.IncidenciaSentinel (estado → SOLUCIONADO; el modelo no usa boolean `resuelta`)
  - core.BuzonQuejas (estado → RESUELTO)
  - inventario.NotificacionDiscrepancia (resuelta=True; aquí sí aplica el flag)
  - core.NotificacionSistema (leida=True para bandeja interna)

Uso:
  python manage.py sentinel_amnistia_pre_produccion
  python manage.py sentinel_amnistia_pre_produccion --dry-run
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

NOTA = 'Cierre masivo automático pre-producción (Hito v1.55)'


class Command(BaseCommand):
    help = 'Amnistía Sentinel / buzón / discrepancias / notificaciones internas antes de go-live (v1.55)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar conteos; no escribe en base de datos',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        now = timezone.now()
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('  SENTINEL AMNISTÍA PRE-PRODUCCIÓN (v1.55)'))
        self.stdout.write(self.style.WARNING(f'  Modo: {"DRY-RUN" if dry else "EJECUCIÓN REAL"}'))
        self.stdout.write(self.style.WARNING('=' * 60))

        total_ops = 0

        # 1) IncidenciaSentinel
        try:
            from consultorio.models import IncidenciaSentinel

            qs = IncidenciaSentinel.objects.exclude(estado='SOLUCIONADO')
            n = qs.count()
            self.stdout.write(f'\n[IncidenciaSentinel] pendientes: {n}')
            if n and not dry:
                qs.update(
                    estado='SOLUCIONADO',
                    notas_resolucion=NOTA,
                    fecha_resolucion=now,
                )
            total_ops += n
            if n and dry:
                self.stdout.write('  (dry-run: no actualizado)')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (sentinel_amnistia_pre_produccion.py)")
            self.stdout.write(self.style.ERROR(f'  [skip] IncidenciaSentinel: {e}'))

        # 2) BuzonQuejas
        try:
            from core.models import BuzonQuejas

            qs = BuzonQuejas.objects.exclude(estado__in=['RESUELTO', 'DESCARTADO'])
            n = qs.count()
            self.stdout.write(f'\n[BuzonQuejas] pendientes: {n}')
            if n and not dry:
                qs.update(
                    estado='RESUELTO',
                    notas_resolucion=NOTA,
                    fecha_resolucion=now,
                    fecha_cierre=now,
                )
            total_ops += n
            if n and dry:
                self.stdout.write('  (dry-run: no actualizado)')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (sentinel_amnistia_pre_produccion.py)")
            self.stdout.write(self.style.ERROR(f'  [skip] BuzonQuejas: {e}'))

        # 3) NotificacionDiscrepancia (inventario)
        try:
            from inventario.models import NotificacionDiscrepancia

            qs = NotificacionDiscrepancia.objects.filter(resuelta=False)
            n = qs.count()
            self.stdout.write(f'\n[NotificacionDiscrepancia] sin resolver: {n}')
            if n and not dry:
                qs.update(
                    resuelta=True,
                    notas_resolucion=NOTA,
                    resuelta_en=now,
                )
            total_ops += n
            if n and dry:
                self.stdout.write('  (dry-run: no actualizado)')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (sentinel_amnistia_pre_produccion.py)")
            self.stdout.write(self.style.ERROR(f'  [skip] NotificacionDiscrepancia: {e}'))

        # 4) NotificacionSistema (centro de alertas internas)
        try:
            from core.models import NotificacionSistema

            qs = NotificacionSistema.objects.filter(leida=False)
            n = qs.count()
            self.stdout.write(f'\n[NotificacionSistema] no leídas: {n}')
            if n and not dry:
                qs.update(leida=True, fecha_lectura=now)
            total_ops += n
            if n and dry:
                self.stdout.write('  (dry-run: no actualizado)')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (sentinel_amnistia_pre_produccion.py)")
            self.stdout.write(self.style.ERROR(f'  [skip] NotificacionSistema: {e}'))

        self.stdout.write('\n' + '=' * 60)
        if dry:
            self.stdout.write(self.style.SUCCESS(f'  DRY-RUN: {total_ops} filas habrían sido actualizadas'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  Listo: {total_ops} filas actualizadas (acumulado por modelo)'))
        self.stdout.write(self.style.WARNING('  IncidenciaOperativa (auditoría de negocio) NO se modifica.'))
        self.stdout.write('=' * 60)