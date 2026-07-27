from django.db import migrations, models
import django.db.models.deletion


def backfill_empresa(apps, schema_editor):
    CotizacionOCR = apps.get_model('ia', 'CotizacionOCR')
    for cotizacion in CotizacionOCR.objects.filter(
        empresa__isnull=True,
        usuario_creador__empresa__isnull=False,
    ).select_related('usuario_creador'):
        cotizacion.empresa_id = cotizacion.usuario_creador.empresa_id
        cotizacion.save(update_fields=['empresa'])

    orphan_count = CotizacionOCR.objects.filter(empresa__isnull=True).count()
    if orphan_count:
        raise RuntimeError(
            f'No se puede cerrar el aislamiento de CotizacionOCR: {orphan_count} registros sin empresa.'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('ia', '0003_alter_cotizacionocr_orden_asociada_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cotizacionocr',
            name='empresa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='cotizaciones_ocr',
                to='core.empresa',
                help_text='Empresa propietaria de la cotización OCR.',
            ),
        ),
        migrations.RunPython(backfill_empresa, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cotizacionocr',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='cotizaciones_ocr',
                to='core.empresa',
                help_text='Empresa propietaria de la cotización OCR.',
            ),
        ),
    ]
