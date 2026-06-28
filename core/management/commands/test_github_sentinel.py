"""
PRIS Sentinel: Test de conexion con GitHub para auto-reporte de errores.
Uso: python manage.py test_github_sentinel
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Prueba la conexion de PRIS Sentinel con GitHub Issues'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('\n' + '=' * 60))
        self.stdout.write(self.style.NOTICE('  PRIS SENTINEL - Test de Conexion GitHub'))
        self.stdout.write(self.style.NOTICE('=' * 60 + '\n'))

        from core.services.github_reporter import (
            test_github_connection, GITHUB_TOKEN, GITHUB_REPO
        )

        # Mostrar config
        token_display = f'{GITHUB_TOKEN[:8]}...' if GITHUB_TOKEN else '(no configurado)'
        self.stdout.write(f'  GITHUB_TOKEN: {token_display}')
        self.stdout.write(f'  GITHUB_REPO:  {GITHUB_REPO or "(no configurado)"}')
        self.stdout.write('')

        if not GITHUB_TOKEN or not GITHUB_REPO:
            self.stdout.write(self.style.WARNING(
                '  ATENCION: Configura las variables de entorno:\n'
                '    GITHUB_TOKEN = tu Personal Access Token (con permiso "repo")\n'
                '    GITHUB_REPO  = owner/repo (ej: jonilsam/PRISLAB_SaaS)\n\n'
                '  En producción:\n'
                '    reinicia el servicio web si es necesario\n'
                '      --region us-central1 \\\n'
                '      --set-env-vars GITHUB_TOKEN=ghp_xxx,GITHUB_REPO=owner/repo\n'
            ))
            return

        # Test conexion
        self.stdout.write('  Probando conexion...')
        ok, msg = test_github_connection()

        if ok:
            self.stdout.write(self.style.SUCCESS(f'  CONECTADO: {msg}'))
            self.stdout.write(self.style.SUCCESS(
                '\n  Sentinel creara Issues automaticamente cuando detecte errores 500.'
                '\n  Las notificaciones llegaran a la App movil de GitHub.\n'
            ))
        else:
            self.stdout.write(self.style.ERROR(f'  ERROR: {msg}'))

        self.stdout.write('=' * 60 + '\n')
