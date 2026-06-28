"""
PRIS-Chat: Agregar campos de audio y tipo al modelo MensajeInterno.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_voiceauditlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='mensajeinterno',
            name='tipo',
            field=models.CharField(
                choices=[('texto', 'Texto'), ('audio', 'Nota de Voz')],
                default='texto',
                max_length=10,
                verbose_name='Tipo',
            ),
        ),
        migrations.AddField(
            model_name='mensajeinterno',
            name='audio',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='chat_audios/%Y/%m/',
                verbose_name='Nota de Voz',
            ),
        ),
        migrations.AlterField(
            model_name='mensajeinterno',
            name='mensaje',
            field=models.TextField(blank=True, default='', verbose_name='Mensaje'),
        ),
        migrations.AlterModelOptions(
            name='mensajeinterno',
            options={
                'ordering': ['fecha'],
                'verbose_name': 'Mensaje Interno',
                'verbose_name_plural': 'Mensajes Internos',
            },
        ),
    ]
