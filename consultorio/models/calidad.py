"""
Modelos de encuestas NPS, seguimiento de tratamiento e incidencias Sentinel.
"""
from django.conf import settings
from django.db import models


class EncuestaSatisfaccion(models.Model):
    """
    Encuesta NPS (Net Promoter Score) post-consulta.
    Mide: Satisfacción general, atención médica, tiempo espera, instalaciones.
    Se envía automáticamente tras finalizar la consulta.
    """
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE)
    consulta = models.OneToOneField(
        "core.ConsultaMedica", on_delete=models.PROTECT,
        related_name='encuesta_satisfaccion_consultorio'
    )
    paciente = models.ForeignKey("core.Paciente", on_delete=models.PROTECT)

    # NPS Core (0-10)
    puntuacion_nps = models.IntegerField(
        verbose_name="¿Qué tan probable es que nos recomiende? (0-10)"
    )

    # Dimensiones (1-5 estrellas)
    atencion_medico = models.IntegerField(
        null=True, blank=True,
        verbose_name="Calidad de atención del médico"
    )
    tiempo_espera = models.IntegerField(
        null=True, blank=True,
        verbose_name="Tiempo de espera"
    )
    instalaciones = models.IntegerField(
        null=True, blank=True,
        verbose_name="Estado de las instalaciones"
    )
    explicacion_tratamiento = models.IntegerField(
        null=True, blank=True,
        verbose_name="Claridad en explicación del tratamiento"
    )

    comentarios = models.TextField(blank=True, verbose_name="Comentarios libres")
    recomendaria = models.BooleanField(default=True, verbose_name="¿Nos recomendaría?")

    # Estado del envío
    token_encuesta = models.CharField(
        max_length=64, unique=True, blank=True,
        verbose_name="Token único de acceso"
    )
    enviada = models.BooleanField(default=False)
    respondida = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Encuesta de Satisfacción"
        verbose_name_plural = "Encuestas de Satisfacción"
        ordering = ['-fecha_respuesta']

    def __str__(self):
        return f"NPS: {self.puntuacion_nps}/10 - {self.paciente}"

    @property
    def clasificacion_nps(self):
        """Clasifica: Promotor (9-10), Pasivo (7-8), Detractor (0-6)."""
        if self.puntuacion_nps >= 9:
            return 'PROMOTOR'
        elif self.puntuacion_nps >= 7:
            return 'PASIVO'
        return 'DETRACTOR'

    def save(self, *args, **kwargs):
        if not self.token_encuesta:
            import secrets
            self.token_encuesta = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)


class SeguimientoTratamiento(models.Model):
    """
    Sistema de seguimiento post-consulta.
    Genera alertas automáticas sobre: medicación, próximas citas, estudios pendientes.
    """
    TIPO_CHOICES = [
        ('MEDICACION', 'Recordatorio de Medicación'),
        ('PROXIMA_CITA', 'Recordatorio de Próxima Cita'),
        ('ESTUDIOS', 'Estudios Pendientes'),
        ('EVOLUCION', 'Seguimiento de Evolución'),
        ('CONTROL', 'Control de Seguimiento'),
    ]

    CANAL_CHOICES = [
        ('WHATSAPP', 'WhatsApp'),
        ('SMS', 'SMS'),
        ('EMAIL', 'Correo Electrónico'),
        ('SISTEMA', 'Notificación en el Sistema'),
    ]

    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE)
    consulta = models.ForeignKey(
        "core.ConsultaMedica", on_delete=models.PROTECT,
        related_name='seguimientos_consultorio'
    )
    paciente = models.ForeignKey(
        "core.Paciente", on_delete=models.PROTECT,
        related_name="seguimientos_tratamiento"
    )

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    canal = models.CharField(max_length=20, choices=CANAL_CHOICES, default='WHATSAPP')

    mensaje = models.TextField(verbose_name="Mensaje del recordatorio")
    fecha_programada = models.DateTimeField(verbose_name="Fecha y hora programada")

    # Estado de envío
    enviado = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(null=True, blank=True)

    # Recurrencia (para medicación)
    recurrente = models.BooleanField(default=False)
    intervalo_horas = models.IntegerField(
        null=True, blank=True,
        verbose_name="Cada cuántas horas",
        help_text="Ej: 8 para cada 8 horas"
    )
    fecha_fin = models.DateField(
        null=True, blank=True,
        verbose_name="Última fecha del tratamiento"
    )

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Seguimiento de Tratamiento"
        verbose_name_plural = "Seguimientos de Tratamiento"
        ordering = ['fecha_programada']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.paciente} ({self.fecha_programada})"


