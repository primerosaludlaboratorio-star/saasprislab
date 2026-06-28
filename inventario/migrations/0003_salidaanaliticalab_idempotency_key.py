# Fase 1 inventario federado v7.5 — idempotencia en salidas analíticas

from django.db import migrations, models


def _fill_idempotency_keys(apps, schema_editor):
    SalidaAnaliticaLab = apps.get_model('inventario', 'SalidaAnaliticaLab')
    for row in SalidaAnaliticaLab.objects.all().iterator():
        if row.idempotency_key:
            continue
        aid = row.analito_id or 0
        fid = row.formula_consumo_id or 0
        base = f'lab_legacy_o{row.orden_id}_a{aid}_f{fid}_l{row.lote_id}_p{row.pk}'
        row.idempotency_key = base[:190]
        row.save(update_fields=['idempotency_key'])


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0002_traspasoinventario_notificaciondiscrepancia_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='salidaanaliticalab',
            name='idempotency_key',
            field=models.CharField(
                blank=True,
                max_length=190,
                null=True,
                verbose_name='Clave de idempotencia',
                help_text='Determinista: lab_rp{resultado_id}_f{formula_id}_l{lote_id}.',
            ),
        ),
        migrations.RunPython(_fill_idempotency_keys, _noop),
        migrations.AlterField(
            model_name='salidaanaliticalab',
            name='idempotency_key',
            field=models.CharField(
                max_length=190,
                unique=True,
                verbose_name='Clave de idempotencia',
                help_text='Determinista: lab_rp{resultado_id}_f{formula_id}_l{lote_id}. Evita doble descuento bajo concurrencia.',
            ),
        ),
    ]
