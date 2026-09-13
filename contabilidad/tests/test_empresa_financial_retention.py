from django.db.models.deletion import ProtectedError, PROTECT
from django.test import SimpleTestCase, TestCase

from contabilidad.models import (
    ClienteFacturacion,
    Compra,
    CuentaContable,
    FacturaCFDI,
    Nomina,
    Poliza,
)
from core.models import Empresa


class EmpresaFinancialRetentionModelTests(SimpleTestCase):
    def test_financial_records_protect_empresa_deletion(self):
        models = (
            ClienteFacturacion,
            FacturaCFDI,
            CuentaContable,
            Poliza,
            Compra,
            Nomina,
        )
        for model in models:
            field = model._meta.get_field('empresa')
            self.assertIs(
                field.remote_field.on_delete,
                PROTECT,
                f'{model.__name__}.empresa debe conservar evidencia fiscal',
            )


class EmpresaFinancialRetentionDatabaseTests(TestCase):
    def test_empresa_with_compra_cannot_be_deleted(self):
        empresa = Empresa.objects.create(
            nombre='Empresa Retencion Fiscal',
            rfc='RET260913AAA',
        )
        Compra.objects.create(
            empresa=empresa,
            proveedor='Proveedor de prueba',
            total='100.00',
        )

        with self.assertRaises(ProtectedError):
            empresa.delete()
