"""
Migration to add stock_minimo field to Producto model.
Auto-generated equivalent.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_paciente_nombres_apellidos'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='stock_minimo',
            field=models.IntegerField(
                default=5,
                help_text='Se genera alerta cuando el stock baje de este nivel',
                verbose_name='Stock Mínimo (Alerta)',
            ),
        ),
    ]
