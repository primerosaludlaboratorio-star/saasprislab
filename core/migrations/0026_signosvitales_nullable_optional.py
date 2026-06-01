# Consultorio CICLO 1: Triage puede guardar signos parciales (campos opcionales)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_alter_venta_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='signosvitales',
            name='presion_arterial_sistolica',
            field=models.IntegerField(blank=True, null=True, verbose_name='PA Sistólica (mmHg)'),
        ),
        migrations.AlterField(
            model_name='signosvitales',
            name='presion_arterial_diastolica',
            field=models.IntegerField(blank=True, null=True, verbose_name='PA Diastólica (mmHg)'),
        ),
        migrations.AlterField(
            model_name='signosvitales',
            name='frecuencia_cardiaca',
            field=models.IntegerField(blank=True, null=True, verbose_name='Frecuencia Cardíaca (lat/min)'),
        ),
        migrations.AlterField(
            model_name='signosvitales',
            name='frecuencia_respiratoria',
            field=models.IntegerField(blank=True, null=True, verbose_name='Frecuencia Respiratoria (resp/min)'),
        ),
        migrations.AlterField(
            model_name='signosvitales',
            name='temperatura',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='Temperatura (°C)'),
        ),
        migrations.AlterField(
            model_name='signosvitales',
            name='peso',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Peso (kg)'),
        ),
        migrations.AlterField(
            model_name='signosvitales',
            name='talla',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='Talla (m)'),
        ),
    ]
