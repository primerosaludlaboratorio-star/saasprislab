# ACAYUCAN TOTAL v7.5 — GastoCaja: comprobante obligatorio > Zona Verde (Bankguard)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0056_bankguard_v114_niveles_2_3'),
    ]

    operations = [
        migrations.AddField(
            model_name='gastocaja',
            name='documento_adjunto',
            field=models.FileField(
                blank=True,
                help_text='Obligatorio si el monto supera el límite Zona Verde (Política de Límites de la empresa).',
                null=True,
                upload_to='gastos_caja/%Y/%m/',
                verbose_name='Comprobante / documento',
            ),
        ),
    ]
