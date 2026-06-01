"""
Script para poblar recursos de bienestar en la base de datos.
Ejecutar: python poblar_recursos_bienestar.py
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from bienestar.models import RecursoCrecimiento

# Limpiar recursos existentes (opcional)
print("Limpiando recursos existentes...")
RecursoCrecimiento.objects.all().delete()

# Recursos de ejemplo estilo YANA
recursos_data = [
    # FINANZAS
    {
        'titulo': 'Presupuesto Personal Saludable',
        'categoria': 'FINANZAS',
        'url_contenido': 'https://www.youtube.com/watch?v=HQzoZfc3GwQ',
        'descripcion': 'Aprende a crear y mantener un presupuesto que te ayude a alcanzar tus metas financieras sin estrés.',
        'activo': True
    },
    {
        'titulo': 'Ahorro Inteligente: Pequeños Pasos, Grandes Resultados',
        'categoria': 'FINANZAS',
        'url_contenido': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'descripcion': 'Estrategias simples para comenzar a ahorrar sin sentir que te privas de todo.',
        'activo': True
    },
    {
        'titulo': 'Deudas: Cómo Salir del Ciclo',
        'categoria': 'FINANZAS',
        'url_contenido': 'https://www.youtube.com/watch?v=example3',
        'descripcion': 'Guía paso a paso para liberarte de las deudas y recuperar tu tranquilidad financiera.',
        'activo': True
    },
    
    # EMOCIONAL
    {
        'titulo': 'Técnicas de Respiración para la Ansiedad',
        'categoria': 'EMOCIONAL',
        'url_contenido': 'https://www.youtube.com/watch?v=DbDoBzGY3vo',
        'descripcion': 'Ejercicios de respiración guiada que puedes hacer en cualquier momento para calmar la ansiedad.',
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
        'descripcion': 'Introducción a la práctica del mindfulness para reducir el estrés y aumentar el bienestar.',
        'activo': True
    },
    {
        'titulo': 'Cómo Manejar la Tristeza',
        'categoria': 'EMOCIONAL',
        'url_contenido': 'https://www.youtube.com/watch?v=example7',
        'descripcion': 'Estrategias compasivas para atravesar momentos de tristeza sin juzgarte.',
        'activo': True
    },
    {
        'titulo': 'Autoestima: Construyendo tu Valor',
        'categoria': 'EMOCIONAL',
        'url_contenido': 'https://www.youtube.com/watch?v=example8',
        'descripcion': 'Ejercicios prácticos para fortalecer tu autoestima y confianza personal.',
        'activo': True
    },
    
    # SALUD
    {
        'titulo': 'Nutrición Balanceada para Principiantes',
        'categoria': 'SALUD',
        'url_contenido': 'https://www.youtube.com/watch?v=example9',
        'descripcion': 'Los fundamentos de una alimentación saludable sin dietas extremas.',
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
        'titulo': 'Higiene del Sueño',
        'categoria': 'SALUD',
        'url_contenido': 'https://www.youtube.com/watch?v=example11',
        'descripcion': 'Consejos científicos para mejorar la calidad de tu sueño y descansar mejor.',
        'activo': True
    },
    {
        'titulo': 'Hidratación: Más que Solo Agua',
        'categoria': 'SALUD',
        'url_contenido': 'https://www.youtube.com/watch?v=example12',
        'descripcion': 'La importancia de mantenerte hidratado y cómo hacerlo correctamente.',
        'activo': True
    },
    
    # PROFESIONAL
    {
        'titulo': 'Balance Trabajo-Vida Personal',
        'categoria': 'PROFESIONAL',
        'url_contenido': 'https://www.youtube.com/watch?v=example13',
        'descripcion': 'Estrategias para mantener límites saludables entre tu trabajo y vida personal.',
        'activo': True
    },
    {
        'titulo': 'Manejo del Estrés Laboral',
        'categoria': 'PROFESIONAL',
        'url_contenido': 'https://www.youtube.com/watch?v=example14',
        'descripcion': 'Técnicas para lidiar con la presión del trabajo sin agotarte.',
        'activo': True
    },
    {
        'titulo': 'Comunicación Efectiva en el Trabajo',
        'categoria': 'PROFESIONAL',
        'url_contenido': 'https://www.youtube.com/watch?v=example15',
        'descripcion': 'Mejora tus habilidades de comunicación para relaciones laborales más sanas.',
        'activo': True
    },
    {
        'titulo': 'Crecimiento Profesional sin Burnout',
        'categoria': 'PROFESIONAL',
        'url_contenido': 'https://www.youtube.com/watch?v=example16',
        'descripcion': 'Cómo avanzar en tu carrera cuidando tu salud mental.',
        'activo': True
    },
    
    # RELACIONES
    {
        'titulo': 'Límites Saludables en Relaciones',
        'categoria': 'RELACIONES',
        'url_contenido': 'https://www.youtube.com/watch?v=example17',
        'descripcion': 'Aprende a establecer límites sin sentir culpa para proteger tu bienestar.',
        'activo': True
    },
    {
        'titulo': 'Comunicación Asertiva con Seres Queridos',
        'categoria': 'RELACIONES',
        'url_contenido': 'https://www.youtube.com/watch?v=example18',
        'descripcion': 'Expresa tus necesidades de manera clara y respetuosa.',
        'activo': True
    },
    {
        'titulo': 'Relaciones Tóxicas: Señales y Soluciones',
        'categoria': 'RELACIONES',
        'url_contenido': 'https://www.youtube.com/watch?v=example19',
        'descripcion': 'Identifica patrones dañinos y aprende a protegerte.',
        'activo': True
    },
    {
        'titulo': 'Empatía y Escucha Activa',
        'categoria': 'RELACIONES',
        'url_contenido': 'https://www.youtube.com/watch?v=example20',
        'descripcion': 'Mejora la calidad de tus relaciones a través de la escucha genuina.',
        'activo': True
    },
    
    # OTRO
    {
        'titulo': 'Meditación Guiada para Principiantes',
        'categoria': 'OTRO',
        'url_contenido': 'https://www.youtube.com/watch?v=example21',
        'descripcion': 'Sesión de meditación de 10 minutos para comenzar tu práctica.',
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
        'titulo': 'Rutina Matutina para un Día Positivo',
        'categoria': 'OTRO',
        'url_contenido': 'https://www.youtube.com/watch?v=example23',
        'descripcion': 'Crea una rutina matutina que establezca un tono positivo para tu día.',
        'activo': True
    },
]

print(f"Creando {len(recursos_data)} recursos de bienestar...")
created_count = 0

for recurso_info in recursos_data:
    recurso, created = RecursoCrecimiento.objects.get_or_create(
        titulo=recurso_info['titulo'],
        defaults=recurso_info
    )
    if created:
        created_count += 1
        print(f"  [OK] Creado: {recurso.titulo} ({recurso.get_categoria_display()})")
    else:
        print(f"  [-] Ya existe: {recurso.titulo}")

print(f"\n[EXITO] Proceso completado:")
print(f"   - {created_count} recursos creados")
print(f"   - {len(recursos_data) - created_count} recursos ya existian")
print(f"   - Total en BD: {RecursoCrecimiento.objects.count()}")
