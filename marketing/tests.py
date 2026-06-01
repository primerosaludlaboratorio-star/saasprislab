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
