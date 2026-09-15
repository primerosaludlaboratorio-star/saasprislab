"""Database-level ACID checks used by the PostgreSQL staging gate."""

from uuid import uuid4

from django.db import transaction
from django.test import TransactionTestCase

from core.models import Empresa


class Phase3AtomicityTests(TransactionTestCase):
    reset_sequences = True

    def test_atomic_block_rolls_back_all_writes_after_failure(self):
        marker = f"phase3-acid-{uuid4()}"

        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                Empresa.objects.create(nombre=marker)
                raise RuntimeError("intentional phase 3 rollback")

        self.assertFalse(Empresa.objects.filter(nombre=marker).exists())
