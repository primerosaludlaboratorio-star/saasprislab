"""
CICLO 10: Limpieza de archivos temporales y huérfanos en MEDIA_ROOT.

Elimina:
  1. Archivos en subdirectorios tmp/, cache/, temp/, caché/ bajo MEDIA_ROOT con más de 7 días.
  2. Opcionalmente, archivos en MEDIA_ROOT no referenciados por ningún modelo (huérfanos).

Nota: Los archivos temporales creados en el directorio del sistema (tempfile.gettempdir()),
por ejemplo en core/services/ai_medico.py o restaurar_backup, se eliminan en bloque finally
por el código que los crea; este comando no los procesa.

Ejecución periódica recomendada: cron o Cloud Scheduler (ej. diario a las 4:00).

Uso:
  python manage.py limpiar_temporales
  python manage.py limpiar_temporales --dry-run
  python manage.py limpiar_temporales --days 14
  python manage.py limpiar_temporales --orphans  (eliminar huérfanos > 7 días)
"""
import os
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db.models import FileField, ImageField
from django.apps import apps


class Command(BaseCommand):
    help = 'Limpia archivos temporales y opcionalmente huérfanos en MEDIA_ROOT (tmp/cache > N días).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo reportar qué se eliminaría, sin borrar.',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Eliminar archivos más antiguos que N días (default: 7).',
        )
        parser.add_argument(
            '--orphans',
            action='store_true',
            help='Además, eliminar archivos huérfanos (no referenciados por ningún modelo) mayores a --days.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days = options['days']
        do_orphans = options['orphans']
        cutoff = timezone.now() - timedelta(days=days)

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root or not os.path.isdir(media_root):
            self.stdout.write(self.style.WARNING(
                f'MEDIA_ROOT no existe o no es directorio: {media_root}. Nada que limpiar.'
            ))
            return

        self.stdout.write(self.style.WARNING(
            '═══════════════════════════════════════════════════════════════'
        ))
        self.stdout.write(self.style.WARNING(
            '  CICLO 10 — Limpieza de temporales'
        ))
        self.stdout.write(self.style.WARNING(
            f'  Modo: {"DRY RUN (solo reportar)" if dry_run else "EJECUCIÓN REAL"}'
        ))
        self.stdout.write(self.style.WARNING(
            f'  MEDIA_ROOT: {media_root}'
        ))
        self.stdout.write(self.style.WARNING(
            f'  Edad mínima para eliminar: {days} días (antes de {cutoff.date()})'
        ))
        self.stdout.write(self.style.WARNING(
            '═══════════════════════════════════════════════════════════════'
        ))

        total_deleted = 0
        total_bytes = 0

        # ── 1. Limpiar tmp/ y cache/ bajo MEDIA_ROOT ─────────────────
        for subdir in ('tmp', 'cache', 'temp', 'caché'):
            dir_path = os.path.join(media_root, subdir)
            if not os.path.isdir(dir_path):
                continue
            deleted, bytes_freed = self._clean_directory(dir_path, cutoff, dry_run)
            total_deleted += deleted
            total_bytes += bytes_freed
            if deleted:
                self.stdout.write(
                    self.style.SUCCESS(f'  {subdir}/: {deleted} archivo(s), {self._fmt_size(bytes_freed)} liberados')
                )

        # ── 2. Opcional: huérfanos en todo MEDIA_ROOT ─────────────────
        if do_orphans:
            referenced = self._get_referenced_media_paths()
            deleted_orph, bytes_orph = self._clean_orphans(media_root, media_root, referenced, cutoff, dry_run)
            total_deleted += deleted_orph
            total_bytes += bytes_orph
            if deleted_orph:
                self.stdout.write(
                    self.style.SUCCESS(f'  Huérfanos: {deleted_orph} archivo(s), {self._fmt_size(bytes_orph)} liberados')
                )
            elif do_orphans and not dry_run:
                self.stdout.write('  Huérfanos: 0 archivos eliminados.')

        # ── Resumen ───────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Total: {total_deleted} archivo(s) {"a eliminar" if dry_run else "eliminados"}, '
            f'{self._fmt_size(total_bytes)} {"a liberar" if dry_run else "liberados"}.'
        ))
        if dry_run and (total_deleted or total_bytes):
            self.stdout.write(self.style.NOTICE('Ejecuta sin --dry-run para aplicar los cambios.'))

    def _fmt_size(self, size_bytes):
        if size_bytes >= 1024 * 1024:
            return f'{size_bytes / (1024 * 1024):.2f} MB'
        if size_bytes >= 1024:
            return f'{size_bytes / 1024:.2f} KB'
        return f'{size_bytes} B'

    def _clean_directory(self, dir_path, cutoff, dry_run):
        """Elimina archivos bajo dir_path con mtime < cutoff. No borra subdirs recursivamente por defecto."""
        deleted = 0
        bytes_freed = 0
        try:
            for entry in os.scandir(dir_path):
                if entry.is_file():
                    try:
                        mtime = entry.stat().st_mtime
                        from datetime import datetime
                        if datetime.fromtimestamp(mtime).date() < cutoff.date():
                            size = entry.stat().st_size
                            if not dry_run:
                                try:
                                    os.remove(entry.path)
                                except OSError:
                                    pass
                            deleted += 1
                            bytes_freed += size
                    except OSError:
                        pass
                elif entry.is_dir():
                    d_deleted, d_bytes = self._clean_directory(entry.path, cutoff, dry_run)
                    deleted += d_deleted
                    bytes_freed += d_bytes
        except OSError:
            pass
        return deleted, bytes_freed

    def _get_referenced_media_paths(self):
        """Devuelve un set de rutas relativas a MEDIA_ROOT que están en uso en modelos."""
        referenced = set()
        media_root = os.path.normpath(settings.MEDIA_ROOT)
        for model in apps.get_models():
            for field in model._meta.get_fields():
                if not isinstance(field, (FileField, ImageField)):
                    continue
                attr = field.name
                try:
                    for obj in model.objects.iterator():
                        f = getattr(obj, attr)
                        if f:
                            name = getattr(f, 'name', None)
                            if name:
                                referenced.add(os.path.normpath(name).replace('\\', '/'))
                except Exception:
                    continue
        return referenced

    def _clean_orphans(self, media_root, current_path, referenced, cutoff, dry_run):
        """Elimina archivos bajo current_path que no están en referenced y son más viejos que cutoff."""
        deleted = 0
        bytes_freed = 0
        try:
            for entry in os.scandir(current_path):
                if entry.is_file():
                    rel = os.path.normpath(os.path.relpath(entry.path, media_root)).replace('\\', '/')
                    if rel in referenced:
                        continue
                    try:
                        mtime = entry.stat().st_mtime
                        if datetime.fromtimestamp(mtime).date() < cutoff.date():
                            size = entry.stat().st_size
                            if not dry_run:
                                try:
                                    os.remove(entry.path)
                                except OSError:
                                    pass
                            deleted += 1
                            bytes_freed += size
                    except OSError:
                        pass
                elif entry.is_dir():
                    # Evitar recursión infinita en tmp/cache ya limpiados
                    d_deleted, d_bytes = self._clean_orphans(media_root, entry.path, referenced, cutoff, dry_run)
                    deleted += d_deleted
                    bytes_freed += d_bytes
        except OSError:
            pass
        return deleted, bytes_freed
