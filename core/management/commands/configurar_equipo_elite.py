"""
Script de Configuración del Equipo de Élite - PRISLAB v5
Configura títulos profesionales y enfoques para que los saludos funcionen desde el lunes.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import logging

Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Configura títulos profesionales y enfoques del Equipo de Élite'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Configurando Equipo de Elite...\n'))
        
        # Configuración del Equipo de Élite
        equipo_elite = [
            {
                'username': 'gabriela',
                'titulo': 'Q.C.',
                'enfoque': 'Integridad y Calidad en cada análisis'
            },
            {
                'username': 'nancy',
                'titulo': 'IQFB',
                'enfoque': 'Operación Científica de Excelencia'
            },
            {
                'username': 'janet',
                'titulo': 'TLQ',
                'enfoque': 'Precisión Analítica y Rigor Técnico'
            },
            {
                'username': 'tania',
                'titulo': 'TLQ',
                'enfoque': 'Fiabilidad en Procesos y Resultados'
            },
            {
                'username': 'brizia',
                'titulo': 'Dra.',
                'enfoque': 'Liderazgo Clínico y Visión Integral'
            },
            {
                'username': 'deya',
                'titulo': '',
                'enfoque': 'Soporte y Evolución Profesional Continua'
            },
        ]
        
        actualizados = 0
        no_encontrados = []
        
        for miembro in equipo_elite:
            try:
                # Buscar por username (case insensitive)
                usuario = Usuario.objects.filter(username__iexact=miembro['username']).first()
                
                if not usuario:
                    # Intentar buscar por first_name
                    usuario = Usuario.objects.filter(first_name__iexact=miembro['username']).first()
                
                if usuario:
                    usuario.titulo_profesional = miembro['titulo']
                    usuario.enfoque_profesional = miembro['enfoque']
                    usuario.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[OK] {usuario.username}: {miembro['titulo']} - {miembro['enfoque']}"
                        )
                    )
                    actualizados += 1
                else:
                    no_encontrados.append(miembro['username'])
                    self.stdout.write(
                        self.style.WARNING(
                            f"[WARN] Usuario '{miembro['username']}' no encontrado"
                        )
                    )
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en handle (configurar_equipo_elite.py)")
                self.stdout.write(
                    self.style.ERROR(
                        f"[ERROR] Error al actualizar '{miembro['username']}': {str(e)}"
                    )
                )
        
        self.stdout.write(self.style.SUCCESS(f'\nProceso completado: {actualizados} usuarios actualizados'))
        
        if no_encontrados:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[WARN] Usuarios no encontrados: {", ".join(no_encontrados)}'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    '   Verifica que los usernames coincidan con la base de datos.'
                )
            )