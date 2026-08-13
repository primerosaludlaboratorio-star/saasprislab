import json

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse

from bienestar.models import DiarioEmocional, RecursoCrecimiento
from core.models import Empresa
from django.contrib.auth import get_user_model


Usuario = get_user_model()


class BienestarPrivacyTests(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='Bienestar A', rfc='BIA010101AAA')
        self.empresa_b = Empresa.objects.create(nombre='Bienestar B', rfc='BIB010101BBB')
        self.user_a = Usuario.objects.create_user(
            username='bienestar_a', password='pass12345', empresa=self.empresa_a, rol='RECEPCION'
        )
        self.user_b = Usuario.objects.create_user(
            username='bienestar_b', password='pass12345', empresa=self.empresa_b, rol='RECEPCION'
        )
        self.client = Client()

    def test_diario_se_cifra_y_se_asigna_al_tenant_del_usuario(self):
        entrada = DiarioEmocional.objects.create(
            usuario=self.user_a,
            fecha='2026-08-12',
            contenido_privado='confidencial de prueba',
        )
        self.assertEqual(entrada.empresa_id, self.empresa_a.id)
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT contenido_privado FROM bienestar_diarioemocional WHERE id = %s',
                [entrada.id],
            )
            almacenado = cursor.fetchone()[0]
        self.assertNotIn('confidencial de prueba', almacenado)
        entrada.refresh_from_db()
        self.assertEqual(entrada.contenido_privado, 'confidencial de prueba')

    def test_diario_rechaza_empresa_de_otro_tenant(self):
        entrada = DiarioEmocional(
            usuario=self.user_a,
            empresa=self.empresa_b,
            fecha='2026-08-12',
            contenido_privado='no debe cruzar tenant',
        )
        with self.assertRaises(ValidationError):
            entrada.full_clean()

    def test_recursos_no_exponen_recursos_privados_de_otro_tenant(self):
        RecursoCrecimiento.objects.create(
            empresa=self.empresa_a,
            titulo='Recurso A', categoria='EMOCIONAL',
            url_contenido='https://example.com/a', activo=True,
        )
        recurso_b = RecursoCrecimiento.objects.create(
            empresa=self.empresa_b,
            titulo='Recurso B', categoria='EMOCIONAL',
            url_contenido='https://example.com/b', activo=True,
        )
        global_resource = RecursoCrecimiento.objects.create(
            titulo='Recurso global', categoria='SALUD',
            url_contenido='https://example.com/global', activo=True,
        )

        self.client.login(username='bienestar_a', password='pass12345')
        response = self.client.get(reverse('bienestar:recursos_bienestar'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recurso A')
        self.assertContains(response, 'Recurso global')
        self.assertNotContains(response, 'Recurso B')

        response = self.client.get(
            reverse('bienestar:detalle_recurso', args=[recurso_b.id])
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.client.get(
                reverse('bienestar:detalle_recurso', args=[global_resource.id])
            ).status_code,
            200,
        )
