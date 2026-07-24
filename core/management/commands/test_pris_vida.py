"""Prueba de vida del proveedor activo de PRIS."""

from django.conf import settings
from django.core.management.base import BaseCommand

from core.utils.gemini_client import _get_ai_provider, _get_api_key as _get_gemini_key


class Command(BaseCommand):
    help = "Verifica el proveedor activo de PRIS sin mostrar secretos"

    def handle(self, *args, **options):
        provider = _get_ai_provider()
        self.stdout.write(f"=== PRUEBA DE VIDA: PRIS ({provider}) ===")

        if provider == "deepseek":
            from core.utils.deepseek_client import test_deepseek_connection

            configured = bool((getattr(settings, "DEEPSEEK_API_KEY", "") or "").strip())
            if not configured:
                self.stdout.write(self.style.ERROR("[ERROR] DEEPSEEK_API_KEY no está configurada."))
                return
            resultado = test_deepseek_connection()
        else:
            from core.utils.gemini_client import test_gemini_connection

            if not _get_gemini_key():
                self.stdout.write(self.style.ERROR("[ERROR] GOOGLE_API_KEY no está configurada."))
                return
            resultado = test_gemini_connection()

        if resultado.get("success"):
            self.stdout.write(self.style.SUCCESS("[OK] PRIS está conectada y lista."))
            self.stdout.write(f"Modelo: {resultado.get('model', 'no informado')}")
            self.stdout.write(f"Respuesta: {resultado.get('response', 'OK')}")
            return

        self.stdout.write(self.style.ERROR(f"[ERROR] {resultado.get('message', 'Proveedor sin respuesta.')}"))
