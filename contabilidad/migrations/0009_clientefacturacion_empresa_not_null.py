from django.db import migrations, models
import django.db.models.deletion


def backfill_cliente_empresa(apps, schema_editor):
    """
    Backfill de ClienteFacturacion.empresa antes de volverla obligatoria.

    Prioridad:
    1. paciente.empresa
    2. empresa de alguna FacturaCFDI relacionada ya backfilleada en 0008
    Si aún quedan registros huérfanos, se aborta la migración para limpieza manual.
    """
    ClienteFacturacion = apps.get_model('contabilidad', 'ClienteFacturacion')
    FacturaCFDI = apps.get_model('contabilidad', 'FacturaCFDI')

    for cliente in ClienteFacturacion.objects.filter(empresa__isnull=True):
        empresa_id = None

        if getattr(cliente, 'paciente_id', None):
            paciente = getattr(cliente, 'paciente', None)
            empresa_id = getattr(paciente, 'empresa_id', None)

        if not empresa_id:
            factura = (
                FacturaCFDI.objects
                .filter(cliente_id=cliente.id, empresa__isnull=False)
                .order_by('id')
                .first()
            )
            empresa_id = getattr(factura, 'empresa_id', None)

        if empresa_id:
            cliente.empresa_id = empresa_id
            cliente.save(update_fields=['empresa'])

    remaining = ClienteFacturacion.objects.filter(empresa__isnull=True).count()
    if remaining:
        raise RuntimeError(
            f'No se pudo backfillear empresa en {remaining} ClienteFacturacion huérfanos. '
            'Limpia esos registros antes de aplicar NOT NULL.'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('contabilidad', '0008_facturacfdi_empresa_fk'),
    ]

    operations = [
        migrations.RunPython(backfill_cliente_empresa, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='clientefacturacion',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='clientes_facturacion',
                to='core.empresa',
            ),
        ),
    ]
