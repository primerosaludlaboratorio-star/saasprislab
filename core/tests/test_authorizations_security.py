import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa, SolicitudAutorizacion


Usuario = get_user_model()


class AuthorizationTenantSecurityTests(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='Empresa Autorizaciones A')
        self.empresa_b = Empresa.objects.create(nombre='Empresa Autorizaciones B')
        self.solicitante = Usuario.objects.create_user(
            username='solicitante_auth', password='testpass123', empresa=self.empresa_a,
        )
        self.director_b = Usuario.objects.create_user(
            username='director_auth_b', password='testpass123', empresa=self.empresa_b,
            rol='DIRECTOR', is_superuser=True,
        )

    def test_crear_solicitud_asigna_empresa_del_solicitante(self):
        self.client.force_login(self.solicitante)
        response = self.client.post(
            reverse('crear_solicitud_autorizacion'),
            data=json.dumps({
                'tipo_accion': 'OTRO',
                'descripcion': 'Se requiere autorización operativa para esta empresa.',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        solicitud = SolicitudAutorizacion.objects.get(pk=response.json()['solicitud_id'])
        self.assertEqual(solicitud.empresa_id, self.empresa_a.id)

    def test_director_de_otro_tenant_no_puede_aprobar(self):
        solicitud = SolicitudAutorizacion.objects.create(
            empresa=self.empresa_a,
            usuario_solicita=self.solicitante,
            tipo_accion='OTRO',
            descripcion='Solicitud aislada por empresa para prueba.',
        )
        self.client.force_login(self.director_b)
        response = self.client.post(
            reverse('api_aprobar_solicitud', kwargs={'solicitud_id': solicitud.id}),
        )
        self.assertEqual(response.status_code, 404)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'PENDIENTE')
