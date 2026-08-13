from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0106_scope_solicitud_autorizacion_by_empresa'),
    ]

    operations = [
        migrations.AddField(
            model_name='consentimientoinformado',
            name='folio_consentimiento',
            field=models.CharField(
                blank=True,
                max_length=24,
                null=True,
                unique=True,
                verbose_name='Folio de consentimiento',
            ),
        ),
    ]
