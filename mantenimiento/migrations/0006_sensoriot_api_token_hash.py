from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('mantenimiento', '0005_fix_ticket_nullable_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensoriot',
            name='api_token_hash',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Nunca se almacena el token físico en claro.',
                max_length=64,
                verbose_name='Hash del token API',
            ),
        ),
    ]
