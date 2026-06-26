"""
Management Command: activar_war_room
════════════════════════════════════
Activa el flag WAR_ROOM_ACTIVO para TODAS las empresas activas.
Se ejecuta en cada deploy para garantizar que ninguna empresa quede sin el War Room.
Idempotente: se puede correr N veces sin efectos secundarios.
"""
from django.core.management.base import BaseCommand
import logging


class Command(BaseCommand):
    help = 'Activa el War Room del Director para todas las empresas activas.'

    def handle(self, *args, **options):
        from core.models import Empresa
        from core.services.feature_flags import activar

        empresas = Empresa.objects.filter(activa=True)
        activadas = 0
        for empresa in empresas:
            try:
                activar('WAR_ROOM_ACTIVO', empresa)
                activadas += 1
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en handle (activar_war_room.py)")
                self.stderr.write(f'[WARN] Empresa {empresa.id}: {e}')

        self.stdout.write(
            self.style.SUCCESS(
                f'[OK] WAR_ROOM_ACTIVO activado en {activadas}/{empresas.count()} empresas.'
            )
        )