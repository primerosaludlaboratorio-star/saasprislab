"""
Management command para poblar recursos de bienestar.
Ejecutar: python manage.py poblar_recursos
"""
from django.core.management.base import BaseCommand
from bienestar.models import RecursoCrecimiento


class Command(BaseCommand):
    help = 'Pobla la base de datos con recursos de bienestar de ejemplo'

    def handle(self, *args, **options):
        self.stdout.write('Limpiando recursos existentes...')
        RecursoCrecimiento.objects.all().delete()

        recursos_data = [
            # FINANZAS
            {
                'titulo': 'Presupuesto Personal Saludable',
                'categoria': 'FINANZAS',
                'url_contenido': 'https://www.youtube.com/watch?v=HQzoZfc3GwQ',
                'descripcion': 'Aprende a crear y mantener un presupuesto que te ayude a alcanzar tus metas financieras sin estres.',
                'activo': True
            },
            {
                'titulo': 'Ahorro Inteligente: Pequenos Pasos, Grandes Resultados',
                'categoria': 'FINANZAS',
                'url_contenido': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'descripcion': 'Estrategias simples para comenzar a ahorrar sin sentir que te privas de todo.',
                'activo': True
            },
            {
                'titulo': 'Deudas: Como Salir del Ciclo',
                'categoria': 'FINANZAS',
                'url_contenido': 'https://www.youtube.com/watch?v=example3',
                'descripcion': 'Guia paso a paso para liberarte de las deudas y recuperar tu tranquilidad financiera.',
                'activo': True
            },
            
            # EMOCIONAL
            {
                'titulo': 'Tecnicas de Respiracion para la Ansiedad',
                'categoria': 'EMOCIONAL',
                'url_contenido': 'https://www.youtube.com/watch?v=DbDoBzGY3vo',
                'descripcion': 'Ejercicios de respiracion guiada que puedes hacer en cualquier momento para calmar la ansiedad.',
                'activo': True
            },
            {
                'titulo': 'Entendiendo tus Emociones',
                'categoria': 'EMOCIONAL',
                'url_contenido': 'https://www.youtube.com/watch?v=example5',
                'descripcion': 'Aprende a identificar y gestionar tus emociones de manera saludable.',
                'activo': True
            },
            {
                'titulo': 'Mindfulness: Vivir el Presente',
                'categoria': 'EMOCIONAL',
                'url_contenido': 'https://www.youtube.com/watch?v=example6',
                'descripcion': 'Introduccion a la practica del mindfulness para reducir el estres y aumentar el bienestar.',
                'activo': True
            },
            {
                'titulo': 'Como Manejar la Tristeza',
                'categoria': 'EMOCIONAL',
                'url_contenido': 'https://www.youtube.com/watch?v=example7',
                'descripcion': 'Estrategias compasivas para atravesar momentos de tristeza sin juzgarte.',
                'activo': True
            },
            {
                'titulo': 'Autoestima: Construyendo tu Valor',
                'categoria': 'EMOCIONAL',
                'url_contenido': 'https://www.youtube.com/watch?v=example8',
                'descripcion': 'Ejercicios practicos para fortalecer tu autoestima y confianza personal.',
                'activo': True
            },
            
            # SALUD
            {
                'titulo': 'Nutricion Balanceada para Principiantes',
                'categoria': 'SALUD',
                'url_contenido': 'https://www.youtube.com/watch?v=example9',
                'descripcion': 'Los fundamentos de una alimentacion saludable sin dietas extremas.',
                'activo': True
            },
            {
                'titulo': 'Ejercicio en Casa sin Equipo',
                'categoria': 'SALUD',
                'url_contenido': 'https://www.youtube.com/watch?v=example10',
                'descripcion': 'Rutina completa de 20 minutos que puedes hacer en cualquier espacio.',
                'activo': True
            },
            {
                'titulo': 'Higiene del Sueno',
                'categoria': 'SALUD',
                'url_contenido': 'https://www.youtube.com/watch?v=example11',
                'descripcion': 'Consejos cientificos para mejorar la calidad de tu sueno y descansar mejor.',
                'activo': True
            },
            {
                'titulo': 'Hidratacion: Mas que Solo Agua',
                'categoria': 'SALUD',
                'url_contenido': 'https://www.youtube.com/watch?v=example12',
                'descripcion': 'La importancia de mantenerte hidratado y como hacerlo correctamente.',
                'activo': True
            },
            
            # PROFESIONAL
            {
                'titulo': 'Balance Trabajo-Vida Personal',
                'categoria': 'PROFESIONAL',
                'url_contenido': 'https://www.youtube.com/watch?v=example13',
                'descripcion': 'Estrategias para mantener limites saludables entre tu trabajo y vida personal.',
                'activo': True
            },
            {
                'titulo': 'Manejo del Estres Laboral',
                'categoria': 'PROFESIONAL',
                'url_contenido': 'https://www.youtube.com/watch?v=example14',
                'descripcion': 'Tecnicas para lidiar con la presion del trabajo sin agotarte.',
                'activo': True
            },
            {
                'titulo': 'Comunicacion Efectiva en el Trabajo',
                'categoria': 'PROFESIONAL',
                'url_contenido': 'https://www.youtube.com/watch?v=example15',
                'descripcion': 'Mejora tus habilidades de comunicacion para relaciones laborales mas sanas.',
                'activo': True
            },
            {
                'titulo': 'Crecimiento Profesional sin Burnout',
                'categoria': 'PROFESIONAL',
                'url_contenido': 'https://www.youtube.com/watch?v=example16',
                'descripcion': 'Como avanzar en tu carrera cuidando tu salud mental.',
                'activo': True
            },
            
            # RELACIONES
            {
                'titulo': 'Limites Saludables en Relaciones',
                'categoria': 'RELACIONES',
                'url_contenido': 'https://www.youtube.com/watch?v=example17',
                'descripcion': 'Aprende a establecer limites sin sentir culpa para proteger tu bienestar.',
                'activo': True
            },
            {
                'titulo': 'Comunicacion Asertiva con Seres Queridos',
                'categoria': 'RELACIONES',
                'url_contenido': 'https://www.youtube.com/watch?v=example18',
                'descripcion': 'Expresa tus necesidades de manera clara y respetuosa.',
                'activo': True
            },
            {
                'titulo': 'Relaciones Toxicas: Senales y Soluciones',
                'categoria': 'RELACIONES',
                'url_contenido': 'https://www.youtube.com/watch?v=example19',
                'descripcion': 'Identifica patrones daninos y aprende a protegerte.',
                'activo': True
            },
            {
                'titulo': 'Empatia y Escucha Activa',
                'categoria': 'RELACIONES',
                'url_contenido': 'https://www.youtube.com/watch?v=example20',
                'descripcion': 'Mejora la calidad de tus relaciones a traves de la escucha genuina.',
                'activo': True
            },
            
            # OTRO
            {
                'titulo': 'Meditacion Guiada para Principiantes',
                'categoria': 'OTRO',
                'url_contenido': 'https://www.youtube.com/watch?v=example21',
                'descripcion': 'Sesion de meditacion de 10 minutos para comenzar tu practica.',
                'activo': True
            },
            {
                'titulo': 'Gratitud: Transformando tu Perspectiva',
                'categoria': 'OTRO',
                'url_contenido': 'https://www.youtube.com/watch?v=example22',
                'descripcion': 'El poder de la gratitud para mejorar tu bienestar emocional.',
                'activo': True
            },
            {
                'titulo': 'Rutina Matutina para un Dia Positivo',
                'categoria': 'OTRO',
                'url_contenido': 'https://www.youtube.com/watch?v=example23',
                'descripcion': 'Crea una rutina matutina que establezca un tono positivo para tu dia.',
                'activo': True
            },
        ]

        self.stdout.write(f'Creando {len(recursos_data)} recursos de bienestar...')
        created_count = 0

        for recurso_info in recursos_data:
            recurso, created = RecursoCrecimiento.objects.get_or_create(
                titulo=recurso_info['titulo'],
                defaults=recurso_info
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  [OK] Creado: {recurso.titulo}"))
            else:
                self.stdout.write(f"  [-] Ya existe: {recurso.titulo}")

        self.stdout.write(self.style.SUCCESS(f'\n[EXITO] Proceso completado:'))
        self.stdout.write(f'   - {created_count} recursos creados')
        self.stdout.write(f'   - {len(recursos_data) - created_count} recursos ya existian')
        self.stdout.write(f'   - Total en BD: {RecursoCrecimiento.objects.count()}')
