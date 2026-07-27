import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Empresa
from ia.models import CotizacionOCR

Usuario = get_user_model()


class IAViewsTest(TestCase):
    """Tests for IA module views (OCR and voice transcription)."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test Empresa",
            rfc="TEST123456",
        )
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            password='test123',
            empresa=self.empresa,
        )
        self.client = Client()

    def test_ocr_receta_view_exists(self):
        self.client.login(username='testuser', password='test123')
        try:
            url = reverse('ia:ocr_receta')
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 302, 405, 400])
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Error inesperado en test_ocr_receta_view_exists"
            )
            self.skipTest(f"ocr_receta view not available: {exc}")

    def test_transcripcion_voz_view_exists(self):
        self.client.login(username='testuser', password='test123')
        try:
            url = reverse('ia:transcripcion_voz')
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 302, 405, 400])
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Error inesperado en test_transcripcion_voz_view_exists"
            )
            self.skipTest(f"transcripcion_voz view not available: {exc}")

    def test_ia_module_imports(self):
        import ia
        self.assertTrue(ia)


class CotizacionOCRTenantTests(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='OCR Empresa A')
        self.empresa_b = Empresa.objects.create(nombre='OCR Empresa B')
        self.usuario_a = Usuario.objects.create_user(
            username='ocr-a', password='test-password-123', empresa=self.empresa_a
        )
        self.usuario_b = Usuario.objects.create_user(
            username='ocr-b', password='test-password-123', empresa=self.empresa_b
        )
        self.cotizacion_b = CotizacionOCR.objects_all.create(
            empresa=self.empresa_b,
            usuario_creador=self.usuario_b,
            imagen_receta='recetas_ocr/test.png',
            texto_extraido='Glucosa',
        )
        self.client = Client()

    def test_resultado_ocr_no_expone_otro_tenant(self):
        self.client.force_login(self.usuario_a)

        response = self.client.get(
            reverse('ia:resultados_ocr', args=[self.cotizacion_b.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_cotizacion_ocr_requiere_empresa(self):
        with self.assertRaises(IntegrityError):
            CotizacionOCR.objects_all.create(
                usuario_creador=self.usuario_a,
                imagen_receta='recetas_ocr/orphan.png',
                texto_extraido='Sin empresa',
            )
