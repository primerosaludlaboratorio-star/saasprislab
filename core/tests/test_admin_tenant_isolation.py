from unittest.mock import MagicMock

from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase

from core.admin.ventas import VentaAdmin
from core.models import Venta


class AdminTenantIsolationTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.model_admin = VentaAdmin(Venta, admin.site)

    def test_non_superuser_queryset_is_scoped_to_company(self):
        request = self.factory.get('/admin/core/venta/')
        request.user = MagicMock(is_superuser=False, empresa_id=42)

        query = self.model_admin.get_queryset(request).query

        self.assertIn('empresa', str(query.where))
        self.assertIn('42', str(query.where))

    def test_user_without_company_sees_nothing(self):
        request = self.factory.get('/admin/core/venta/')
        request.user = MagicMock(is_superuser=False, empresa_id=None)

        self.assertTrue(self.model_admin.get_queryset(request).query.is_empty())

    def test_superuser_keeps_global_admin_scope(self):
        request = self.factory.get('/admin/core/venta/')
        request.user = MagicMock(is_superuser=True, empresa_id=None)

        self.assertFalse(self.model_admin.get_queryset(request).query.is_empty())
