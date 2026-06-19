"""
FASE 0 - Limpieza de Entorno para Stress Test
==============================================
Sanea el estado temporal del servidor/BD antes de la carga masiva.
NO borra datos reales de usuarios.

Ejecutar: python manage.py limpieza_entorno_prod
"""
import os
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.core.management import call_command


class Command(BaseCommand):
    help = "Limpieza pre-stress: sesiones expiradas, caché, PDFs temp. NO borra datos de usuarios."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se haría, sin ejecutar',
        )

    def handle(self, *args, **options):
        dry = options.get('dry_run', False)
        if dry:
            self.stdout.write(self.style.WARNING("Modo dry-run: no se modificará nada\n"))

        # 1. Sesiones expiradas
        try:
            qs = Session.objects.filter(expire_date__lt=timezone.now())
            count = qs.count()
            if not dry and count > 0:
                qs.delete()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Sesiones expiradas: {count} eliminadas"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [X] Sesiones: {e}"))

        # 2. clearsessions (redundante pero seguro)
        if not dry:
            try:
                call_command('clearsessions', verbosity=0)
                self.stdout.write(self.style.SUCCESS("  [OK] clearsessions ejecutado"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  [i] clearsessions: {e}"))

        # 3. Caché
        try:
            from django.core.cache import cache
            if not dry:
                cache.clear()
            self.stdout.write(self.style.SUCCESS("  [OK] Caché Django: limpiado"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  [i] Caché: {e}"))

        # 4. PDFs temporales huérfanos
        try:
            from django.conf import settings
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            eliminados = 0
            if media_root and os.path.isdir(media_root):
                for subdir in ('temp', 'tmp', 'pdf_temp'):
                    d = os.path.join(media_root, subdir)
                    if os.path.isdir(d):
                        for f in os.listdir(d):
                            path = os.path.join(d, f)
                            try:
                                mtime = os.path.getmtime(path)
                                age = timezone.now() - timezone.make_aware(datetime.fromtimestamp(mtime))
                                if age > timedelta(hours=24):
                                    if not dry:
                                        os.remove(path)
                                    eliminados += 1
                            except Exception:
                                pass
            self.stdout.write(self.style.SUCCESS(f"  [OK] PDFs temp: {eliminados} huérfanos"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [X] PDFs temp: {e}"))

        self.stdout.write(self.style.SUCCESS("\nLimpieza completada. Entorno listo para stress test."))
