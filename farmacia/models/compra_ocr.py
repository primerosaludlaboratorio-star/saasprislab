"""Capturas OCR de facturas/notas de compra de Farmacia."""

from django.conf import settings
from django.db import models

from core.models import Empresa
from core.tenant import TenantModel
from core.validators import validate_image_upload


class LecturaCompraFarmacia(TenantModel):
    """Documento leído; no aplica inventario hasta una confirmación humana."""

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="lecturas_compra_farmacia")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    imagen = models.ImageField(upload_to="compras_ocr/%Y/%m/%d/", validators=[validate_image_upload])
    texto_extraido = models.TextField(blank=True, default="")
    datos_extraidos = models.JSONField(default=dict, blank=True)
    sugerencias = models.JSONField(default=list, blank=True)
    items_confirmados = models.JSONField(default=list, blank=True)
    estado = models.CharField(max_length=20, default="PROCESADA", db_index=True)
    confianza = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    error = models.TextField(blank=True, default="")
    confirmado_en = models.DateTimeField(null=True, blank=True)
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lecturas_compra_farmacia_confirmadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Lectura OCR de compra de farmacia"
        verbose_name_plural = "Lecturas OCR de compras de farmacia"
