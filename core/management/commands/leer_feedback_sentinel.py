"""
PRIS SENTINEL — Leer Feedback del Personal
============================================
Imprime en consola todas las quejas/reportes enviados por el personal
a traves del boton de feedback de Sentinel.

Uso:
  python manage.py leer_feedback_sentinel
"""
import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger('sentinel')


class Command(BaseCommand):
    help = 'Muestra las quejas y reportes del personal via Sentinel Feedback'

    def handle(self, *args, **options):
        try:
            from consultorio.models import IncidenciaSentinel
        except ImportError:
            self.stderr.write('No se pudo importar IncidenciaSentinel')
            return

        # Obtener TODOS los feedback (origen=FEEDBACK)
        feedbacks = IncidenciaSentinel.objects.filter(
            origen='FEEDBACK',
        ).order_by('-fecha_creacion').values(
            'id', 'descripcion_usuario', 'url_afectada', 'estado',
            'severidad', 'fecha_creacion',
            'usuario_reporta__username', 'usuario_reporta__first_name',
        )[:50]

        self.stdout.write('=' * 70)
        self.stdout.write('  REPORTES DEL PERSONAL (SENTINEL FEEDBACK)')
        self.stdout.write('=' * 70)

        if not feedbacks:
            self.stdout.write('  No hay reportes de feedback.')
            return

        for fb in feedbacks:
            usuario = fb['usuario_reporta__first_name'] or fb['usuario_reporta__username'] or 'Anonimo'
            fecha = fb['fecha_creacion'].strftime('%Y-%m-%d %H:%M') if fb['fecha_creacion'] else 'N/A'
            desc = fb['descripcion_usuario'] or '(sin descripcion)'
            estado = fb['estado']
            sev = fb['severidad']

            self.stdout.write(f'\n  --- Incidencia #{fb["id"]} [{estado}] [{sev}] ---')
            self.stdout.write(f'  Usuario: {usuario} | Fecha: {fecha}')
            self.stdout.write(f'  URL: {fb["url_afectada"]}')
            self.stdout.write(f'  QUEJA: {desc}')

            # Log para que aparezca en Cloud Logging
            logger.info(
                f'FEEDBACK #{fb["id"]} [{estado}] by {usuario} at {fecha}: {desc}'
            )

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(f'  Total reportes: {len(feedbacks)}')
        self.stdout.write('=' * 70)
