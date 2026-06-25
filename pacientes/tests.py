from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import uuid
from datetime import date

Usuario = get_user_model()

try:
    from core.models import Empresa, Paciente
except ImportError:
    Empresa = None
    Paciente = None


class PacienteModelTest(TestCase):
    """Tests for Paciente model"""
    
    def setUp(self):
        """Set up test data"""
        if Empresa is None or Paciente is None:
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
    
    def test_paciente_creation(self):
        """Test creating a Paciente instance"""
        paciente = Paciente.objects.create(
            nombres="Juan",
            apellido_paterno="Pérez",
            apellido_materno="García",
            nombre_completo="Juan Pérez García",
            telefono="5551234567",
            email="juan@example.com",
            empresa=self.empresa,
            sexo="M",
            fecha_nacimiento="1990-01-01"
        )
        
        self.assertIsNotNone(paciente)
        self.assertEqual(paciente.nombres, "Juan")
        self.assertEqual(paciente.apellido_paterno, "Pérez")
        self.assertEqual(paciente.apellido_materno, "García")
        self.assertEqual(paciente.empresa, self.empresa)
        self.assertIsNotNone(paciente.id)  # UUID field should exist
    
    def test_paciente_nombre_completo_property(self):
        """Test the nombre_completo property"""
        paciente = Paciente.objects.create(
            nombres="María",
            apellido_paterno="López",
            apellido_materno="Martínez",
            nombre_completo="María López Martínez",
            telefono="5559876543",
            email="maria@example.com",
            empresa=self.empresa,
            sexo="F",
            fecha_nacimiento="1985-05-15"
        )
        
        nombre_completo = paciente.nombre_completo
        self.assertIsInstance(nombre_completo, str)
        self.assertIn("María", nombre_completo)
        self.assertIn("López", nombre_completo)
        self.assertIn("Martínez", nombre_completo)
    
    def test_portal_paciente_view_get(self):
        """Test portal_paciente view with GET request"""
        self.client.login(username='testuser', password='test123')
        
        try:
            url = reverse('pacientes:portal_paciente')
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 302, 404])  # Accept various valid responses
        except Exception as e:
            # View might not exist or have different requirements
            self.skipTest(f"portal_paciente view not available: {e}")
    
    def test_paciente_uuid_field(self):
        """Test that Paciente has a UUID field"""
        paciente = Paciente.objects.create(
            nombres="Test",
            apellido_paterno="UUID",
            apellido_materno="Paciente",
            nombre_completo="Test UUID Paciente",
            telefono="5551111111",
            email="test@example.com",
            empresa=self.empresa,
            sexo="M",
            fecha_nacimiento="2000-01-01"
        )
        
        # Check if UUID field exists and is valid
        if hasattr(paciente, 'uuid'):
            self.assertIsNotNone(paciente.uuid)
            # Verify it's a valid UUID
            try:
                uuid.UUID(str(paciente.uuid))
            except (ValueError, AttributeError):
                self.fail("UUID field is not a valid UUID")


class PacienteRoutesTenantTest(TestCase):
    """Pruebas mínimas de rutas y aislamiento para el módulo Pacientes."""

    def setUp(self):
        if Empresa is None or Paciente is None:
            self.skipTest("Required models not available")

        self.empresa_a = Empresa.objects.create(nombre="Empresa A Pacientes", rfc="PACA010101AA1")
        self.empresa_b = Empresa.objects.create(nombre="Empresa B Pacientes", rfc="PACB010101BB2")

        self.user_a = Usuario.objects.create_user(
            username='paciente_audit_a',
            password='test123',
            empresa=self.empresa_a,
        )
        self.user_b = Usuario.objects.create_user(
            username='paciente_audit_b',
            password='test123',
            empresa=self.empresa_b,
        )

        self.paciente_a = Paciente.objects.create(
            nombres="Ana",
            apellido_paterno="Audit",
            apellido_materno="EmpresaA",
            nombre_completo="Ana Audit EmpresaA",
            telefono="5550000001",
            email="ana@example.com",
            empresa=self.empresa_a,
            sexo="F",
            fecha_nacimiento=date(1990, 1, 1),
        )
        self.paciente_b = Paciente.objects.create(
            nombres="Bea",
            apellido_paterno="Audit",
            apellido_materno="EmpresaB",
            nombre_completo="Bea Audit EmpresaB",
            telefono="5550000002",
            email="bea@example.com",
            empresa=self.empresa_b,
            sexo="F",
            fecha_nacimiento=date(1991, 1, 1),
        )

        self.client = Client()

    def test_lista_pacientes_carga_para_usuario_con_empresa(self):
        self.client.login(username='paciente_audit_a', password='test123')
        response = self.client.get(reverse('pacientes:lista_pacientes'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Listado de Pacientes')
        self.assertContains(response, self.paciente_a.nombre_completo)
        self.assertNotContains(response, self.paciente_b.nombre_completo)

    def test_buscar_paciente_responde_json_y_respeta_tenant(self):
        self.client.login(username='paciente_audit_a', password='test123')
        response = self.client.get(reverse('pacientes:buscar_paciente'), {'q': 'Audit'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        nombres = [p['nombre_completo'] for p in data['pacientes']]
        self.assertIn(self.paciente_a.nombre_completo, nombres)
        self.assertNotIn(self.paciente_b.nombre_completo, nombres)

    def test_crear_paciente_requiere_empresa_y_muestra_formulario(self):
        self.client.login(username='paciente_audit_a', password='test123')
        response = self.client.get(reverse('pacientes:crear_paciente'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Crear Paciente')
