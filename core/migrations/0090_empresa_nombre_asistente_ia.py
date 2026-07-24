from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0089_dispensacion_receta_parcial"),
    ]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="nombre_asistente_ia",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Nombre de marca que verá el personal. Vacío usa PRIS; para una empresa "
                    "cuyo nombre contiene Valle se usa LIA como valor inicial compatible."
                ),
                max_length=80,
                verbose_name="Nombre visible del asistente IA",
            ),
        ),
    ]
