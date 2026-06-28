# Generated migration: add empresa FK to FacturaCFDI for direct multi-tenant scoping

from django.db import migrations, models
import django.db.models.deletion


def backfill_empresa(apps, schema_editor):
    """Backfill FacturaCFDI.empresa from cliente.empresa for existing records."""
    FacturaCFDI = apps.get_model('contabilidad', 'FacturaCFDI')
    updated = 0
    for factura in FacturaCFDI.objects.filter(empresa__isnull=True).select_related('cliente__empresa'):
        if factura.cliente_id and factura.cliente.empresa_id:
            factura.empresa_id = factura.cliente.empresa_id
            factura.save(update_fields=['empresa'])
            updated += 1
    if updated:
        print(f'  Backfilled empresa on {updated} FacturaCFDI records from cliente.empresa.')


class Migration(migrations.Migration):

    dependencies = [
        ('contabilidad', '0007_facturacfdi_ultimo_error_pac'),
        ('core', '0001_initial'),  # core.Empresa
    ]

    operations = [
        migrations.AddField(
            model_name='facturacfdi',
            name='empresa',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='facturas_cfdi',
                to='core.empresa',
                help_text='Empresa emisora del CFDI (denormalizada de cliente.empresa para integridad y performance)',
            ),
        ),
        migrations.RunPython(backfill_empresa, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name='facturacfdi',
            index=models.Index(fields=['empresa', 'serie', 'folio'], name='contab_empresa_serie_folio_idx'),
        ),
    ]
