"""
Comando de Django para probar la conexión con Gemini API.
Usa el cliente centralizado google.genai (SDK unificado v1.60+).
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import sys
import logging


class Command(BaseCommand):
    help = 'Prueba la conexión con Gemini API via google.genai SDK'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== PRUEBA DE CONEXIÓN GEMINI API (google.genai SDK) ===\n'))

        # 1. Verificar que la librería está instalada
        self.stdout.write('1. Verificando instalación de google-genai...')
        try:
            from google import genai
            self.stdout.write(self.style.SUCCESS('   [OK] google-genai importado correctamente'))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'   [ERROR] Error al importar: {e}'))
            self.stdout.write(self.style.WARNING('   Ejecuta: pip install google-genai'))
            sys.exit(1)

        # 2. Verificar API Key
        self.stdout.write('\n2. Verificando GOOGLE_API_KEY...')
        api_key = (
            getattr(settings, 'GOOGLE_API_KEY', '') or
            getattr(settings, 'GEMINI_API_KEY', '') or
            getattr(settings, 'GOOGLE_GEMINI_API_KEY', '')
        )
        if not api_key:
            self.stdout.write(self.style.WARNING('   [ADVERTENCIA] GOOGLE_API_KEY no configurada'))
        else:
            self.stdout.write(self.style.SUCCESS(f'   [OK] GOOGLE_API_KEY configurada ({len(api_key)} chars)'))

        # 3. Crear cliente
        self.stdout.write('\n3. Creando cliente google.genai...')
        try:
            from core.utils.gemini_client import get_gemini_client
            client = get_gemini_client()
            self.stdout.write(self.style.SUCCESS('   [OK] Cliente creado correctamente'))
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (test_gemini_connection.py)")
            self.stdout.write(self.style.ERROR(f'   [ERROR] {e}'))
            sys.exit(1)

        # 4. Prueba de ping real
        self.stdout.write('\n4. Realizando prueba de ping a gemini-2.0-flash...')
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents="Responde solo con 'OK'."
            )
            texto = response.text.strip()
            self.stdout.write(self.style.SUCCESS(f'   [OK] Respuesta: {texto[:80]}'))
            self.stdout.write(self.style.SUCCESS('\n=== CONEXIÓN GEMINI VERIFICADA ==='))
            self.stdout.write(self.style.SUCCESS('   Estado: OPERATIVO'))
            self.stdout.write(self.style.SUCCESS('   Modelo: gemini-2.0-flash'))
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (test_gemini_connection.py)")
            self.stdout.write(self.style.ERROR(f'   [ERROR] Ping fallido: {e}'))
            sys.exit(1)

        self.stdout.write('')