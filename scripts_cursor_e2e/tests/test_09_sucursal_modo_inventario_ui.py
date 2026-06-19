"""v1.49 — UI staff: página modo inventario lab por sucursal (director)."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase

from core.models import Empresa, Sucursal

User = get_user_model()


class SucursalModoInventarioUiTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Emp Modo Inv UI', rfc='MUI123456AAA')
        self.user = User.objects.create_user(
            username='dir_modo_inv',
            password='secret-77',
            empresa=self.empresa,
            rol='DIRECTOR',
            is_staff=True,
        )
        Sucursal.objects.create(
            empresa=self.empresa,
            nombre='Central',
            codigo_sucursal='SUC-MUI-01',
            gestion_inventario_activa=True,
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_pagina_modo_inventario_responde_200(self):
        r = self.client.get('/director/sucursales/modo-inventario-lab/', follow=True)
        self.assertEqual(r.status_code, 200)
        body = r.content.decode('utf-8', errors='replace')
        self.assertIn('Gestión de inventario', body)
        self.assertIn('gestion_', body)

    def test_post_actualiza_flag(self):
        s = Sucursal.objects.get(codigo_sucursal='SUC-MUI-01')
        self.assertTrue(s.gestion_inventario_activa)
        r = self.client.post(
            '/director/sucursales/modo-inventario-lab/',
            data={},
        )
        self.assertIn(r.status_code, [200, 302])
        s.refresh_from_db()
        self.assertFalse(s.gestion_inventario_activa)
