from django.db import migrations, models


def backfill_pagoorden_empresa(apps, schema_editor):
    PagoOrden = apps.get_model('core', 'PagoOrden')
    for pago in PagoOrden.objects.filter(empresa__isnull=True).select_related('orden').iterator():
        orden = getattr(pago, 'orden', None)
        if orden and getattr(orden, 'empresa_id', None):
            PagoOrden.objects.filter(pk=pago.pk).update(empresa_id=orden.empresa_id)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0073_conveniopreciolims_and_legacy_lab_drop'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagoorden',
            name='empresa',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name='pagos_orden', to='core.empresa', verbose_name='Empresa'),
        ),
        migrations.RunPython(backfill_pagoorden_empresa, migrations.RunPython.noop),
    ]
