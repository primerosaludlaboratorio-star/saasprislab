from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('farmacia', '0008_lecturarecetafarmacia_imagen_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='cierreturnofarmacia',
            name='cerrado_por',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuario que ejecutó el cierre. Puede ser distinto al responsable de apertura.',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='cierres_farmacia_realizados',
                to='core.usuario',
                verbose_name='Cerrado por',
            ),
        ),
        migrations.AddIndex(
            model_name='cierreturnofarmacia',
            index=models.Index(fields=['cerrado_por', '-fecha_cierre'], name='farmacia_ci_cerrado_d08f5c_idx'),
        ),
    ]
