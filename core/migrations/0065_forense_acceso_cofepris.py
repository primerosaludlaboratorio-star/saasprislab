# Solo modelo ForenseAcceso (Punto 12 COFEPRIS) — sin arrastrar drift de otros modelos.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0064_consentimiento_marketing_y_orden_opcional'),
    ]

    operations = [
        migrations.CreateModel(
            name='ForenseAcceso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'paciente_id',
                    models.PositiveIntegerField(
                        blank=True,
                        help_text='Sin FK a Paciente: solo ID para cero acoplamiento y retención.',
                        null=True,
                        verbose_name='ID paciente (referencial)',
                    ),
                ),
                (
                    'orden_id',
                    models.PositiveIntegerField(blank=True, null=True, verbose_name='ID orden de servicio (referencial)'),
                ),
                (
                    'usuario_id',
                    models.PositiveIntegerField(
                        blank=True,
                        help_text='Nulo si acceso público o anónimo autorizado por token.',
                        null=True,
                        verbose_name='ID usuario staff (referencial)',
                    ),
                ),
                (
                    'accion',
                    models.CharField(
                        choices=[
                            ('PDF_STAFF', 'PDF personal autorizado'),
                            ('PDF_PUBLICO', 'Resultados vía enlace/token público'),
                            ('VALIDACION_TOKEN', 'Validación QR/token sin sesión'),
                            ('EXPEDIENTE_VIEW', 'Vista expediente clínico'),
                            ('WHATSAPP_ENVIO', 'Envío o disparo WhatsApp resultados'),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                (
                    'token_prefix',
                    models.CharField(blank=True, default='', max_length=8, verbose_name='Prefijo token (8 caracteres)'),
                ),
                ('es_publico', models.BooleanField(default=False)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    'empresa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='accesos_forense',
                        to='core.empresa',
                        verbose_name='Empresa',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Acceso forense',
                'verbose_name_plural': 'Accesos forenses',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='forenseacceso',
            index=models.Index(fields=['empresa', 'paciente_id', 'created_at'], name='core_foren_emp_pac_crt'),
        ),
        migrations.AddIndex(
            model_name='forenseacceso',
            index=models.Index(fields=['empresa', 'orden_id', 'created_at'], name='core_foren_emp_ord_crt'),
        ),
    ]
