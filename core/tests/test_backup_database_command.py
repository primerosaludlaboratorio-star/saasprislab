"""Comando backup_database — rechazo fuera de PostgreSQL."""
from io import StringIO

from cryptography.fernet import Fernet
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings


class BackupDatabaseCommandTests(TestCase):
    @override_settings(FERNET_KEY=Fernet.generate_key().decode())
    def test_sqlite_raises_command_error(self):
        with self.assertRaises(CommandError) as ctx:
            call_command('backup_database', stdout=StringIO(), stderr=StringIO())
        self.assertIn('PostgreSQL', str(ctx.exception))
