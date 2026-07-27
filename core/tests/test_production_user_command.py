import os
from unittest.mock import patch

from django.core.management import CommandError
from django.test import SimpleTestCase, override_settings

from core.management.commands.crear_usuarios_produccion import Command


class ProductionUserCommandSecurityTests(SimpleTestCase):
    @override_settings(IS_PRODUCTION=True)
    def test_password_is_required_in_production(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(Command.password_env, None)
            with self.assertRaises(CommandError):
                Command()._password()

    def test_password_is_not_printed_or_accepted_when_too_short(self):
        with patch.dict(os.environ, {Command.password_env: 'short'}, clear=False):
            with self.assertRaises(CommandError):
                Command()._password()
