from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0063_tejido_blando_v75_marketing_academy'),
    ]

    operations = [
        migrations.AddField(
            model_name='consentimientoinformado',
            name='consentimiento_marketing',
            field=models.BooleanField(default=False, verbose_name='Acepta Comunicaciones de Marketing'),
        ),
        migrations.AlterField(
            model_name='consentimientoinformado',
            name='firma_digital',
            field=models.TextField(blank=True, help_text='Firma del paciente en formato base64', verbose_name='Firma Digital (base64)'),
        ),
        migrations.AlterField(
            model_name='consentimientoinformado',
            name='orden',
            field=models.OneToOneField(blank=True, help_text='Opcional: orden asociada al consentimiento', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='consentimiento', to='core.ordendeservicio'),
        ),
    ]
