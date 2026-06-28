# Data integrity: snapshot de costo al momento de la venta (CICLO 4)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_change_parametro_unique_to_abreviatura'),
    ]

    operations = [
        migrations.AddField(
            model_name='detalleventa',
            name='costo_unitario_momento',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                verbose_name='Costo unitario al momento de la venta',
            ),
        ),
    ]
