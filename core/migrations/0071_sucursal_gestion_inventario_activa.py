from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0070_repair_client_mutation_columns'),
    ]

    operations = [
        migrations.AddField(
            model_name='sucursal',
            name='gestion_inventario_activa',
            field=models.BooleanField(
                default=True,
                help_text='Si está desactivado (modo ágil / pruebas), no se descuentan reactivos por FEFO al validar resultados de laboratorio para órdenes de esta sucursal. Si está activado, aplican las reglas estrictas de consumo y lotes.',
                verbose_name='Gestión de inventario (laboratorio)',
            ),
        ),
    ]
