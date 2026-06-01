# Manual migration — MarketingTrackingHit + consentimiento prospecto (LFPDPPP opt-in)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0005_cupon_uso"),
    ]

    operations = [
        migrations.AddField(
            model_name="prospectocrm",
            name="consentimiento_comunicaciones",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "LFPDPPP (Mexico): opt-in explicito para envio de promociones o seguimiento comercial. "
                    "Sin True, no se deben registrar hits de tracking vinculados a este prospecto."
                ),
                verbose_name="Consentimiento comunicaciones comerciales",
            ),
        ),
        migrations.CreateModel(
            name="MarketingTrackingHit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "event_key",
                    models.CharField(
                        db_index=True,
                        help_text="Ej: whatsapp_resultado_link, email_apertura",
                        max_length=64,
                        verbose_name="Clave de evento",
                    ),
                ),
                (
                    "meta",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Parametros no sensibles acotados (tamano limitado en vista).",
                    ),
                ),
                ("user_agent_hash", models.CharField(blank=True, default="", max_length=64)),
                ("ip_hash", models.CharField(blank=True, default="", max_length=64)),
                ("creado_en", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "campana",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tracking_hits",
                        to="marketing.campanamarketing",
                    ),
                ),
                (
                    "empresa",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="marketing_tracking_hits",
                        to="core.empresa",
                    ),
                ),
                (
                    "paciente",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="marketing_tracking_hits",
                        to="core.paciente",
                    ),
                ),
                (
                    "prospecto",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="marketing_tracking_hits",
                        to="marketing.prospectocrm",
                    ),
                ),
            ],
            options={
                "verbose_name": "Hit de tracking marketing",
                "verbose_name_plural": "Hits de tracking marketing",
                "ordering": ["-creado_en"],
                "indexes": [
                    models.Index(
                        fields=["empresa", "-creado_en"],
                        name="marketing_m_trk_emp_fecha",
                    ),
                    models.Index(
                        fields=["event_key", "-creado_en"],
                        name="marketing_m_trk_evt_fecha",
                    ),
                ],
            },
        ),
    ]
