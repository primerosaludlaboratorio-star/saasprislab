# Punto 18 — Ética IA: trazabilidad de aprobación humana + método IA_BORRADOR

from django.db import migrations, models


def forwards_aprobado(apps, schema_editor):
    RP = apps.get_model('core', 'ResultadoParametro')
    RP.objects.filter(validado=True).update(aprobado_por_humano=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0066_offline_client_mutation_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='resultadoparametro',
            name='aprobado_por_humano',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'True cuando un profesional autorizado validó el resultado en captura '
                    '(acción «validar»). La IA nunca puede fijar este campo en True.'
                ),
                verbose_name='Aprobación humana formal',
            ),
        ),
        migrations.AlterField(
            model_name='resultadoparametro',
            name='metodo_captura',
            field=models.CharField(
                choices=[
                    ('MANUAL', 'Captura Manual'),
                    ('VOZ', 'Dictado por Voz'),
                    ('OCR', 'Escaneado OCR'),
                    ('INTERFAZ', 'Interfaz Automática'),
                    ('IA_BORRADOR', 'Sugerencia IA (pendiente aprobación clínica)'),
                ],
                default='MANUAL',
                max_length=20,
                verbose_name='Método de Captura',
            ),
        ),
        migrations.RunPython(forwards_aprobado, noop_reverse),
    ]
