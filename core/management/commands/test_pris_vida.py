"""
Prueba de vida rápida: Verifica que PRIS (Gemini API) esté en línea.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from core.utils.gemini_client import test_gemini_connection


class Command(BaseCommand):
    help = 'Prueba rápida de conexión con Gemini API v1'

    def handle(self, *args, **options):
        self.stdout.write('=== PRUEBA DE VIDA: PRIS (Gemini API) ===\n')
        
        # Verificar que la API key esté configurada
        api_key = getattr(settings, 'GOOGLE_API_KEY', '')
        if not api_key:
            self.stdout.write(self.style.ERROR('[ERROR] GOOGLE_API_KEY no esta configurada en settings'))
            self.stdout.write(self.style.WARNING('\nConfigura la API key en .env o settings.py'))
            self.stdout.write(self.style.WARNING('Una vez configurada, ejecuta este comando nuevamente.'))
            return
        
        self.stdout.write('[INFO] API key encontrada, probando conexion...\n')
        
        resultado = test_gemini_connection()
        
        if resultado['success']:
            self.stdout.write(self.style.SUCCESS('[OK] PRIS esta en linea y lista para la batalla'))
            self.stdout.write(self.style.SUCCESS(f'   Modelo: {resultado["model"]}'))
            self.stdout.write(self.style.SUCCESS(f'   Respuesta: {resultado.get("response", "OK")}'))
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('\nJonathan, PRIS esta en linea y lista para la batalla.\n'))
        else:
            error_msg = resultado["message"]
            self.stdout.write(self.style.ERROR(f'[ERROR] Error: {error_msg}'))
            
            # Diagnóstico específico
            if '404' in error_msg or 'not found' in error_msg.lower():
                self.stdout.write(self.style.WARNING('\n[DIAGNOSTICO] Error 404 detectado:'))
                self.stdout.write('   - Verifica que uses google-genai (nuevo) en lugar de google-generativeai (deprecado)')
                self.stdout.write('   - Verifica que el modelo sea: gemini-1.5-flash-latest')
                self.stdout.write('   - Verifica que la API key tenga permisos para Gemini API v1')
            elif 'API key' in error_msg or 'authentication' in error_msg.lower():
                self.stdout.write(self.style.WARNING('\n[DIAGNOSTICO] Error de autenticacion:'))
                self.stdout.write('   - Verifica que GOOGLE_API_KEY sea valida')
                self.stdout.write('   - Verifica que la API key tenga permisos para Gemini API')
            else:
                self.stdout.write(self.style.WARNING('\nVerifica:'))
                self.stdout.write('   1. Que GOOGLE_API_KEY este configurada correctamente')
                self.stdout.write('   2. Que google-genai este instalado: pip install google-genai')
                self.stdout.write('   3. Que la API key tenga permisos para Gemini API v1')
