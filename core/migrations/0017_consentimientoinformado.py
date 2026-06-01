import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_convenio_cuentaporcobrar_notacredito'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsentimientoInformado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('firma_digital', models.TextField(verbose_name='Firma Digital (base64)')),
                ('acepta_privacidad', models.BooleanField(default=False)),
                ('acepta_procesamiento', models.BooleanField(default=False)),
                ('hash_firma', models.CharField(blank=True, max_length=64)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=500)),
                ('fecha_firma', models.DateTimeField(auto_now_add=True)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consentimientos', to='core.empresa')),
                ('paciente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consentimientos', to='core.paciente')),
                ('orden', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='consentimiento', to='core.ordendeservicio')),
            ],
            options={
                'verbose_name': 'Consentimiento Informado',
                'verbose_name_plural': 'Consentimientos Informados',
                'ordering': ['-fecha_firma'],
            },
        ),
        migrations.CreateModel(
            name='RegistroAuditoriaConsentimiento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accion', models.CharField(choices=[('CREADO', 'Creado'), ('MODIFICADO', 'Modificado'), ('REVOCADO', 'Revocado')], max_length=20)),
                ('descripcion', models.TextField(blank=True)),
                ('datos_nuevos', models.JSONField(blank=True, default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('consentimiento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auditoria', to='core.consentimientoinformado')),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Auditoria de Consentimiento',
                'verbose_name_plural': 'Auditorias de Consentimientos',
                'ordering': ['-fecha'],
            },
        ),
    ]
