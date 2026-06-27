"""
MÓDULO DE LABORATORIO - Cumplimiento normativo (NOM-007 + ISO 15189).
"""
from django.conf import settings
from django.db import models

from core.validators import validate_image_upload


# ==============================================================================
# MODELOS DE CUMPLIMIENTO NORMATIVO (NOM-007 + ISO 15189)
# ==============================================================================

class ResponsableSanitario(models.Model):
    """
    Responsable Sanitario del Laboratorio Clínico.
    CRÍTICO NOM-007-SSA3-2011: El reporte debe incluir nombre, cédula y universidad.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='responsable_sanitario',
        verbose_name="Usuario del Sistema",
        help_text="Usuario vinculado al Responsable Sanitario"
    )
    
    # Datos Legales Obligatorios (NOM-007)
    cedula_profesional = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Cédula Profesional (DGP)",
        help_text="Número de cédula profesional emitida por la Dirección General de Profesiones"
    )
    universidad_titulo = models.CharField(
        max_length=255,
        verbose_name="Universidad que Expidió el Título",
        help_text="Nombre completo de la institución educativa"
    )
    
    # Datos Profesionales
    especialidad = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Especialidad",
        help_text="Ej: Químico Farmacobiólogo, Químico Clínico"
    )
    numero_autorizacion_sanitaria = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Número de Autorización Sanitaria",
        help_text="Número de licencia sanitaria del laboratorio (COFEPRIS)"
    )
    
    # Firma Digital
    firma_digital = models.ImageField(
        upload_to='firmas_sanitarias/%Y/',
        blank=True,
        null=True,
        verbose_name="Firma Digital",
        help_text="Imagen de la firma para incluir en reportes PDF",
        validators=[validate_image_upload],
    )
    
    # Control
    activo = models.BooleanField(
        default=True,
        verbose_name="Responsable Activo",
        help_text="Solo puede haber UN responsable activo a la vez"
    )
    fecha_alta = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Alta"
    )
    fecha_baja = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de Baja"
    )
    
    class Meta:
        verbose_name = "Responsable Sanitario"
        verbose_name_plural = "Responsables Sanitarios"
        ordering = ['-activo', '-fecha_alta']
    
    def __str__(self) -> str:
        activo_str = " [ACTIVO]" if self.activo else ""
        return f"Q.F.B. {self.usuario.get_full_name()} - Céd. {self.cedula_profesional}{activo_str}"
    
    def save(self, *args, **kwargs):
        """
        Garantiza que solo haya un Responsable Sanitario activo a la vez.
        Si este se marca como activo, desactiva a los demás.
        """
        if self.activo:
            # Desactivar otros responsables activos
            ResponsableSanitario.objects.filter(activo=True).exclude(pk=self.pk).update(activo=False)
        super().save(*args, **kwargs)


class NotificacionPanico(models.Model):
    """
    Bitácora de Notificación de Valores Críticos (ISO 15189:2012, Punto 5.9).
    
    Requisito Internacional: Cuando se detecta un valor crítico, el laboratorio DEBE:
    - Notificar INMEDIATAMENTE al médico tratante
    - Registrar: ¿A quién? ¿Cuándo? ¿Por qué medio?
    
    Sin este registro, el laboratorio NO puede demostrar que cumplió con la notificación.
    """
    MEDIO_TELEFONO = 'TELEFONO'
    MEDIO_WHATSAPP = 'WHATSAPP'
    MEDIO_EMAIL = 'EMAIL'
    MEDIO_PRESENCIAL = 'PRESENCIAL'
    MEDIO_CHOICES = [
        (MEDIO_TELEFONO, 'Teléfono'),
        (MEDIO_WHATSAPP, 'WhatsApp'),
        (MEDIO_EMAIL, 'Correo Electrónico'),
        (MEDIO_PRESENCIAL, 'Presencial'),
    ]
    
    # Relación con Resultado
    resultado = models.ForeignKey(
        'core.ResultadoParametro',
        on_delete=models.PROTECT,
        related_name='notificaciones_panico',
        verbose_name="Resultado Crítico"
    )
    # v7.5: trazabilidad ISO 15189 enlazada a core.OrdenDeServicio (única orden operativa)
    orden = models.ForeignKey(
        'core.OrdenDeServicio',
        on_delete=models.PROTECT,
        related_name='notificaciones_panico_iso',
        verbose_name="Orden Asociada"
    )
    
    # Datos de la Notificación
    medico_notificado = models.CharField(
        max_length=255,
        verbose_name="Nombre del Médico Notificado",
        help_text="Nombre completo del médico o personal que recibió la notificación"
    )
    cargo_receptor = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Cargo del Receptor",
        help_text="Ej: Médico Tratante, Enfermera Jefe, Residente"
    )
    medio_notificacion = models.CharField(
        max_length=20,
        choices=MEDIO_CHOICES,
        verbose_name="Medio de Notificación"
    )
    numero_contacto = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Número de Contacto",
        help_text="Teléfono o correo usado para la notificación"
    )
    
    # Trazabilidad Forense
    fecha_hora_notificacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y Hora de Notificación"
    )
    usuario_notifico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='notificaciones_panico_realizadas',
        verbose_name="Usuario que Realizó la Notificación"
    )
    
    # Confirmación
    confirmacion_recepcion = models.BooleanField(
        default=False,
        verbose_name="Confirmación de Recepción",
        help_text="El receptor confirmó que recibió y entendió la información"
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones",
        help_text="Detalles adicionales de la notificación (ej: 'Médico indicó que revisará al paciente de inmediato')"
    )
    
    # Auditoría de Seguimiento
    seguimiento_realizado = models.BooleanField(
        default=False,
        verbose_name="Seguimiento Realizado",
        help_text="Se realizó seguimiento para verificar atención al paciente"
    )
    fecha_seguimiento = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de Seguimiento"
    )
    resultado_seguimiento = models.TextField(
        blank=True,
        null=True,
        verbose_name="Resultado del Seguimiento"
    )
    
    class Meta:
        verbose_name = "Notificación de Valor Crítico (Pánico)"
        verbose_name_plural = "Notificaciones de Valores Críticos"
        ordering = ['-fecha_hora_notificacion']
        indexes = [
            models.Index(fields=['orden', '-fecha_hora_notificacion']),
            models.Index(fields=['usuario_notifico', '-fecha_hora_notificacion']),
        ]
    
    def __str__(self):
        an = getattr(self.resultado, 'analito', None)
        nom = an.nombre if an else '?'
        return f"Notificación Pánico - {nom} = {self.resultado.valor} - Notificado a: {self.medico_notificado}"


class ControlCalidad(models.Model):
    """Control de calidad para Levey-Jennings (placeholder en app laboratorio)."""
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="qc_laboratorio")
    equipo = models.CharField(max_length=255)
    parametro = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=12, decimal_places=4)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Control de Calidad (QC)"
        verbose_name_plural = "Control de Calidad (QC)"
        ordering = ["-fecha_registro"]
