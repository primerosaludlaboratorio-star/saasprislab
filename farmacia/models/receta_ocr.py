"""Capturas OCR de recetas para sugerir medicamentos en el PDV."""

from django.conf import settings
from django.db import models

from core.tenant import TenantModel
from core.validators import validate_image_upload
from core.models import Empresa


class LecturaRecetaFarmacia(TenantModel):
    """Resultado auditable de una lectura de receta; nunca crea una venta sola."""

    ESTADOS = [
        ("PROCESADA", "Procesada; requiere confirmación"),
        ("CONFIRMADA", "Sugerencias confirmadas por usuario"),
        ("ERROR", "Error de lectura"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="lecturas_receta_farmacia")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="lecturas_receta_farmacia",
    )
    imagen = models.ImageField(
        upload_to="recetas_farmacia/%Y/%m/%d/",
        validators=[validate_image_upload],
        max_length=255,
    )
    texto_extraido = models.TextField(blank=True, default="")
    datos_extraidos = models.JSONField(default=dict, blank=True)
    sugerencias = models.JSONField(default=list, blank=True)
    productos_confirmados = models.JSONField(default=list, blank=True)
    confianza = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="PROCESADA", db_index=True)
    error = models.TextField(blank=True, default="")
    confirmada_en = models.DateTimeField(null=True, blank=True)
    confirmada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lecturas_receta_farmacia_confirmadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Lectura OCR de receta de farmacia"
        verbose_name_plural = "Lecturas OCR de recetas de farmacia"

    def __str__(self):
        return f"Receta farmacia #{self.pk} - {self.estado}"
