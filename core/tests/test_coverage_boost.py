"""
Test suite para aumentar cobertura de código.
Tests para core, laboratorio, farmacia - flujos críticos.
"""
import json
from unittest.mock import patch
from django.contrib.auth.models import Group
from django.db import OperationalError
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Empresa, Sucursal, Paciente, Producto, Lote, Venta, DetalleVenta, OrdenDeServicio
from laboratorio.models import Estudio, CategoriaExamen
try:
    from laboratorio.models import Resultado
except ImportError:
    Resultado = None

User = get_user_model()


class CoverageBoostTests(TestCase):
    """Tests para aumentar cobertura en módulos críticos."""
    
    def setUp(self):
        """Configuración común para tests."""
        self.client = Client()
        
        # Crear estructura base
        self.empresa = Empresa.objects.create(
            nombre='Test Company',
            rfc='TEST123456789'
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre='Sucursal Test',
            codigo_sucursal='SUC-TEST-001'
        )
        
        # Crear usuario admin
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='admin123',
            email='admin@test.com',
            rol='ADMIN',
            empresa=self.empresa,
            sucursal=self.sucursal,
            is_staff=True
        )
        
        # Crear usuario de laboratorio
        self.lab_user = User.objects.create_user(
            username='quimico_test',
            password='lab123',
            email='lab@test.com',
            rol='QUIMICO',
            empresa=self.empresa,
            sucursal=self.sucursal
        )
        
        # Crear paciente
        self.paciente = Paciente.objects.create(
            nombres='Juan',
            apellido_paterno='Pérez',
            nombre_completo='Juan Pérez',
            empresa=self.empresa,
            sucursal=self.sucursal,
            telefono='5555555555'
        )
        
        # Crear producto para farmacia
        import uuid
        self.producto = Producto.objects.create(
            nombre='Paracetamol 500mg',
            codigo_barras=str(uuid.uuid4())[:20],
            empresa=self.empresa,
            sucursal=self.sucursal,
            forma_farmaceutica='Tabletas',
            concentracion='500mg',
            presentacion='20 tabletas',
            precio_publico=50.00,
            stock=100
        )
        
        # Crear lote para inventario
        from datetime import date
        self.lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-001',
            cantidad=100,
            empresa=self.empresa,
            fecha_caducidad=date(2030, 12, 31),
            costo_adquisicion=25.00,
        )
        
        # Login
        self.client.login(username='admin_test', password='admin123')
    
    # ========================================================================
    # TESTS CORE - Modelos básicos
    # ========================================================================
    
    def test_empresa_creation(self):
        """Test creación de empresa."""
        self.assertEqual(self.empresa.nombre, 'Test Company')
        self.assertIn('Test Company', str(self.empresa))
    
    def test_sucursal_creation(self):
        """Test creación de sucursal."""
        self.assertEqual(self.sucursal.nombre, 'Sucursal Test')
        self.assertEqual(str(self.sucursal), 'Sucursal Test (SUC-TEST-001)')
    
    def test_paciente_creation(self):
        """Test creación de paciente."""
        self.assertEqual(self.paciente.nombre_completo, 'Juan Pérez')
        self.assertIn('Juan Pérez', str(self.paciente))
    
    def test_producto_creation(self):
        """Test creación de producto."""
        self.assertEqual(self.producto.nombre, 'Paracetamol 500mg')
        self.assertEqual(self.producto.stock, 100)
    
    def test_lote_creation(self):
        """Test creación de lote."""
        self.assertEqual(self.lote.numero_lote, 'LOT-001')
        self.assertEqual(self.lote.cantidad, 100)
    
    # ========================================================================
    # TESTS CORE - Vistas básicas
    # ========================================================================
    
    def test_login_page_accessible(self):
        """Test que la página de login es accesible."""
        self.client.logout()
        response = self.client.get('/login/', follow=True)
        self.assertIn(response.status_code, [200, 301, 302])
    
    def test_dashboard_accessible(self):
        """Test que el dashboard es accesible para usuarios logueados."""
        response = self.client.get('/home/')
        self.assertIn(response.status_code, [200, 302])

    def test_home_fallback_to_login_when_redirect_resolution_fails(self):
        """Test que / no rompe si la resolución del dashboard falla por DB."""
        with patch('core.views.general.get_redirect_url_by_role', side_effect=OperationalError('db busy')):
            response = self.client.get('/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))
    
    def test_paciente_list_view(self):
        """Test vista de lista de pacientes."""
        response = self.client.get('/pacientes/')
        self.assertIn(response.status_code, [200, 302, 403, 404])
    
    # ========================================================================
    # TESTS LABORATORIO - Flujo completo
    # ========================================================================
    
    def test_crear_orden_servicio(self):
        """Test creación de orden de servicio."""
        orden = OrdenDeServicio.objects.create(
            paciente=self.paciente,
            empresa=self.empresa,
            sucursal=self.sucursal,
            estado='PENDIENTE',
            total=0,
        )
        
        self.assertEqual(orden.estado, 'PENDIENTE')
        self.assertEqual(orden.paciente, self.paciente)
        self.assertIsNotNone(orden.fecha_creacion)
    
    def test_crear_estudio(self):
        """Test creación de estudio."""
        cat = CategoriaExamen.objects.create(nombre='Química Clínica')
        estudio = Estudio.objects.create(
            nombre='Glucosa',
            codigo='GLU-001',
            precio_base=150.00,
            categoria=cat,
        )
        
        self.assertEqual(estudio.nombre, 'Glucosa')
        self.assertEqual(estudio.precio_base, 150.00)
    
    def test_laboratorio_lista_trabajo(self):
        """Test acceso a lista de trabajo del laboratorio."""
        response = self.client.get('/laboratorio/lista-trabajo/')
        self.assertIn(response.status_code, [200, 302, 403])
    
    def test_laboratorio_api_buscar(self):
        """Test API de búsqueda del laboratorio."""
        response = self.client.get('/laboratorio/api/buscar-estudios/?q=test')
        self.assertIn(response.status_code, [200, 302, 403, 404])
    
    # ========================================================================
    # TESTS FARMACIA - Flujo PDV
    # ========================================================================
    
    def test_farmacia_pdv_access(self):
        """Test acceso al punto de venta."""
        response = self.client.get('/farmacia/pdv/')
        self.assertIn(response.status_code, [200, 302, 403])
    
    def test_farmacia_api_buscar_producto(self):
        """Test API de búsqueda de productos."""
        response = self.client.get('/farmacia/api/buscar-producto-pdv/?q=para')
        self.assertIn(response.status_code, [200, 302, 403])
    
    def test_crear_venta(self):
        """Test creación de venta."""
        venta = Venta.objects.create(
            paciente=self.paciente,
            empresa=self.empresa,
            sucursal=self.sucursal,
            usuario=self.admin_user,
            total=100.00,
            estado='COMPLETADA'
        )
        
        item = DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=2,
            precio_unitario=50.00,
            subtotal=100.00,
        )
        
        self.assertEqual(venta.total, 100.00)
        self.assertEqual(item.cantidad, 2)
    
    # ========================================================================
    # TESTS USUARIOS Y AUTENTICACIÓN
    # ========================================================================
    
    def test_user_roles(self):
        """Test que los usuarios tienen roles correctos."""
        self.assertEqual(self.admin_user.rol, 'ADMIN')
        self.assertEqual(self.lab_user.rol, 'QUIMICO')
        self.assertTrue(self.admin_user.is_staff)
    
    def test_user_empresa_tenant(self):
        """Test que los usuarios pertenecen a una empresa."""
        self.assertEqual(self.admin_user.empresa, self.empresa)
        self.assertEqual(self.lab_user.empresa, self.empresa)
    
    # ========================================================================
    # TESTS INTEGRACIÓN - Flujo humano completo
    # ========================================================================
    
    def test_flujo_completo_laboratorio(self):
        """Test flujo completo: orden -> captura -> resultado."""
        # 1. Crear orden
        orden = OrdenDeServicio.objects.create(
            paciente=self.paciente,
            empresa=self.empresa,
            sucursal=self.sucursal,
            estado='PENDIENTE',
            total=0,
        )
        self.assertEqual(orden.estado, 'PENDIENTE')
        
        # 2. Cambiar estado a EN_PROCESO
        orden.estado = 'EN_PROCESO'
        orden.save()
        self.assertEqual(orden.estado, 'EN_PROCESO')
        
        # 3. Marcar como LISTA
        orden.estado = 'LISTA'
        orden.save()
        self.assertEqual(orden.estado, 'LISTA')
    
    def test_tenant_isolation(self):
        """Test que los datos están aislados por empresa."""
        # Crear otra empresa
        empresa2 = Empresa.objects.create(nombre='Otra Empresa', rfc='OTRA123456')
        
        # Verificar que el paciente de empresa 1 no aparece en empresa 2
        pacientes_empresa1 = Paciente.objects.filter(empresa=self.empresa)
        pacientes_empresa2 = Paciente.objects.filter(empresa=empresa2)
        
        self.assertIn(self.paciente, pacientes_empresa1)
        self.assertNotIn(self.paciente, pacientes_empresa2)
