from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase

from core.api_contracts.ninja_api import _requiere_lims_captura
from core.decorators import role_required


class StaffNoRbacBypassTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            is_staff=True,
            rol="RECEPCION",
            username="staff-recepcion",
        )

    def test_role_required_rejects_staff_without_allowed_role(self):
        @role_required("QUIMICO")
        def protected_view(request):
            return "allowed"

        request = self.factory.get("/laboratorio/captura/")
        request.user = self.user

        response = protected_view(request)

        self.assertEqual(response.status_code, 403)

    def test_lims_api_rejects_staff_without_allowed_role(self):
        self.assertFalse(_requiere_lims_captura(self.user))
