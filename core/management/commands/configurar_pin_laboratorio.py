"""Configura o rota el PIN clínico de una empresa sin exponerlo en argumentos."""

import getpass
import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.models import ConfiguracionModulos, Empresa


class Command(BaseCommand):
    help = 'Configura o rota el PIN tenant-scoped para validar resultados de laboratorio'

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, required=True)
        parser.add_argument(
            '--pin-env',
            default='PRISLAB_LAB_VALIDATION_PIN',
            help='Variable de entorno que contiene el PIN; no se acepta --pin.',
        )

    def _get_pin(self, env_name):
        pin = os.environ.get(env_name, '').strip()
        if not pin:
            if getattr(settings, 'IS_PRODUCTION', False) or not sys.stdin.isatty():
                raise CommandError(f'Configura {env_name} en el entorno antes de ejecutar este comando.')
            pin = getpass.getpass('PIN clínico (mínimo 8 caracteres): ').strip()
        if len(pin) < 8:
            raise CommandError('El PIN clínico debe tener al menos 8 caracteres.')
        return pin

    def handle(self, *args, **options):
        try:
            empresa = Empresa.objects.get(pk=options['empresa_id'])
        except Empresa.DoesNotExist as exc:
            raise CommandError('La empresa indicada no existe.') from exc

        pin = self._get_pin(options['pin_env'])
        configuracion, _ = ConfiguracionModulos.objects.get_or_create(empresa=empresa)
        configuracion.pin_validacion_laboratorio = pin
        configuracion.save(update_fields=['pin_validacion_laboratorio', 'fecha_actualizacion'])
        self.stdout.write(self.style.SUCCESS(
            f'PIN clínico configurado para empresa {empresa.pk}. El valor nunca se muestra.'
        ))
