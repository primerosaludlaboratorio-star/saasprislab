from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_remove_paciente_core_pacien_nombre__3dc2ec_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='estudio',
            name='venta_individual',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'Si está activo, aparece en la lista de precios, cotizador y búsqueda de órdenes. '
                    'Desactívalo para estudios que solo son parámetros dentro de otro estudio '
                    '(p.ej. Hemoglobina dentro de Biometría Hemática).'
                ),
                verbose_name='Se puede vender individualmente',
            ),
        ),
    ]
