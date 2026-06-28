"""
Test de conexión con Gemini API v1 (estable).
Verifica que el cliente esté correctamente configurado y funcione.
"""
from django.core.management.base import BaseCommand
from core.utils.gemini_client import test_gemini_connection


class Command(BaseCommand):
    help = 'Prueba la conexión con Gemini API v1 y verifica que funcione correctamente'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== PRUEBA DE CONEXION GEMINI API v1 ===\n'))
        
        self.stdout.write('Ejecutando test de conexion...')
        resultado = test_gemini_connection()
        
        if resultado['success']:
            self.stdout.write(self.style.SUCCESS('\n[OK] CONEXION EXITOSA'))
            self.stdout.write(f"   Modelo: {resultado['model']}")
            self.stdout.write(f"   Mensaje: {resultado['message']}")
            self.stdout.write(f"   Respuesta: {resultado.get('response', 'N/A')}")
            self.stdout.write(self.style.SUCCESS('\n=== Jonathan, PRIS esta en linea y lista para la batalla ===\n'))
        else:
            self.stdout.write(self.style.ERROR('\n[ERROR] FALLO DE CONEXION'))
            self.stdout.write(self.style.ERROR(f"   Mensaje: {resultado['message']}"))
            self.stdout.write(self.style.WARNING('\nVerifica:'))
            self.stdout.write('   1. Que GOOGLE_API_KEY esté configurada en variables de entorno')
            self.stdout.write('   2. Que google-generativeai esté instalado: pip install google-generativeai')
            self.stdout.write('   3. Que la API key sea válida y tenga permisos para Gemini API')
