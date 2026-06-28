"""
Rastro forense COFEPRIS / LFPDPPP — Punto 12.

Regla de cero-PHI: no almacenar nombres, resultados clínicos ni contacto;
solo identificadores referenciales y metadatos técnicos/consentimiento (banderas).
"""
from django.db import models

from .base import Empresa


class ForenseAcceso(models.Model):
    """
    Acceso a datos de salud — registro append-only para auditoría.

    Retención (LFPDPPP): conservar al menos 5 años salvo política interna
    o resolución de autoridad que indique lo contrario; archivar fuera de línea
    después de ese plazo si aplica.
    """

    ACCION_PDF_STAFF = 'PDF_STAFF'
    ACCION_PDF_PUBLICO = 'PDF_PUBLICO'
    ACCION_VALIDACION_TOKEN = 'VALIDACION_TOKEN'
    ACCION_EXPEDIENTE_VIEW = 'EXPEDIENTE_VIEW'
    ACCION_WHATSAPP_ENVIO = 'WHATSAPP_ENVIO'

    ACCION_CHOICES = [
        (ACCION_PDF_STAFF, 'PDF personal autorizado'),
        (ACCION_PDF_PUBLICO, 'Resultados vía enlace/token público'),
        (ACCION_VALIDACION_TOKEN, 'Validación QR/token sin sesión'),
        (ACCION_EXPEDIENTE_VIEW, 'Vista expediente clínico'),
        (ACCION_WHATSAPP_ENVIO, 'Envío o disparo WhatsApp resultados'),
    ]

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='accesos_forense',
        verbose_name='Empresa',
    )
    paciente_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='ID paciente (referencial)',
        help_text='Sin FK a Paciente: solo ID para cero acoplamiento y retención.',
    )
    orden_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='ID orden de servicio (referencial)',
    )
    usuario_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='ID usuario staff (referencial)',
        help_text='Nulo si acceso público o anónimo autorizado por token.',
    )
    accion = models.CharField(max_length=32, choices=ACCION_CHOICES, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    token_prefix = models.CharField(
        max_length=8,
        blank=True,
        default='',
        verbose_name='Prefijo token (8 caracteres)',
    )
    es_publico = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Acceso forense'
        verbose_name_plural = 'Accesos forenses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['empresa', 'paciente_id', 'created_at'], name='core_foren_emp_pac_crt'),
            models.Index(fields=['empresa', 'orden_id', 'created_at'], name='core_foren_emp_ord_crt'),
        ]

    def __str__(self):
        return f'{self.accion} empresa={self.empresa_id} p={self.paciente_id} o={self.orden_id} @ {self.created_at}'
