from unittest.mock import patch

from django.test import SimpleTestCase

from core.services import auto_repair


class AutoRepairRestartGuardTests(SimpleTestCase):
    def setUp(self):
        auto_repair._critical_errors.clear()
        auto_repair._last_restart_time = None

    def test_request_path_never_restarts_gunicorn_at_threshold(self):
        with patch.object(auto_repair, "_ejecutar_soft_restart") as restart:
            for _ in range(3):
                result = auto_repair.registrar_error_critico(
                    "TimeoutError",
                    "upstream timeout",
                )

        self.assertFalse(result)
        restart.assert_not_called()

    def test_restart_requires_explicit_infrastructure_authorization(self):
        with patch.object(auto_repair, "_ejecutar_soft_restart", return_value=True) as restart:
            for _ in range(3):
                result = auto_repair.registrar_error_critico(
                    "TimeoutError",
                    "upstream timeout",
                    permitir_restart=True,
                )

        self.assertTrue(result)
        restart.assert_called_once_with()

