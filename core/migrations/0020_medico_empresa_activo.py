"""
Migration to add empresa (FK) and activo fields to Medico model.
Fixes FieldError when filtering Medico by empresa/activo in views.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_producto_stock_minimo'),
    ]

    operations = [
        migrations.AddField(
            model_name='medico',
            name='empresa',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='medicos',
                to='core.empresa',
                verbose_name='Empresa',
            ),
        ),
        migrations.AddField(
            model_name='medico',
            name='activo',
            field=models.BooleanField(default=True, verbose_name='Activo'),
        ),
        migrations.AlterModelOptions(
            name='medico',
            options={
                'ordering': ['nombre_completo'],
                'verbose_name': 'Médico',
                'verbose_name_plural': 'Médicos',
            },
        ),
    ]
