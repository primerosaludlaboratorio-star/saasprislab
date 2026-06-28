# Escudo clinico v1.14
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("lims", "0005_analito_codigo_rastreo_iso")]
    operations = [
        migrations.AddField(
            model_name="valorreferenciaanalito",
            name="es_critico_si_fuera_de_rango",
            field=models.BooleanField(
                default=False,
                help_text="Si esta activo, cualquier valor fuera de ref min/max se considera critico.",
                verbose_name="Panico si fuera de referencia",
            ),
        ),
        migrations.AddField(
            model_name="valorreferenciaanalito",
            name="mensaje_critico",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Texto para notificaciones.",
                max_length=300,
                verbose_name="Mensaje critico (push / notificacion)",
            ),
        ),
        migrations.AddField(
            model_name="valorreferenciaanalito",
            name="valor_critico_alto",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Valor estrictamente por encima de este limite = panico.",
                max_digits=14,
                null=True,
                verbose_name="Umbral critico alto",
            ),
        ),
        migrations.AddField(
            model_name="valorreferenciaanalito",
            name="valor_critico_bajo",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Valor estrictamente por debajo de este limite = panico.",
                max_digits=14,
                null=True,
                verbose_name="Umbral critico bajo",
            ),
        ),
    ]
