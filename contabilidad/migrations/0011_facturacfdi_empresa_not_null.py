# Generated migration: make FacturaCFDI.empresa NOT NULL after backfill

from django.db import migrations, models
import django.db.models.deletion


def backfill_factura_empresa(apps, schema_editor):
    """Backfill any remaining FacturaCFDI.empresa from cliente.empresa."""
    FacturaCFDI = apps.get_model('contabilidad', 'FacturaCFDI')
    updated = 0
    for factura in FacturaCFDI.objects.filter(empresa__isnull=True).select_related('cliente__empresa'):
        if factura.cliente_id and factura.cliente.empresa_id:
            factura.empresa_id = factura.cliente.empresa_id
            factura.save(update_fields=['empresa'])
            updated += 1
    if updated:
        print(f'  Backfilled empresa on {updated} FacturaCFDI records before NOT NULL.')


class Migration(migrations.Migration):

    dependencies = [
        ('contabilidad', '0010_rename_contab_empresa_serie_folio_idx_contabilida_empresa_e9f2ce_idx'),
    ]

    operations = [
        migrations.RunPython(backfill_factura_empresa, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='facturacfdi',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='facturas_cfdi',
                to='core.empresa',
                help_text='Empresa emisora del CFDI (denormalizada de cliente.empresa para integridad y performance)',
            ),
        ),
    ]
