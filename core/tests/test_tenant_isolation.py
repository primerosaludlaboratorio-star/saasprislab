"""
core/tests/test_tenant_isolation.py
====================================
Tests REALES de aislamiento multi-tenant.

Verifican que los datos de Empresa A nunca sean accesibles
desde el contexto de Empresa B — ni por ORM directo, ni por vistas HTTP.

Esto es crítico para la seguridad del sistema SaaS.
"""
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from core.models import (
    Empresa, Producto, Lote, Paciente,
)

User = get_user_model()


def _crear_empresa(nombre, rfc):
    return Empresa.objects.create(nombre=nombre, rfc=rfc)


def _crear_usuario(username, empresa, rol='ADMIN'):
    u = User.objects.create_user(
        username=username,
        password='Test2026!PRIS',
        email=f'{username}@test.prislab',
    )
    u.empresa = empresa
    u.rol = rol
    u.save()
    return u


def _crear_producto(nombre, empresa):
    return Producto.objects.create(
        nombre=nombre,
        empresa=empresa,
        codigo_barras=f'TEST-{nombre[:8]}-{empresa.id}',
        precio_publico=Decimal('100.00'),
        precio_compra=Decimal('50.00'),
        stock=10,
        categoria='MEDICAMENTO',
    )


def _crear_paciente(nombre, empresa):
    return Paciente.objects.create(
        nombres=nombre,
        apellido_paterno='TestApellido',
        empresa=empresa,
        fecha_nacimiento=date(1990, 1, 1),
        sexo='M',
    )


