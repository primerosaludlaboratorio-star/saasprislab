"""
INVENTARIO V8.0 — Logística Inter-Sedes (Traspasos y Notificaciones)
"""
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from .compras import OrdenDeCompra


# =============================================================================
# PARTE 5: LOGÍSTICA INTER-SEDES
# =============================================================================

class TraspasoInventario(models.Model):
    """Traspaso de stock entre sucursales o almacenes internos."""
    SILO_CHOICES = [
        ('LAB',         'Laboratorio (Reactivos / Calibradores)'),
        ('CONSULTORIO', 'Consultorio (Material de Curación)'),
        ('GENERAL',     'Insumos Generales (Papelería / Limpieza)'),
    ]
    ESTADO_CHOICES = [
        ('BORRADOR',     'Borrador'),
        ('EN_TRANSITO',  'En Tránsito'),
        ('RECIBIDO',     'Recibido y Confirmado'),
        ('RECHAZADO',    'Rechazado por Receptor'),
        ('CANCELADO',    'Cancelado'),
    ]

    empresa_origen  = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="traspasos_enviados", verbose_name="Empresa Origen",
    )
    empresa_destino = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="traspasos_recibidos", verbose_name="Empresa Destino",
    )
    silo = models.CharField(max_length=15, choices=SILO_CHOICES, verbose_name="Silo")

    folio = models.CharField(max_length=30, verbose_name="Folio")
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES,
                               default="BORRADOR", verbose_name="Estado")
    motivo = models.TextField(verbose_name="Motivo del Traspaso")

    solicitado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.PROTECT,
        related_name="traspasos_solicitados", verbose_name="Solicitado por",
    )
    despachado_por = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="traspasos_despachados", verbose_name="Despachado por",
    )
    receptor = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="traspasos_recibidos_personal", verbose_name="Receptor (firma PIN)",
    )
    razon_rechazo = models.TextField(blank=True, null=True, verbose_name="Razón de Rechazo")

    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Solicitud")
    fecha_despacho  = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Despacho")
    fecha_recepcion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Recepción")

    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Traspaso de Inventario"
        verbose_name_plural = "Traspasos de Inventario"
        ordering = ["-fecha_solicitud"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_origen", "folio"],
                name="inventario_traspaso_empresa_folio_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["empresa_origen", "estado"]),
            models.Index(fields=["empresa_destino", "estado"]),
        ]

    def __str__(self):
        return (f"Traspaso {self.folio} — {self.silo} "
                f"{self.empresa_origen} → {self.empresa_destino} ({self.get_estado_display()})")


class LineaTraspasoInventario(models.Model):
    """Línea de artículo dentro de un TraspasoInventario."""
    SILO_LOTE_CHOICES = [
        ('LAB',         'Silo Laboratorio'),
        ('CONSULTORIO', 'Silo Consultorio'),
        ('GENERAL',     'Silo Generales'),
    ]

    traspaso = models.ForeignKey(
        TraspasoInventario, on_delete=models.CASCADE,
        related_name="lineas", verbose_name="Traspaso",
    )
    empresa_origen = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="lineas_traspaso_origen", verbose_name="Empresa Origen",
    )
    silo = models.CharField(max_length=15, choices=SILO_LOTE_CHOICES)

    lote_content_type = models.ForeignKey(
        ContentType, on_delete=models.PROTECT,
        verbose_name="Tipo de Lote",
        limit_choices_to={"app_label": "inventario",
                          "model__in": ["lotereactivolab",
                                        "loteinsumoconsultorio",
                                        "loteinsumogeneral"]},
    )
    lote_object_id  = models.PositiveIntegerField(verbose_name="ID del Lote")
    lote            = GenericForeignKey("lote_content_type", "lote_object_id")

    nombre_articulo_snapshot = models.CharField(
        max_length=300, verbose_name="Artículo (snapshot al generar traspaso)",
    )
    numero_lote_snapshot = models.CharField(
        max_length=120, blank=True, null=True, verbose_name="Número de Lote (snapshot)",
    )

    cantidad_enviada  = models.DecimalField(max_digits=10, decimal_places=4,
                                             verbose_name="Cantidad Enviada")
    cantidad_recibida = models.DecimalField(max_digits=10, decimal_places=4, default=0,
                                             verbose_name="Cantidad Recibida")

    class Meta:
        verbose_name = "Línea de Traspaso"
        verbose_name_plural = "Líneas de Traspaso"

    def __str__(self):
        return (f"{self.nombre_articulo_snapshot} "
                f"× {self.cantidad_enviada} → {self.traspaso.folio}")


class NotificacionDiscrepancia(models.Model):
    """Notificación automática al Director sobre discrepancias de stock."""
    TIPO_CHOICES = [
        ('OC_DISCREPANCIA',       'Discrepancia en Recepción de OC'),
        ('TRASPASO_DISCREPANCIA', 'Discrepancia en Traspaso Recibido'),
        ('STOCK_CRITICO',         'Stock Crítico Detectado'),
        ('LOTE_CADUCADO',         'Lote Caducado en Almacén'),
        ('HL7_MAPEO',             'HL7 — error de mapeo a LIMS'),
        ('HL7_CUARENTENA',        'HL7 — cuarentena (unidad/valor)'),
        ('QC_WESTGARD',           'CCI — rechazo reglas Westgard (ISO 15189)'),
    ]
    NIVEL_CHOICES = [
        ('INFO',       'Informativa'),
        ('ADVERTENCIA','Advertencia'),
        ('CRITICO',    'Crítico'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="notificaciones_discrepancia", verbose_name="Empresa",
    )
    tipo  = models.CharField(max_length=30, choices=TIPO_CHOICES, verbose_name="Tipo")
    nivel = models.CharField(max_length=15, choices=NIVEL_CHOICES,
                              default="ADVERTENCIA", verbose_name="Nivel")

    titulo   = models.CharField(max_length=255, verbose_name="Título")
    detalle  = models.TextField(verbose_name="Detalle de la Discrepancia")
    resuelta = models.BooleanField(default=False, verbose_name="Resuelta")

    oc       = models.ForeignKey(
        OrdenDeCompra, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notificaciones", verbose_name="OC Relacionada",
    )
    traspaso = models.ForeignKey(
        TraspasoInventario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notificaciones", verbose_name="Traspaso Relacionado",
    )

    generada_en   = models.DateTimeField(auto_now_add=True, verbose_name="Generada")
    resuelta_por  = models.ForeignKey(
        "core.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="discrepancias_resueltas", verbose_name="Resuelta por",
    )
    resuelta_en   = models.DateTimeField(null=True, blank=True, verbose_name="Resuelta en")
    notas_resolucion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Notificación de Discrepancia"
        verbose_name_plural = "Notificaciones de Discrepancia"
        ordering = ["-generada_en"]
        indexes = [
            models.Index(fields=["empresa", "resuelta", "-generada_en"]),
        ]

    def __str__(self):
        return f"[{self.nivel}] {self.titulo} — {self.generada_en:%d/%m/%Y}"
