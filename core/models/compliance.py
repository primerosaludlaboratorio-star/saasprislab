"""
Compliance — COFEPRIS (NOM-004-SSA3-2012) y LGPD (Ley General de Protección de Datos)
Modelos para auditoría regulatoria y privacidad de datos.
"""

from django.db import models
from django.utils import timezone
from core.models.base import Empresa, Usuario
from core.models.pacientes import Paciente


# ═══════════════════════════════════════════════════════════════════════════════
# COFEPRIS — Norma Oficial Mexicana 004-SSA3-2012 (Expedientes Clínicos)
# ═══════════════════════════════════════════════════════════════════════════════

class ResponsableSanitario(models.Model):
    """
    Responsable Sanitario — Quimico Farmacéutico Biólogo autorizado.
    COFEPRIS NOM-004-SSA3-2012 requiere responsable firmante de resultados/expedientes.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='responsables_sanitarios',
        verbose_name="Empresa"
    )
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='responsable_sanitario_profile',
        verbose_name="Usuario"
    )
    cedula_profesional = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Cédula Profesional",
        help_text="Cédula QFB expedida por Secretaría de Educación"
    )
    numero_registro_cofepris = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Número de Registro COFEPRIS",
        help_text="Opcional: número de registro ante COFEPRIS"
    )
    fecha_vigencia_inicio = models.DateField(
        verbose_name="Vigencia Inicio"
    )
    fecha_vigencia_fin = models.DateField(
        verbose_name="Vigencia Fin"
    )
    certificado_digital = models.FileField(
        upload_to='certificados_cofepris/',
        blank=True,
        null=True,
        verbose_name="Certificado Digital",
        help_text=".pfx o .pem para firma digital"
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Responsable Sanitario"
        verbose_name_plural = "Responsables Sanitarios"

    def __str__(self) -> str:
        return f"{self.usuario.get_full_name()} (Cédula: {self.cedula_profesional})"

    def esta_vigente(self) -> bool:
        """Retorna True si el registro es vigente."""
        hoy = timezone.now().date()
        return self.activo and self.fecha_vigencia_inicio <= hoy <= self.fecha_vigencia_fin


class FirmaDigitalResultado(models.Model):
    """
    Registro de firma digital de resultados de laboratorio.
    COFEPRIS: trazabilidad y no repudio de quién firmó qué y cuándo.
    """
    responsable_sanitario = models.ForeignKey(
        ResponsableSanitario,
        on_delete=models.PROTECT,
        related_name='firmas_resultados',
        verbose_name="Responsable Sanitario"
    )
    # Referencia al resultado (puede ser OrdenDeServicio u otro modelo)
    modelo_referencia = models.CharField(
        max_length=50,
        verbose_name="Modelo Referencia",
        help_text="Ej: 'OrdenDeServicio', 'ResultadoParametro'"
    )
    objeto_id = models.PositiveIntegerField(
        verbose_name="ID del Objeto"
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name='firmas_digitales',
        verbose_name="Paciente"
    )

    # Firma
    hash_contenido = models.CharField(
        max_length=512,
        verbose_name="Hash SHA-256 del Contenido",
        help_text="Hash del PDF/contenido firmado"
    )
    firma_hexadecimal = models.TextField(
        verbose_name="Firma (Hexadecimal)",
        help_text="Firma digital en formato hexadecimal"
    )
    certificado_usado = models.TextField(
        verbose_name="Certificado Usado",
        blank=True,
        help_text="Serialización del certificado digital usado"
    )

    # Metadata
    fecha_firma = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha/Hora de Firma"
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="IP de Firma"
    )
    verificada = models.BooleanField(
        default=False,
        verbose_name="Firma Verificada",
        help_text="True si la firma fue verificada mediante certificado"
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Firma Digital"
        verbose_name_plural = "Firmas Digitales"
        indexes = [
            models.Index(fields=['paciente', 'fecha_firma']),
            models.Index(fields=['responsable_sanitario', 'fecha_firma']),
        ]

    def save(self, *args, **kwargs):
        if not self.responsable_sanitario.esta_vigente():
            raise ValueError(
                "No se puede firmar con un Responsable Sanitario vencido o inactivo."
            )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Firma {self.paciente.nombre_completo} por {self.responsable_sanitario.usuario.get_full_name()} @ {self.fecha_firma:%Y-%m-%d %H:%M}"


# ═══════════════════════════════════════════════════════════════════════════════
# LGPD — Ley General de Protección de Datos Personales
# ═══════════════════════════════════════════════════════════════════════════════

class ConsentimientoLGPD(models.Model):
    """
    Consentimiento informado del paciente para tratamiento de datos.
    LGPD Art. 6: Consentimiento del titular para recopilar/procesar datos personales.
    """
    TIPO_CONSENTIMIENTO = (
        ('CLINICO', 'Datos Clínicos (Historia, Diagnósticos, Tratamientos)'),
        ('CONTACTO', 'Datos de Contacto (Telefono, Email, SMS)'),
        ('MARKETING', 'Datos para Marketing/Campañas'),
        ('INVESTIGACION', 'Datos para Investigación Médica'),
    )

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='consentimientos_lgpd',
        verbose_name="Paciente"
    )
    tipo = models.CharField(
        max_length=50,
        choices=TIPO_CONSENTIMIENTO,
        verbose_name="Tipo de Consentimiento"
    )
    otorgado = models.BooleanField(
        default=True,
        verbose_name="Otorgado",
        help_text="True = consentimiento dado; False = revocado"
    )

    # Trazabilidad
    fecha_otorgamiento = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Otorgamiento"
    )
    fecha_revocacion = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de Revocación"
    )
    usuario_registro = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='consentimientos_registrados',
        verbose_name="Usuario que Registró"
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="IP de Registro"
    )
    documento_consentimiento = models.FileField(
        upload_to='consentimientos_lgpd/',
        blank=True,
        null=True,
        verbose_name="Documento de Consentimiento",
        help_text="PDF firmado del consentimiento"
    )

    class Meta:
        app_label = 'core'
        unique_together = ('paciente', 'tipo')
        verbose_name = "Consentimiento LGPD"
        verbose_name_plural = "Consentimientos LGPD"

    def __str__(self) -> str:
        estado = "Vigente" if self.otorgado else "Revocado"
        return f"{self.paciente.nombre_completo} — {self.get_tipo_display()} ({estado})"

    def es_vigente(self) -> bool:
        """Retorna True si el consentimiento está otorgado y no ha sido revocado."""
        return self.otorgado and self.fecha_revocacion is None


class DerechoOlvido(models.Model):
    """
    Solicitud de Derecho al Olvido (LGPD Art. 17).
    Paciente puede solicitar que sus datos sean eliminados.
    """
    ESTADO_SOLICITUD = (
        ('SOLICITADO', 'Solicitud Recibida'),
        ('EN_PROCESO', 'En Proceso de Evaluación'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
    )

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='solicitudes_derecho_olvido',
        verbose_name="Paciente"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_SOLICITUD,
        default='SOLICITADO',
        verbose_name="Estado de Solicitud"
    )
    razon = models.TextField(
        verbose_name="Razón de Solicitud"
    )
    datos_a_eliminar = models.TextField(
        verbose_name="Datos Específicos a Eliminar",
        help_text="Descripción de qué datos desea eliminar"
    )

    # Trazabilidad
    fecha_solicitud = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Solicitud"
    )
    fecha_respuesta = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de Respuesta"
    )
    usuario_responsable = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='derechos_olvido_gestionados',
        verbose_name="Usuario Responsable"
    )
    notas_procesamiento = models.TextField(
        blank=True,
        verbose_name="Notas de Procesamiento"
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Derecho al Olvido"
        verbose_name_plural = "Derechos al Olvido"
        ordering = ['-fecha_solicitud']

    def __str__(self) -> str:
        return f"Derecho al Olvido — {self.paciente.nombre_completo} ({self.estado})"


class RegistroAccesoDatos(models.Model):
    """
    Auditoría de acceso a datos sensibles (LGPD).
    Registra quién accedió a qué datos sensibles y cuándo.
    """
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='accesos_datos_registrados',
        verbose_name="Usuario"
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='accesos_datos',
        verbose_name="Paciente Accedido"
    )
    tipo_datos = models.CharField(
        max_length=100,
        verbose_name="Tipo de Datos Accedidos",
        help_text="Ej: 'historia_clinica', 'expediente', 'resultados_lab'"
    )
    accion = models.CharField(
        max_length=20,
        choices=(('READ', 'Lectura'), ('DOWNLOAD', 'Descarga'), ('EXPORT', 'Exportación')),
        default='READ',
        verbose_name="Acción"
    )

    # Metadata
    fecha_acceso = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha/Hora de Acceso"
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="IP"
    )
    motivo = models.TextField(
        blank=True,
        verbose_name="Motivo del Acceso"
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Acceso a Datos Personales"
        verbose_name_plural = "Accesos a Datos Personales"
        indexes = [
            models.Index(fields=['paciente', 'fecha_acceso']),
            models.Index(fields=['usuario', 'fecha_acceso']),
        ]

    def delete(self, *args, **kwargs):
        raise PermissionError("RegistroAccesoDatos es append-only y no puede eliminarse.")

    def __str__(self) -> str:
        return f"{self.usuario.username} accedió {self.tipo_datos} de {self.paciente.nombre_completo} @ {self.fecha_acceso:%Y-%m-%d %H:%M}"