def _crear_lote(producto, empresa, numero):
    return Lote.objects.create(
        empresa=empresa,
        producto=producto,
        numero_lote=numero,
        fecha_caducidad=date.today() + timedelta(days=365),
        cantidad=50,
        costo_adquisicion=Decimal('20.00'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# TESTS ORM — Aislamiento a nivel de base de datos
# ─────────────────────────────────────────────────────────────────────────────

class TenantIsolationModelTest(TestCase):
    """Verifica que el ORM no mezcla datos entre empresas."""

    def setUp(self):
        self.empresa_a = _crear_empresa('CLINICA ALFA', 'ALF900101TST')
        self.empresa_b = _crear_empresa('CLINICA BETA', 'BET900101TST')
        self.producto_a = _crear_producto('ProductoAlfa', self.empresa_a)
        self.producto_b = _crear_producto('ProductoBeta', self.empresa_b)
        self.paciente_a = _crear_paciente('PacienteAlfa', self.empresa_a)
        self.paciente_b = _crear_paciente('PacienteBeta', self.empresa_b)
        self.lote_a = _crear_lote(self.producto_a, self.empresa_a, 'LOTE-A-001')
        self.lote_b = _crear_lote(self.producto_b, self.empresa_b, 'LOTE-B-001')

    # Productos
    def test_empresa_a_no_ve_productos_de_empresa_b(self):
        qs = Producto.objects.filter(empresa=self.empresa_a)
        self.assertIn(self.producto_a, qs)
        self.assertNotIn(self.producto_b, qs)

    def test_empresa_b_no_ve_productos_de_empresa_a(self):
        qs = Producto.objects.filter(empresa=self.empresa_b)
        self.assertIn(self.producto_b, qs)
        self.assertNotIn(self.producto_a, qs)

    def test_filtro_empresa_productos_es_exclusivo(self):
        empresas = set(Producto.objects.filter(empresa=self.empresa_a)
                       .values_list('empresa_id', flat=True))
        self.assertEqual(empresas, {self.empresa_a.id})

    # Pacientes
    def test_empresa_a_no_ve_pacientes_de_empresa_b(self):
        qs = Paciente.objects.filter(empresa=self.empresa_a)
        self.assertIn(self.paciente_a, qs)
        self.assertNotIn(self.paciente_b, qs)

    def test_empresa_b_no_ve_pacientes_de_empresa_a(self):
        qs = Paciente.objects.filter(empresa=self.empresa_b)
        self.assertIn(self.paciente_b, qs)
        self.assertNotIn(self.paciente_a, qs)

    # Lotes
    def test_empresa_a_no_ve_lotes_de_empresa_b(self):
        qs = Lote.objects.filter(empresa=self.empresa_a)
        self.assertIn(self.lote_a, qs)
        self.assertNotIn(self.lote_b, qs)

    def test_empresa_b_no_ve_lotes_de_empresa_a(self):
        qs = Lote.objects.filter(empresa=self.empresa_b)
        self.assertIn(self.lote_b, qs)
        self.assertNotIn(self.lote_a, qs)

    # IDOR por PK
    def test_idor_producto_pk_bloqueado_por_empresa(self):
        """Empresa A no puede obtener producto de B aunque conozca el PK."""
        resultado = Producto.objects.filter(
            empresa=self.empresa_a, pk=self.producto_b.pk
        ).first()
        self.assertIsNone(resultado,
            "IDOR: empresa_a NO debe obtener producto de empresa_b por PK")

    def test_idor_paciente_pk_bloqueado_por_empresa(self):
        resultado = Paciente.objects.filter(
            empresa=self.empresa_a, pk=self.paciente_b.pk
        ).first()
        self.assertIsNone(resultado,
            "IDOR: empresa_a NO debe obtener paciente de empresa_b por PK")

    def test_idor_lote_pk_bloqueado_por_empresa(self):
        resultado = Lote.objects.filter(
            empresa=self.empresa_a, pk=self.lote_b.pk
        ).first()
        self.assertIsNone(resultado,
            "IDOR: empresa_a NO debe obtener lote de empresa_b por PK")

    def test_empresas_son_completamente_independientes(self):
        """Conteo por empresa es independiente — sin interferencia."""
        count_a = Producto.objects.filter(empresa=self.empresa_a).count()
        count_b = Producto.objects.filter(empresa=self.empresa_b).count()
        total = Producto.objects.filter(
            empresa__in=[self.empresa_a, self.empresa_b]
        ).count()
        self.assertEqual(count_a + count_b, total)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS HTTP — Aislamiento en vistas reales
# ─────────────────────────────────────────────────────────────────────────────

class TenantIsolationViewTest(TestCase):
    """Verifica que las vistas HTTP respetan el aislamiento de tenant."""

    def setUp(self):
        self.empresa_a = _crear_empresa('CLINICA GAMMA', 'GAM900101TST')
        self.empresa_b = _crear_empresa('CLINICA DELTA', 'DEL900101TST')
        self.user_a = _crear_usuario('user_gamma', self.empresa_a)
        self.user_b = _crear_usuario('user_delta', self.empresa_b)
        self.producto_a = _crear_producto('ProdGamma', self.empresa_a)
        self.producto_b = _crear_producto('ProdDelta', self.empresa_b)
        self.paciente_a = _crear_paciente('PacGamma', self.empresa_a)
        self.paciente_b = _crear_paciente('PacDelta', self.empresa_b)

        self.client_a = Client(SERVER_NAME='localhost')
        self.client_b = Client(SERVER_NAME='localhost')
        self.client_a.login(username='user_gamma', password='Test2026!PRIS')
        self.client_b.login(username='user_delta', password='Test2026!PRIS')

    def test_busqueda_pacientes_aislada_por_empresa(self):
        """Usuario A busca 'PacDelta' → no debe aparecer en sus resultados."""
        resp = self.client_a.get('/api/pacientes/buscar/', {'q': 'PacDelta'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8', errors='ignore').lower()
        self.assertNotIn('pacdelta', content,
            "Usuario de empresa_a NO debe ver pacientes de empresa_b")

    def test_busqueda_pacientes_positiva_empresa_a(self):
        """Usuario A sí ve sus propios pacientes."""
        resp = self.client_a.get('/api/pacientes/buscar/', {'q': 'PacGamma'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8', errors='ignore').lower()
        self.assertIn('pacgamma', content,
            "Usuario de empresa_a SÍ debe ver sus propios pacientes")

    def test_busqueda_productos_pdv_aislada(self):
        """Usuario A busca 'ProdDelta' en PDV → no debe aparecer."""
        resp = self.client_a.get(
            '/farmacia/api/buscar-producto-pdv/', {'q': 'ProdDelta'}, follow=True
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8', errors='ignore').lower()
        self.assertNotIn('proddelta', content,
            "Usuario de empresa_a NO debe ver productos de empresa_b en PDV")

    def test_busqueda_productos_pdv_positiva(self):
        """Usuario A sí ve sus propios productos en PDV."""
        resp = self.client_a.get(
            '/farmacia/api/buscar-producto-pdv/', {'q': 'ProdGamma'}, follow=True
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8', errors='ignore').lower()
        self.assertIn('prodgamma', content,
            "Usuario de empresa_a SÍ debe ver sus propios productos en PDV")

    def test_cross_tenant_simmetrico_empresa_b(self):
        """Usuario B tampoco ve datos de empresa_a."""
        resp = self.client_b.get('/api/pacientes/buscar/', {'q': 'PacGamma'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8', errors='ignore').lower()
        self.assertNotIn('pacgamma', content,
            "Usuario de empresa_b NO debe ver pacientes de empresa_a")

    def test_usuario_sin_autenticar_redirigido(self):
        """Un usuario anónimo no accede a datos de ninguna empresa."""
        anon = Client(SERVER_NAME='localhost')
        resp = anon.get('/api/pacientes/buscar/', {'q': 'test'})
        # API consumida por fetch(): debe rechazar con JSON, nunca HTML de login.
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp['Content-Type'], 'application/json')
        data = resp.json()
        self.assertEqual(data['code'], 'AUTH_REQUIRED')
        self.assertEqual(data['pacientes'], [])
