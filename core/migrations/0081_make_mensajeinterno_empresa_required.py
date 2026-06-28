# Generated manually — makes MensajeInterno.empresa non-nullable after backfill

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0080_backfill_mensajeinterno_empresa'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mensajeinterno',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='mensajes_internos',
                to='core.empresa',
                verbose_name='Empresa',
            ),
        ),
    ]
