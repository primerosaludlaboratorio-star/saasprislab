"""
Comando de gestión para cargar la biblioteca inicial de liderazgo.
Ejecutar: python manage.py cargar_biblioteca_inicial
"""
from django.core.management.base import BaseCommand
from core.models import LibroLiderazgo, Empresa


class Command(BaseCommand):
    help = 'Carga el libro inicial de la Biblioteca de Liderazgo (Viktor Frankl)'

    def handle(self, *args, **options):
        # Obtener todas las empresas activas
        empresas = Empresa.objects.filter(activa=True)
        
        if not empresas.exists():
            self.stdout.write(self.style.WARNING('No hay empresas activas en el sistema.'))
            return
        
        # Libro inicial: "El hombre en busca de sentido" - Viktor Frankl
        libro_data = {
            'titulo': 'El hombre en busca de sentido',
            'autor': 'Viktor Frankl',
            'portada_url': 'https://images-na.ssl-images-amazon.com/images/I/71Z2eD-WfGL.jpg',
            'resumen_ejecutivo': (
                'La última libertad humana es elegir la actitud ante cualquier circunstancia. '
                'Viktor Frankl, sobreviviente del Holocausto, enseña que incluso en las situaciones más adversas, '
                'tenemos el poder de encontrar propósito y significado. La logoterapia demuestra que la búsqueda '
                'de sentido es la motivación principal del ser humano.'
            ),
            'aplicacion_practica': (
                'Resiliencia ante crisis operativas. Cuando el laboratorio enfrenta problemas críticos '
                '(pandemia, escasez de reactivos, rotación de personal), el director puede mantener la calma '
                'y encontrar oportunidades en lugar de desesperación. Aplicar este principio en reuniones de equipo: '
                'transformar cada crisis en un momento de aprendizaje y crecimiento organizacional.'
            ),
            'estado_lectura': 'POR_LEER'
        }
        
        libros_creados = 0
        libros_existentes = 0
        
        for empresa in empresas:
            # Verificar si ya existe este libro para esta empresa
            existe = LibroLiderazgo.objects.filter(
                empresa=empresa,
                titulo=libro_data['titulo'],
                autor=libro_data['autor']
            ).exists()
            
            if not existe:
                LibroLiderazgo.objects.create(empresa=empresa, **libro_data)
                libros_creados += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[OK] Libro agregado para empresa: {empresa.nombre}'
                    )
                )
            else:
                libros_existentes += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'[SKIP] Libro ya existe para empresa: {empresa.nombre}'
                    )
                )
        
        self.stdout.write(self.style.SUCCESS(
            f'\n[COMPLETADO] Proceso finalizado:\n'
            f'   - Libros creados: {libros_creados}\n'
            f'   - Libros ya existentes: {libros_existentes}'
        ))
