from types import SimpleNamespace

from django.test import SimpleTestCase

from core.views.autofactura import hmac_compare_token, public_autofactura_token


class AutofacturaTokenTests(SimpleTestCase):
    def test_token_is_stable_but_bound_to_tenant_and_folio(self):
        venta = SimpleNamespace(empresa_id=7, folio_operacion='VTA-ABC')
        same = SimpleNamespace(empresa_id=7, folio_operacion='VTA-ABC')
        other_tenant = SimpleNamespace(empresa_id=8, folio_operacion='VTA-ABC')

        token = public_autofactura_token(venta)

        self.assertTrue(hmac_compare_token(same, token))
        self.assertFalse(hmac_compare_token(other_tenant, token))
        self.assertFalse(hmac_compare_token(venta, token[:-1] + '0'))

