# -*- coding: utf-8 -*-
"""
Prueba local del Shadow Mode (Fase 1 v8.5).

Ejecutar con:
  set PRISLAB_TENANT_SHADOW_LOG_CLI=1
  python manage.py tenant_shadow_smoke

Debe emitir al menos un log TENANT_SHADOW_UNSCOPED_QUERY_CLI con stack trace.
"""
from django.core.management.base import BaseCommand

from core.models import Paciente


class Command(BaseCommand):
    help = 'Dispara una consulta TenantModel sin contexto de empresa (ver logs core.tenant).'

    def handle(self, *args, **options):
        n = Paciente.objects.count()
        self.stdout.write(self.style.NOTICE(f'Conteo Paciente.objects (sin tenant en CLI): {n}'))
        self.stdout.write(
            self.style.WARNING(
                'Revise consola o logs: debe aparecer TENANT_SHADOW_UNSCOPED_QUERY_CLI si '
                'PRISLAB_TENANT_SHADOW_LOG_CLI=1 y PRISLAB_TENANT_SHADOW_MODE=1.'
            )
        )
