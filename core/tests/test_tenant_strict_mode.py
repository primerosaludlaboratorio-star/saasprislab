from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase, override_settings

from core.middleware import empresa as empresa_mw
from core.middleware.empresa import EmpresaIdentityMiddleware
from core.models import Empresa, Producto
from core.tenant import clear_current_empresa

User = get_user_model()


class TenantStrictModeTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.empresa = Empresa.objects.create(nombre="Tenant Uno", rfc="TEN123456ABC")
        self.user = User.objects.create_user(
            username="sin_empresa_strict",
            password="Test12345!",
            email="strict@test.local",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            nombre="Producto Tenant",
            codigo_barras="750000000099",
            forma_farmaceutica="Tabletas",
            concentracion="500mg",
            presentacion="10 tabletas",
            categoria="GENERICO",
            precio_publico=Decimal("10.00"),
            precio_compra=Decimal("5.00"),
            stock=5,
        )

    def tearDown(self):
        empresa_mw.set_current_request(None)
        clear_current_empresa()

    @override_settings(PRISLAB_TENANT_STRICT_MODE=True, PRISLAB_DEFAULT_EMPRESA_ID=None)
    def test_middleware_bloquea_usuario_autenticado_sin_empresa(self):
        request = self.factory.get("/panel/")
        request.user = SimpleNamespace(
            is_authenticated=True,
            empresa=None,
            is_superuser=False,
            username="sin_empresa_strict",
        )

        middleware = EmpresaIdentityMiddleware(lambda req: None)

        with patch("core.utils.default_empresa.resolve_default_empresa_sistema", return_value=None):
            with self.assertRaises(PermissionDenied):
                middleware(request)

    @override_settings(PRISLAB_TENANT_STRICT_MODE=True)
    def test_manager_bloquea_queryset_sin_contexto_tenant_en_request_autenticado(self):
        request = self.factory.get("/api/productos/")
        request.user = self.user
        empresa_mw.set_current_request(request)
        clear_current_empresa()

        with self.assertRaises(PermissionDenied):
            list(Producto.objects.all())
