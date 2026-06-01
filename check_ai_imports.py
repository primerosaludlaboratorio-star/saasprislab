
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_imports():
    print("Testing imports...")
    try:
        from core.views import ia_dashboard
        print("OK: core.views.ia_dashboard imported successfully")
    except Exception as e:
        print(f"FAIL: Failed to import core.views.ia_dashboard: {e}")

    try:
        from core.ai_brain import responder
        print("OK: core.ai_brain imported successfully")
        
        # Test responder execution
        try:
            print("Testing responder execution...")
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.first()
            if user:
                print(f"User found: {user.username}")
                # Mock request or user object if needed, but responder only needs user object
                # responder calls get_gemini_model which might make network call
                # We just want to ensure no import/syntax errors crash it immediately
                # But we won't actually call it to avoid network lag/errors in this script unless necessary
                # Just inspecting it
                print("Responder function exists.")
            else:
                print("No user found to test responder.")
        except Exception as e:
            print(f"FAIL: Error preparing responder test: {e}")

    except Exception as e:
        print(f"FAIL: Failed to import core.ai_brain: {e}")

    try:
        from google import generativeai as genai
        print(f"OK: google.generativeai imported. Version: {genai.__version__}")
        try:
            from google.generativeai.types import GenerationConfig
            print("OK: GenerationConfig found in google.generativeai.types")
        except ImportError:
            print("WARN: GenerationConfig NOT found in google.generativeai.types")
            try:
                from google.generativeai import GenerationConfig
                print("OK: GenerationConfig found in google.generativeai")
            except ImportError:
                print("FAIL: GenerationConfig NOT found in google.generativeai top level either")

    except ImportError:
        print("FAIL: google.generativeai NOT installed")
    except Exception as e:
        print(f"FAIL: Error checking google.generativeai: {e}")

if __name__ == "__main__":
    test_imports()
