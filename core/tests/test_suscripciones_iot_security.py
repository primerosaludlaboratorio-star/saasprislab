from django.test import TestCase
from django.urls import reverse

from core.models import Empresa, Usuario
from iot.models import Kiosco
from suscripciones.models import PlanSaaS, SuscripcionTenant
from django.utils import timezone
from datetime import timedelta


class SuscripcionesTenantSecurityTests(TestCase):
    def test_staff_only_sees_own_subscription(self):
        empresa_a = Empresa.objects.create(nombre='Empresa A')
        empresa_b = Empresa.objects.create(nombre='Empresa B')
        plan = PlanSaaS.objects.create(nombre='QA', precio_mensual=1)
        for empresa in (empresa_a, empresa_b):
            SuscripcionTenant.objects.create(
                empresa=empresa, plan=plan,
                fecha_proximo_corte=timezone.now() + timedelta(days=30),
            )
        user = Usuario.objects.create_user(username='staff-a', password='x', empresa=empresa_a)
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        self.client.force_login(user)
        response = self.client.get(reverse('suscripciones_lista'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['suscripciones']), list(
            SuscripcionTenant.objects.filter(empresa=empresa_a)
        ))


class KioscoTokenSecurityTests(TestCase):
    def test_kiosco_tokens_are_unique_and_not_interchangeable(self):
        first = Kiosco.objects.create(nombre='Kiosco A')
        second = Kiosco.objects.create(nombre='Kiosco B')
        first_token = first.provisionar_token()
        second_token = second.provisionar_token()
        self.assertNotEqual(first_token, second_token)
        self.assertTrue(first.verificar_token(first_token))
        self.assertFalse(first.verificar_token(second_token))
