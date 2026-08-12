from django.db import migrations, models
import django.db.models.deletion


def reject_legacy_global_anchors(apps, schema_editor):
    HashRaizDiario = apps.get_model('core', 'HashRaizDiario')
    if HashRaizDiario.objects.exists():
        raise RuntimeError(
            'No se pueden migrar HashRaizDiario globales automáticamente: '
            'requieren revisión forense y asignación explícita por empresa.'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0103_alter_medico_lab_validation_pin_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='hashraizdiario',
            name='empresa',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='hashes_raiz_diarios',
                to='core.empresa',
                verbose_name='Empresa',
            ),
        ),
        migrations.RunPython(reject_legacy_global_anchors, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='hashraizdiario',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='hashes_raiz_diarios',
                to='core.empresa',
                verbose_name='Empresa',
            ),
        ),
        migrations.AlterField(
            model_name='hashraizdiario',
            name='fecha',
            field=models.DateField(verbose_name='Fecha'),
        ),
        migrations.AddConstraint(
            model_name='hashraizdiario',
            constraint=models.UniqueConstraint(
                fields=('empresa', 'fecha'),
                name='uq_hash_raiz_diario_empresa_fecha',
            ),
        ),
        migrations.AddIndex(
            model_name='hashraizdiario',
            index=models.Index(
                fields=('empresa', 'fecha', 'hash_raiz'),
                name='core_hash_empresa_fecha_idx',
            ),
        ),
    ]
