from __future__ import annotations

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Q

from core.validators import validate_image_upload


class CampanaMarketing(models.Model):
    """
    Campañas éticas (segmentación + mensaje). No guarda datos financieros sensibles.
    """
    CANAL_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Notificación Push'),
        ('otro', 'Otro'),
    ]

    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="campanas_marketing")
    sucursal = models.ForeignKey("core.Sucursal", on_delete=models.SET_NULL, null=True, blank=True, related_name="campanas_marketing")

    nombre = models.CharField(max_length=200, blank=True, default='', verbose_name="Nombre de la campaña")
    canal_comunicacion = models.CharField(max_length=20, choices=CANAL_CHOICES, default='whatsapp', verbose_name="Canal")
    segmento = models.CharField(max_length=120, help_text="Ej: diabeticos_inactivos_6m")
    mensaje_whatsapp = models.TextField()
    activa = models.BooleanField(default=True)

    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="campanas_creadas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Campaña de Marketing"
        verbose_name_plural = "Campañas de Marketing"

    def __str__(self) -> str:
        return f"{self.segmento} ({self.empresa_id})"


class CuponMarketing(models.Model):
    """
    Cupón QR (imagen JPG/PNG) con identidad dinámica. El contenido del QR puede ser validado posteriormente.
    """
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="cupones_marketing")
    sucursal = models.ForeignKey("core.Sucursal", on_delete=models.SET_NULL, null=True, blank=True, related_name="cupones_marketing")
    paciente = models.ForeignKey("core.Paciente", on_delete=models.SET_NULL, null=True, blank=True, related_name="cupones_marketing")

    codigo = models.CharField(max_length=60, unique=True)
    porcentaje_descuento = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    descripcion = models.CharField(max_length=255, blank=True, null=True)

    imagen = models.ImageField(upload_to="cupones/%Y/%m/%d/", blank=True, null=True, validators=[validate_image_upload])
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="cupones_creados")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Cupón"
        verbose_name_plural = "Cupones"

    def __str__(self) -> str:
        return self.codigo


class CuponUso(models.Model):
    """
    Uso registrado de un cupón (anti doble descuento + trazabilidad).
    Idempotency-Key HTTP se almacena en idempotency_key para mitigar dobles clics.
    """
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE, related_name="cupon_usos",
    )
    cupon = models.ForeignKey(
        CuponMarketing, on_delete=models.CASCADE, related_name="usos",
    )
    paciente = models.ForeignKey(
        "core.Paciente",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cupones_marketing_uso",
    )
    orden = models.ForeignKey(
        "core.OrdenDeServicio",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cupones_marketing_uso",
    )
    venta = models.ForeignKey(
        "core.Venta",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cupones_marketing_uso",
    )
    idempotency_key = models.CharField(max_length=128, unique=True, db_index=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Uso de cupón"
        verbose_name_plural = "Usos de cupones"
        constraints = [
            models.UniqueConstraint(
                fields=["cupon", "paciente", "orden"],
                condition=Q(orden__isnull=False),
                name="marketing_cuponuso_cupon_paciente_orden_uniq",
            ),
            models.UniqueConstraint(
                fields=["cupon", "venta"],
                condition=Q(venta__isnull=False),
                name="marketing_cuponuso_cupon_venta_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.cupon.codigo} — {self.creado_en:%Y-%m-%d %H:%M}"


# ==============================================================================
# MÓDULO CRM — Gestión de Prospectos y Seguimiento Comercial
# ==============================================================================

class ProspectoCRM(models.Model):
    """
    Prospecto / cliente potencial para el laboratorio o consultorio.
    Permite hacer seguimiento desde el primer contacto hasta la primera orden.
    """
    ORIGEN_CHOICES = [
        ('WHATSAPP', 'WhatsApp'),
        ('LLAMADA',  'Llamada telefónica'),
        ('WEB',      'Sitio web / formulario'),
        ('REFERIDO', 'Referido'),
        ('VISITA',   'Visita directa'),
        ('REDES',    'Redes sociales'),
        ('OTRO',     'Otro'),
    ]
    ESTADO_CHOICES = [
        ('NUEVO',       'Nuevo contacto'),
        ('CONTACTADO',  'Contactado'),
        ('INTERESADO',  'Interesado'),
        ('COTIZADO',    'Cotización enviada'),
        ('GANADO',      'Convertido en paciente'),
        ('PERDIDO',     'Perdido'),
    ]

    empresa   = models.ForeignKey("core.Empresa",  on_delete=models.CASCADE, related_name='prospectos_crm')
    sucursal  = models.ForeignKey("core.Sucursal",  on_delete=models.SET_NULL, null=True, blank=True)
    asignado_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='prospectos_asignados', verbose_name="Asignado a"
    )

    nombre    = models.CharField(max_length=200, verbose_name="Nombre completo")
    telefono  = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    email     = models.EmailField(blank=True, verbose_name="Correo electrónico")
    consentimiento_comunicaciones = models.BooleanField(
        default=False,
        verbose_name="Consentimiento comunicaciones comerciales",
        help_text=(
            "LFPDPPP (México): opt-in explícito para envío de promociones o seguimiento comercial. "
            "Sin True, no se deben registrar hits de tracking vinculados a este prospecto."
        ),
    )
    empresa_prospecto = models.CharField(max_length=200, blank=True, verbose_name="Empresa del prospecto")

    origen    = models.CharField(max_length=15, choices=ORIGEN_CHOICES, default='OTRO', verbose_name="Origen del contacto")
    estado    = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='NUEVO', verbose_name="Estado")

    servicio_interes = models.CharField(max_length=300, blank=True, verbose_name="Servicio de interés")
    notas    = models.TextField(blank=True, verbose_name="Notas internas")
    valor_estimado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Valor estimado ($)")

    paciente_convertido = models.ForeignKey(
        "core.Paciente", on_delete=models.SET_NULL, null=True, blank=True,
        related_name='origen_prospecto', verbose_name="Paciente (si fue convertido)"
    )

    creado   = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    fecha_proximo_contacto = models.DateField(null=True, blank=True, verbose_name="Próximo contacto")

    class Meta:
        ordering = ['-creado']
        verbose_name = 'Prospecto CRM'
        verbose_name_plural = 'Prospectos CRM'
        indexes = [
            models.Index(fields=['empresa', 'estado', '-creado']),
            models.Index(fields=['asignado_a', '-creado']),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_estado_display()}) — {self.origen}"


