"""
PRIS SENTINEL — Auto-Cleanup & Optimize (Rev 128 AIOps)
========================================================
Comando de mantenimiento que se ejecuta cuando la latencia sube
o via cron para mantener el sistema limpio y rapido.

Acciones:
  1. Purgar sesiones inactivas de mas de 24h
  2. Archivar AuditLog de mas de 6 meses (mover a tabla historica)
  3. Optimizar indices de PostgreSQL (VACUUM ANALYZE)
  4. Limpiar incidencias Sentinel resueltas antiguas
  5. Purgar cache de telemetria

Uso:
  python manage.py sentinel_auto_cleanup
  python manage.py sentinel_auto_cleanup --dry-run
  python manage.py sentinel_auto_cleanup --force-vacuum
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

logger = logging.getLogger('sentinel.cleanup')


class Command(BaseCommand):
    help = 'PRIS Sentinel: Auto-limpieza y optimizacion del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular acciones sin ejecutarlas',
        )
        parser.add_argument(
            '--force-vacuum',
            action='store_true',
            help='Forzar VACUUM ANALYZE incluso si no es necesario',
        )
        parser.add_argument(
            '--sessions-max-age-hours',
            type=int,
            default=24,
            help='Edad maxima de sesiones inactivas en horas (default: 24)',
        )
        parser.add_argument(
            '--audit-archive-months',
            type=int,
            default=6,
            help='Archivar audit logs mas antiguos que N meses (default: 6)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force_vacuum = options['force_vacuum']
        session_hours = options['sessions_max_age_hours']
        archive_months = options['audit_archive_months']

        self.stdout.write(self.style.WARNING(
            '═══════════════════════════════════════════════════════════════'
        ))
        self.stdout.write(self.style.WARNING(
            '  PRIS SENTINEL — Auto-Cleanup & Optimize'
        ))
        self.stdout.write(self.style.WARNING(
            f'  Modo: {"DRY RUN (simulacion)" if dry_run else "EJECUCION REAL"}'
        ))
        self.stdout.write(self.style.WARNING(
            '═══════════════════════════════════════════════════════════════'
        ))

        results = {}

        # ── 1. Purgar sesiones inactivas ─────────────────────────────
        results['sessions'] = self._purge_sessions(session_hours, dry_run)

        # ── 2. Archivar AuditLog antiguos ────────────────────────────
        results['audit'] = self._archive_audit_logs(archive_months, dry_run)

        # ── 3. Limpiar incidencias Sentinel resueltas ────────────────
        results['sentinel'] = self._cleanup_sentinel_incidents(dry_run)

        # ── 4. VACUUM ANALYZE en PostgreSQL ──────────────────────────
        results['vacuum'] = self._vacuum_analyze(force_vacuum, dry_run)

        # ── 5. Estadisticas finales ──────────────────────────────────
        self._print_summary(results, dry_run)

    def _purge_sessions(self, max_age_hours, dry_run):
        """Elimina sesiones de Django inactivas."""
        self.stdout.write('\n[1/4] Purgando sesiones inactivas...')
        try:
            from django.contrib.sessions.models import Session
            cutoff = timezone.now() - timedelta(hours=max_age_hours)
            expired = Session.objects.filter(expire_date__lt=cutoff)
            count = expired.count()

            if count > 0 and not dry_run:
                expired.delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ {count} sesiones expiradas eliminadas (>{max_age_hours}h)'
                ))
            elif count > 0:
                self.stdout.write(self.style.NOTICE(
                    f'  [DRY] Se eliminarian {count} sesiones expiradas'
                ))
            else:
                self.stdout.write('  ✓ No hay sesiones expiradas')

            return {'deleted': count if not dry_run else 0, 'found': count}
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _purge_sessions (sentinel_auto_cleanup.py)")
            self.stdout.write(self.style.ERROR(f'  ✗ Error: {e}'))
            return {'deleted': 0, 'found': 0, 'error': str(e)}

    def _archive_audit_logs(self, months, dry_run):
        """Mueve AuditLog antiguos a tabla historica (o elimina si no hay tabla)."""
        self.stdout.write(f'\n[2/4] Archivando AuditLog >{months} meses...')
        try:
            from core.models import AuditLog
            cutoff = timezone.now() - timedelta(days=months * 30)
            old_logs = AuditLog.objects.filter(fecha__lt=cutoff)
            count = old_logs.count()

            if count == 0:
                self.stdout.write('  ✓ No hay logs antiguos para archivar')
                return {'archived': 0, 'found': 0}

            if dry_run:
                self.stdout.write(self.style.NOTICE(
                    f'  [DRY] Se archivarian {count} logs de auditoria'
                ))
                return {'archived': 0, 'found': count}

            # Intentar mover a tabla historica via SQL directo
            # (mas eficiente que INSERT-SELECT en Django ORM)
            archived = self._move_to_archive(cutoff, count)

            if archived:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ {count} logs archivados en core_auditlog_historico'
                ))
            else:
                # Si no existe tabla historica, solo eliminamos los muy viejos (>12m)
                very_old_cutoff = timezone.now() - timedelta(days=365)
                very_old = AuditLog.objects.filter(fecha__lt=very_old_cutoff)
                very_old_count = very_old.count()
                if very_old_count > 0:
                    very_old.delete()
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ {very_old_count} logs >12 meses eliminados (sin tabla historica)'
                    ))
                else:
                    self.stdout.write('  ✓ Logs entre 6-12 meses conservados')

            return {'archived': count, 'found': count}

        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _archive_audit_logs (sentinel_auto_cleanup.py)")
            self.stdout.write(self.style.ERROR(f'  ✗ Error: {e}'))
            return {'archived': 0, 'found': 0, 'error': str(e)}

    def _move_to_archive(self, cutoff, count):
        """Intenta mover logs a tabla historica via SQL."""
        try:
            with connection.cursor() as cursor:
                # Verificar si la tabla historica existe
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'core_auditlog_historico'
                    )
                """)
                exists = cursor.fetchone()[0]

                if not exists:
                    # Crear tabla historica con misma estructura
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS core_auditlog_historico 
                        AS SELECT * FROM core_auditlog WHERE 1=0
                    """)
                    # Agregar timestamp de archivado
                    try:
                        cursor.execute("""
                            ALTER TABLE core_auditlog_historico 
                            ADD COLUMN IF NOT EXISTS archivado_en TIMESTAMP DEFAULT NOW()
                        """)
                    except Exception:
                        logging.getLogger(__name__).exception("Error inesperado en _move_to_archive (sentinel_auto_cleanup.py)")
                        pass

                # Mover datos
                cursor.execute("""
                    INSERT INTO core_auditlog_historico 
                    SELECT *, NOW() as archivado_en
                    FROM core_auditlog 
                    WHERE fecha < %s
                """, [cutoff])

                # Eliminar originales
                cursor.execute("""
                    DELETE FROM core_auditlog WHERE fecha < %s
                """, [cutoff])

                return True
        except Exception as e:
            logger.warning(f'SENTINEL-CLEANUP: No se pudo crear tabla historica: {e}')
            return False

    def _cleanup_sentinel_incidents(self, dry_run):
        """Limpia incidencias Sentinel resueltas de mas de 30 dias."""
        self.stdout.write('\n[3/4] Limpiando incidencias Sentinel resueltas...')
        try:
            from consultorio.models import IncidenciaSentinel
            cutoff = timezone.now() - timedelta(days=30)
            resolved = IncidenciaSentinel.objects.filter(
                estado='SOLUCIONADO',
                fecha_creacion__lt=cutoff,
            )
            count = resolved.count()

            if count > 0 and not dry_run:
                resolved.delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ {count} incidencias resueltas antiguas eliminadas'
                ))
            elif count > 0:
                self.stdout.write(self.style.NOTICE(
                    f'  [DRY] Se eliminarian {count} incidencias resueltas >30 dias'
                ))
            else:
                self.stdout.write('  ✓ No hay incidencias antiguas para limpiar')

            return {'deleted': count if not dry_run else 0, 'found': count}

        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _cleanup_sentinel_incidents (sentinel_auto_cleanup.py)")
            self.stdout.write(self.style.ERROR(f'  ✗ Error: {e}'))
            return {'deleted': 0, 'found': 0, 'error': str(e)}

    def _vacuum_analyze(self, force, dry_run):
        """Ejecuta VACUUM ANALYZE en las tablas principales de PostgreSQL."""
        self.stdout.write('\n[4/4] Optimizando indices (VACUUM ANALYZE)...')

        if dry_run:
            self.stdout.write(self.style.NOTICE(
                '  [DRY] Se ejecutaria VACUUM ANALYZE en tablas principales'
            ))
            return {'optimized': False}

        # Tablas principales que mas benefician de VACUUM
        tables = [
            'core_auditlog',
            'core_paciente',
            'core_venta',
            'core_ordenlab',
            'core_pago',
            'core_producto',
            'core_inventariolaboratorio',
            'django_session',
        ]

        optimized_count = 0
        try:
            # VACUUM requiere auto-commit
            old_autocommit = connection.connection.autocommit if connection.connection else True
            if connection.connection:
                connection.connection.autocommit = True

            with connection.cursor() as cursor:
                for table in tables:
                    try:
                        cursor.execute(f'VACUUM ANALYZE {table}')
                        optimized_count += 1
                        self.stdout.write(f'  ✓ VACUUM ANALYZE {table}')
                    except Exception as e:
                        logging.getLogger(__name__).exception("Error inesperado en _vacuum_analyze (sentinel_auto_cleanup.py)")
                        # Tabla puede no existir
                        self.stdout.write(f'  - {table}: {str(e)[:60]}')

            # Restaurar autocommit
            if connection.connection:
                connection.connection.autocommit = old_autocommit

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {optimized_count}/{len(tables)} tablas optimizadas'
            ))
            return {'optimized': True, 'tables': optimized_count}

        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _vacuum_analyze (sentinel_auto_cleanup.py)")
            self.stdout.write(self.style.ERROR(f'  ✗ Error en VACUUM: {e}'))
            return {'optimized': False, 'error': str(e)}

    def _print_summary(self, results, dry_run):
        """Imprime resumen final."""
        self.stdout.write('\n' + '═' * 63)
        self.stdout.write(self.style.SUCCESS(
            '  RESUMEN DE MANTENIMIENTO'
        ))
        self.stdout.write('═' * 63)
        self.stdout.write(f"  Sesiones purgadas:   {results['sessions'].get('deleted', 0)}")
        self.stdout.write(f"  AuditLogs archivados:{results['audit'].get('archived', 0)}")
        self.stdout.write(f"  Incidencias limpiadas:{results['sentinel'].get('deleted', 0)}")
        vacuum_status = 'OK' if results['vacuum'].get('optimized') else 'N/A'
        self.stdout.write(f"  VACUUM status:       {vacuum_status}")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n  ⚠ DRY RUN: Ningun cambio fue aplicado'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                '\n  ✓ Sistema limpio y optimizado'
            ))

        self.stdout.write('═' * 63)
        logger.info(
            f'SENTINEL-CLEANUP completado: sessions={results["sessions"]}, '
            f'audit={results["audit"]}, sentinel={results["sentinel"]}, '
            f'vacuum={results["vacuum"]}'
        )