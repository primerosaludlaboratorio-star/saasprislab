from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.models import Empresa, Paciente

from marketing.models import MarketingTrackingHit
from marketing.tracking_signing import sign_paciente_track
from marketing.views_tracking import CANONICAL_TRACKING_EVENTS_V120


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class MarketingTrack204Tests(TestCase):
    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(nombre="Emp Track Test")

    def _tenant_headers(self):
        return {"HTTP_X_EMPRESA_ID": str(self.empresa.id)}

    def test_204_invalid_event_no_row(self):
        url = reverse("marketing:marketing_track_pixel")
        r = self.client.get(url, {"ev": "BAD EVENT"})
        self.assertEqual(r.status_code, 204)
        self.assertEqual(MarketingTrackingHit.objects.count(), 0)

    def test_canonical_v120_events_anonymous(self):
        url = reverse("marketing:marketing_track_pixel")
        for ev in sorted(CANONICAL_TRACKING_EVENTS_V120):
            with self.subTest(ev=ev):
                r = self.client.get(url, {"ev": ev}, **self._tenant_headers())
                self.assertEqual(r.status_code, 204)
                self.assertEqual(
                    MarketingTrackingHit.objects.filter(event_key=ev).count(), 1
                )
        self.assertEqual(MarketingTrackingHit.objects.count(), 4)

    def test_204_anonymous_persists(self):
        url = reverse("marketing:marketing_track_pixel")
        r = self.client.get(url, {"ev": "email_resultado_abierto"}, **self._tenant_headers())
        self.assertEqual(r.status_code, 204)
        self.assertEqual(MarketingTrackingHit.objects.count(), 1)
        hit = MarketingTrackingHit.objects.get()
        self.assertEqual(hit.event_key, "email_resultado_abierto")
        self.assertIsNone(hit.paciente_id)

    def test_204_head_same_as_get(self):
        url = reverse("marketing:marketing_track_pixel")
        r = self.client.head(url, {"ev": "push_notif_tap"}, **self._tenant_headers())
        self.assertEqual(r.status_code, 204)

    def test_consent_paciente_denied_no_row(self):
        pac = Paciente.objects.create(
            empresa=self.empresa,
            nombres="Sin",
            apellido_paterno="Marketing",
            nombre_completo="Sin Marketing",
            consentimiento_marketing=False,
        )
        tok = sign_paciente_track(empresa_id=self.empresa.id, paciente_id=pac.id)
        url = reverse("marketing:marketing_track_pixel")
        r = self.client.get(url, {"ev": "wa_resultado_clic", "tok": tok}, **self._tenant_headers())
        self.assertEqual(r.status_code, 204)
        self.assertEqual(MarketingTrackingHit.objects.count(), 0)

    def test_consent_paciente_allowed_row(self):
        pac = Paciente.objects.create(
            empresa=self.empresa,
            nombres="Con",
            apellido_paterno="Marketing",
            nombre_completo="Con Marketing",
            consentimiento_marketing=True,
        )
        tok = sign_paciente_track(empresa_id=self.empresa.id, paciente_id=pac.id)
        url = reverse("marketing:marketing_track_pixel")
        r = self.client.get(url, {"ev": "wa_resultado_clic", "tok": tok}, **self._tenant_headers())
        self.assertEqual(r.status_code, 204)
        self.assertEqual(MarketingTrackingHit.objects.count(), 1)
        hit = MarketingTrackingHit.objects.get()
        self.assertEqual(hit.paciente_id, pac.id)
        self.assertEqual(hit.empresa_id, self.empresa.id)


from django.contrib.auth import get_user_model

Usuario = get_user_model()

class MarketingSecurityTests(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre="Empresa A", rfc="RFC111111AAA")
        
        self.user_con_empresa = Usuario.objects.create_user(
            username="marketing_user_con_emp",
            password="password123",
            empresa=self.empresa_a,
            rol="RECEPCION"
        )
        self.user_sin_empresa = Usuario.objects.create_user(
            username="marketing_user_sin_emp",
            password="password123",
            empresa=None,
            rol="RECEPCION"
        )
        self.client = Client()

    def test_api_generar_cupon_enforces_empresa(self):
        # User without company is blocked
        self.client.login(username="marketing_user_sin_emp", password="password123")
        response = self.client.post(reverse("marketing:api_generar_cupon"), {
            "porcentaje": "15",
            "descripcion": "Descuento especial"
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["ok"])

        # User with company can generate coupon
        self.client.login(username="marketing_user_con_emp", password="password123")
        response = self.client.post(reverse("marketing:api_generar_cupon"), {
            "porcentaje": "15",
            "descripcion": "Descuento especial"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_api_crear_campana_enforces_empresa(self):
        # User without company is blocked
        self.client.login(username="marketing_user_sin_emp", password="password123")
        response = self.client.post(reverse("marketing:api_crear_campana"), {
            "segmento": "diabeticos",
            "mensaje": "Mensaje de campaña"
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["ok"])

        # User with company can create campaign
        self.client.login(username="marketing_user_con_emp", password="password123")
        response = self.client.post(reverse("marketing:api_crear_campana"), {
            "segmento": "diabeticos",
            "mensaje": "Mensaje de campaña"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_entrenamiento_ia_enforces_empresa(self):
        # User without company is redirected to home
        self.client.login(username="marketing_user_sin_emp", password="password123")
        response = self.client.get(reverse("marketing:entrenamiento_ia"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"), target_status_code=302)

        # User with company can access
        self.client.login(username="marketing_user_con_emp", password="password123")
        response = self.client.get(reverse("marketing:entrenamiento_ia"))
        self.assertEqual(response.status_code, 200)