class IncidenciaSentinel(models.Model):
    """
    Registro de incidencias detectadas automáticamente (middleware) o reportadas
    por el usuario (botón de queja). Incluye análisis de IA y estado de reparación.
    Modelo central del sistema PRIS SENTINEL.
    Diferente de core.IncidenciaOperativa (auditoría de negocio);
    este es para telemetría técnica del módulo consultorio.
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_REPARACION', 'En Reparación'),
        ('SOLUCIONADO', 'Solucionado'),
    ]
    ORIGEN_CHOICES = [
        ('MIDDLEWARE', 'Captura Automática (Middleware)'),
        ('FEEDBACK', 'Reporte del Usuario (Feedback)'),
        ('MANUAL', 'Registro Manual'),
    ]
    SEVERIDAD_CHOICES = [
        ('CRITICA', 'Crítica (500 / DB Error)'),
        ('ALTA', 'Alta (404 / Lógica rota)'),
        ('MEDIA', 'Media (Warning / UX)'),
        ('BAJA', 'Baja (Cosmético / Informativo)'),
    ]

    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="incidencias_sentinel"
    )

    # === ORIGEN Y CONTEXTO ===
    origen = models.CharField(
        max_length=20, choices=ORIGEN_CHOICES, default='MIDDLEWARE',
        verbose_name="Origen de la incidencia"
    )
    usuario_reporta = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='incidencias_reportadas',
        verbose_name="Usuario que experimentó el error"
    )
    url_afectada = models.CharField(
        max_length=500, blank=True, default='',
        verbose_name="URL donde ocurrio el error"
    )
    metodo_http = models.CharField(
        max_length=10, blank=True,
        verbose_name="Método HTTP (GET/POST)"
    )
    namespace = models.CharField(
        max_length=100, blank=True, default='consultorio',
        verbose_name="Namespace del módulo afectado"
    )

    # === DATOS TÉCNICOS ===
    codigo_http = models.IntegerField(
        default=500,
        verbose_name="Código HTTP del error"
    )
    tipo_excepcion = models.CharField(
        max_length=255, blank=True,
        verbose_name="Tipo de excepción (class name)"
    )
    traceback_completo = models.TextField(
        blank=True,
        verbose_name="Traceback técnico completo"
    )
    datos_request = models.JSONField(
        default=dict, blank=True,
        verbose_name="Datos del request (sanitizados)",
        help_text="GET/POST params sin datos sensibles (passwords, tokens)"
    )
    tag = models.CharField(
        max_length=50, default='#BUG_CONSULTA',
        verbose_name="Tag de clasificación"
    )

    # === FEEDBACK DEL USUARIO ===
    descripcion_usuario = models.TextField(
        blank=True,
        verbose_name="Descripción en lenguaje natural",
        help_text="Lo que el usuario describió que falló"
    )

    # === ANÁLISIS IA ===
    analisis_ia = models.TextField(
        blank=True,
        verbose_name="Análisis generado por Gemini",
        help_text="Resumen ejecutivo del error para el Director"
    )
    contexto_cursor = models.TextField(
        blank=True,
        verbose_name="Contexto técnico para Cursor",
        help_text="Bloque exportable para pegar en Cursor y corregir el bug"
    )
    contexto_reparacion = models.JSONField(
        default=dict, blank=True,
        verbose_name="Contexto de autocuración (JSON)",
        help_text="Datos estructurados generados por IA: archivo, línea, código propuesto, instrucciones SSH"
    )

    # === ESTADO Y SEVERIDAD ===
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE',
        verbose_name="Estado de la incidencia"
    )
    severidad = models.CharField(
        max_length=10, choices=SEVERIDAD_CHOICES, default='ALTA',
        verbose_name="Severidad"
    )

    # === RESOLUCIÓN ===
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='incidencias_resueltas',
        verbose_name="Resuelto por"
    )
    notas_resolucion = models.TextField(
        blank=True,
        verbose_name="Notas de resolución"
    )
    fecha_resolucion = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha de resolución"
    )

    # === AUDITORÍA ===
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Incidencia Sentinel"
        verbose_name_plural = "Incidencias Sentinel"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', '-fecha_creacion']),
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['severidad', '-fecha_creacion']),
        ]

    def __str__(self):
        return f"[{self.get_severidad_display()}] {self.tipo_excepcion or 'Reporte'} - {self.url_afectada} ({self.get_estado_display()})"
