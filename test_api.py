
import os
import django
import sys
import traceback

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_gemini_pro_connection():
    print("Iniciando prueba de conexion con Gemini 1.5 Pro...")
    
    try:
        # Importar cliente centralizado
        from core.utils.gemini_client import get_gemini_model
        
        # Intentar obtener el modelo Pro
        print("1. Inicializando modelo 'gemini-1.5-pro'...")
        model = get_gemini_model('gemini-1.5-pro')
        print("Modelo inicializado correctamente.")
        
        # Prueba de generación simple
        print("2. Enviando prompt de prueba...")
        response = model.generate_content("Responde solo con la palabra: CONECTADO")
        
        if response and response.text:
            print(f"Respuesta recibida: {response.text.strip()}")
            print("Prueba exitosa! Gemini 1.5 Pro esta operativo.")
        else:
            print("Conexion establecida pero sin respuesta de texto.")
            
    except Exception as e:
        print(f"Error en la prueba: {str(e)}")
        if "GOOGLE_API_KEY" in str(e):
            print("\nATENCION: La variable de entorno GOOGLE_API_KEY no esta configurada.")
            print("   Por favor, configurela en su archivo .env o en las variables de entorno del sistema.")
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini_pro_connection()