class SeguimientoCRM(models.Model):
    """
    Registro de cada interacción con un prospecto (timeline de actividades).
    """
    TIPO_CHOICES = [
        ('LLAMADA',   'Llamada'),
        ('WHATSAPP',  'WhatsApp'),
        ('EMAIL',     'Email'),
        ('VISITA',    'Visita'),
        ('COTIZACION','Cotización'),
        ('NOTA',      'Nota interna'),
    ]

    prospecto  = models.ForeignKey(ProspectoCRM, on_delete=models.CASCADE, related_name='seguimientos')
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name="Realizado por"
    )

    tipo       = models.CharField(max_length=15, choices=TIPO_CHOICES, default='NOTA', verbose_name="Tipo de contacto")
    descripcion = models.TextField(verbose_name="Descripción")
    resultado   = models.TextField(blank=True, verbose_name="Resultado / respuesta")
    nuevo_estado = models.CharField(
        max_length=15, choices=ProspectoCRM.ESTADO_CHOICES,
        blank=True, verbose_name="Cambio de estado (si aplica)"
    )
    fecha      = models.DateTimeField(auto_now_add=True)
    fecha_proximo = models.DateField(null=True, blank=True, verbose_name="Próximo seguimiento")

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Seguimiento CRM'
        verbose_name_plural = 'Seguimientos CRM'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.nuevo_estado:
            self.prospecto.estado = self.nuevo_estado
            if self.fecha_proximo:
                self.prospecto.fecha_proximo_contacto = self.fecha_proximo
            self.prospecto.save(update_fields=['estado', 'fecha_proximo_contacto'])

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.prospecto.nombre} ({self.fecha:%d/%m/%Y})"


# ==============================================================================
# TRACKING 204 — Registro ligero de eventos (sin cuerpo HTTP)
# ==============================================================================

class MarketingTrackingHit(models.Model):
    """
    Evento de tracking vía GET/HEAD (respuesta 204 al cliente).
    Datos mínimos; evitar PII en meta. IP/UA solo como hash si se requiere agregación.
    """

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="marketing_tracking_hits",
    )
    campana = models.ForeignKey(
        CampanaMarketing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tracking_hits",
    )
    paciente = models.ForeignKey(
        "core.Paciente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketing_tracking_hits",
    )
    prospecto = models.ForeignKey(
        ProspectoCRM,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketing_tracking_hits",
    )
    event_key = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name="Clave de evento",
        help_text="Ej: whatsapp_resultado_link, email_apertura",
    )
    meta = models.JSONField(
        default=dict,
        blank=True,
        help_text="Parámetros no sensibles acotados (tamaño limitado en vista).",
    )
    user_agent_hash = models.CharField(max_length=64, blank=True, default="")
    ip_hash = models.CharField(max_length=64, blank=True, default="")

    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Hit de tracking marketing"
        verbose_name_plural = "Hits de tracking marketing"
        indexes = [
            models.Index(fields=["empresa", "-creado_en"]),
            models.Index(fields=["event_key", "-creado_en"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_key} @ {self.creado_en:%Y-%m-%d %H:%M:%S}"
