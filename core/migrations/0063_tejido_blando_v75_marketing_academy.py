import uuid

from django.db import migrations, models


def _assign_unique_tokens(apps, schema_editor):
    """Evita duplicados: AddField+unique+default en un solo paso puede repetir UUID en Postgres."""
    DocumentoCapacitacion = apps.get_model('core', 'DocumentoCapacitacion')
    for doc in DocumentoCapacitacion.objects.all().only('pk'):
        DocumentoCapacitacion.objects.filter(pk=doc.pk).update(token_acceso=uuid.uuid4())


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0062_notaclinicasoap_signos_vitales_snapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='paciente',
            name='consentimiento_marketing',
            field=models.BooleanField(default=False, verbose_name='Consentimiento de Marketing'),
        ),
        migrations.AddField(
            model_name='documentocapacitacion',
            name='token_acceso',
            field=models.UUIDField(
                editable=False,
                null=True,
                unique=False,
                verbose_name='Token de Acceso',
            ),
        ),
        migrations.RunPython(_assign_unique_tokens, _noop_reverse),
        migrations.AlterField(
            model_name='documentocapacitacion',
            name='token_acceso',
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name='Token de Acceso',
            ),
        ),
    ]
