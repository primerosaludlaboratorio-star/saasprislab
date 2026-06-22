from django.test import RequestFactory, TestCase, override_settings

from core.views.autenticacion_2fa import _ip_exenta_2fa
from core.views.entrega_resultados import _resultados_publicos_max_age


class Hardening2FAResultadosTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, ip: str):
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = ip
        return request

    def test_2fa_no_bypassea_red_privada_sin_configuracion_explicita(self):
        request = self._request("192.168.1.23")
        with override_settings(IPS_INTERNAS_2FA_BYPASS=[]):
            self.assertFalse(_ip_exenta_2fa(request))

    def test_2fa_bypassea_solo_si_regla_explicita_lo_permite(self):
        request = self._request("192.168.1.23")
        with override_settings(IPS_INTERNAS_2FA_BYPASS=["192.168.1."]):
            self.assertTrue(_ip_exenta_2fa(request))

    def test_ttl_resultados_publicos_es_configurable(self):
        with override_settings(RESULTADOS_PUBLICOS_TOKEN_MAX_AGE_SECONDS=900):
            self.assertEqual(_resultados_publicos_max_age(), 900)
