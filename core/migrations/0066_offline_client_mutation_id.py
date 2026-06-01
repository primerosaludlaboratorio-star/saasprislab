# Aislada: idempotencia offline (Punto 11) — solo client_mutation_id + constraints.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0065_forense_acceso_cofepris'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordendeservicio',
            name='client_mutation_id',
            field=models.UUIDField(
                blank=True,
                db_index=True,
                editable=False,
                help_text='UUID enviado por el cliente para deduplicar creación al sincronizar sin red.',
                null=True,
                verbose_name='Idempotencia cliente (offline)',
            ),
        ),
        migrations.AddField(
            model_name='pagoorden',
            name='client_mutation_id',
            field=models.UUIDField(
                blank=True,
                db_index=True,
                editable=False,
                help_text='UUID enviado por el cliente para deduplicar el cobro al sincronizar sin red.',
                null=True,
                verbose_name='Idempotencia cliente (offline)',
            ),
        ),
        migrations.AddConstraint(
            model_name='ordendeservicio',
            constraint=models.UniqueConstraint(
                condition=models.Q(client_mutation_id__isnull=False),
                fields=('empresa', 'client_mutation_id'),
                name='unique_orden_client_mutation_per_empresa',
            ),
        ),
        migrations.AddConstraint(
            model_name='pagoorden',
            constraint=models.UniqueConstraint(
                condition=models.Q(client_mutation_id__isnull=False),
                fields=('orden', 'client_mutation_id'),
                name='unique_pago_orden_client_mutation',
            ),
        ),
    ]
