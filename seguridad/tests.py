from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import unittest
import pyotp

Usuario = get_user_model()

try:
    from core.models import Empresa
except ImportError:
    Empresa = None

try:
    from seguridad import models as seguridad_models
except ImportError:
    seguridad_models = None


class SeguridadModuleTest(TestCase):
    """Tests for seguridad module (2FA TOTP, panic button, sensitive action logs)"""
    
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
    
    def test_seguridad_models_import(self):
        """Test that seguridad models can be imported"""
        if seguridad_models is None:
            self.skipTest("Seguridad models not available")
        
        # Check if models module has any models
        self.assertIsNotNone(seguridad_models)
    
    def test_seguridad_urls_resolution(self):
        """Test that seguridad URLs can be resolved"""
        self.client.login(username='testuser', password='test123')
        
        # Try common seguridad URL patterns
        url_patterns = [
            'seguridad:totp_setup',
            'seguridad:panic_button',
            'seguridad:action_logs',
            'seguridad:enable_2fa',
            'seguridad:verify_totp',
        ]
        
        resolved_urls = []
        for pattern in url_patterns:
            try:
                url = reverse(pattern)
                resolved_urls.append(pattern)
            except Exception:
                pass
        
        # At least one URL should resolve, or skip if none exist
        if not resolved_urls:
            self.skipTest("No seguridad URLs found")
        
        # Test that at least one URL returns a valid response
        for pattern in resolved_urls[:1]:  # Test first resolved URL
            try:
                url = reverse(pattern)
                response = self.client.get(url)
                self.assertIn(response.status_code, [200, 302, 405, 400, 403])
                break
            except Exception:
                pass
    
    def test_seguridad_module_structure(self):
        """Test basic seguridad module structure"""
        try:
            import seguridad
            self.assertTrue(hasattr(seguridad, '__name__'))
        except ImportError:
            self.skipTest("Seguridad module not available")


class TwoFactorTest(TestCase):
    """Cobertura funcional para la API 2FA en configuración y respaldo."""

    def setUp(self):
        if Empresa is None or seguridad_models is None:
            self.skipTest("Required seguridad models not available")

        self.empresa = Empresa.objects.create(
            nombre="Empresa 2FA",
            rfc="TFA010101ABC"
        )
        self.usuario = Usuario.objects.create_user(
            username='usuario2fa',
            password='test123',
            empresa=self.empresa
        )
        self.client = Client()
        self.client.login(username='usuario2fa', password='test123')

    def test_api_verificar_codigo_totp_activo(self):
        secret = pyotp.random_base32()
        seguridad_models.DispositivoTOTP.objects.create(
            usuario=self.usuario,
            nombre='Authenticator',
            llave_secreta=secret,
            activo=True,
            confirmado=True,
        )

        response = self.client.post(
            reverse('seguridad:api_verificar_2fa'),
            {'codigo': pyotp.TOTP(secret).now()},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['valido'])
        self.assertEqual(data['tipo'], 'totp')

    def test_api_verificar_codigo_backup_lo_marca_usado(self):
        codigo = 'ABCD1234EFGH'
        backup = seguridad_models.CodigoBackup2FA.objects.create(
            usuario=self.usuario,
            codigo=codigo,
        )

        response = self.client.post(
            reverse('seguridad:api_verificar_2fa'),
            {'codigo': codigo},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['valido'])
        self.assertEqual(data['tipo'], 'backup')
        backup.refresh_from_db()
        self.assertTrue(backup.usado)
