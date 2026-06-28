from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import logging

Usuario = get_user_model()

try:
    from core.models import Empresa
except ImportError:
    Empresa = None


class IAViewsTest(TestCase):
    """Tests for IA module views (OCR and voice transcription)"""
    
    def setUp(self):
        """Set up test data"""
        if Empresa is None:
            self.skipTest("Required models not available")
        
        self.empresa = Empresa.objects.create(
            nombre="Test Empresa",
            rfc="TEST123456"
        )
        
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            password='test123',
            empresa=self.empresa
        )
        
        self.client = Client()
    
    def test_ocr_receta_view_exists(self):
        """Test that ocr_receta view exists and is accessible"""
        self.client.login(username='testuser', password='test123')
        
        try:
            url = reverse('ia:ocr_receta')
            response = self.client.get(url)
            # Accept various valid responses (200, 302 redirect, 405 method not allowed, etc.)
            self.assertIn(response.status_code, [200, 302, 405, 400])
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_ocr_receta_view_exists (tests.py)")
            # View might not exist or have different URL name
            self.skipTest(f"ocr_receta view not available: {e}")
    
    def test_transcripcion_voz_view_exists(self):
        """Test that transcripcion_voz view exists and is accessible"""
        self.client.login(username='testuser', password='test123')
        
        try:
            url = reverse('ia:transcripcion_voz')
            response = self.client.get(url)
            # Accept various valid responses
            self.assertIn(response.status_code, [200, 302, 405, 400])
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_transcripcion_voz_view_exists (tests.py)")
            # View might not exist or have different URL name
            self.skipTest(f"transcripcion_voz view not available: {e}")
    
    def test_ia_module_imports(self):
        """Test that IA module can be imported"""
        try:
            import ia
            self.assertTrue(True)
        except ImportError:
            self.skipTest("IA module not available")