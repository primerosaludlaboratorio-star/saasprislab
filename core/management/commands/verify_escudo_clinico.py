"""
Verifica que PRISLAB_ESCUDO_USUARIO_ID apunte a un usuario activo (escudo LIMS / pánico).

Uso post-despliegue, CI o cron (vía core.views.cron_tasks.cron_verify_escudo_clinico).
Exit code 1 si la configuración es inválida en entornos que exigen escudo (nube).
"""
import os
import sys

from django.core.management.base import BaseCommand

from core.utils.escudo_clinico_check import verificar_escudo_clinico


class Command(BaseCommand):
    help = 'Comprueba que el usuario del Escudo Clínico LIMS exista y esté activo.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict-cloud',
            action='store_true',
            help='En nube (GOOGLE_CLOUD_PROJECT / GAE), fallar con exit 1 si el escudo no es válido.',
        )

    def handle(self, *args, **options):
        strict = options['strict_cloud']
        is_cloud = bool(os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GAE_ENV'))

        ok, msg = verificar_escudo_clinico()
        if ok:
            self.stdout.write(self.style.SUCCESS(msg))
            return

        self.stdout.write(self.style.ERROR(msg))
        if strict and is_cloud:
            sys.exit(1)
