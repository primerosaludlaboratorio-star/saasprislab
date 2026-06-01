"""
core/models/pris.py
Modelo AccionPRIS — registro inmutable de cada acción propuesta por el agente PRIS.
Arquitectura Copiloto: PRIS sugiere, el humano siempre confirma.
Permisos estrictamente acotados al rol del usuario activo (ISO 15189 / auditoría).
"""
from django.db import models
from django.conf import settings


class AccionPRIS(models.Model):
    """
    Log de acciones propuestas por el agente PRIS.
    Estado PENDIENTE = esperando confirmación humana.
    Estado CONFIRMADO = el humano dio clic final.
    Estado RECHAZADO = el humano rechazó la sugerencia.
    Estado EXPIRADO = nadie respondió en tiempo límite.
    """

    ESTADO_PENDIENTE   = 'PENDIENTE'
    ESTADO_CONFIRMADO  = 'CONFIRMADO'
    ESTADO_RECHAZADO   = 'RECHAZADO'
    ESTADO_EXPIRADO    = 'EXPIRADO'

    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE,  'Pendiente de confirmación'),
        (ESTADO_CONFIRMADO, 'Confirmado por usuario'),
        (ESTADO_RECHAZADO,  'Rechazado por usuario'),
        (ESTADO_EXPIRADO,   'Expirado sin respuesta'),
    ]

    TIPO_PRELLENAR_FORMULARIO = 'PRELLENAR_FORM'
    TIPO_CREAR_REGISTRO       = 'CREAR_REGISTRO'
    TIPO_MODIFICAR_REGISTRO   = 'MODIFICAR_REGISTRO'
    TIPO_NAVEGAR_MODULO       = 'NAVEGAR_MODULO'
    TIPO_GENERAR_REPORTE      = 'GENERAR_REPORTE'
    TIPO_VALIDAR_RESULTADO    = 'VALIDAR_RESULTADO'
    TIPO_ALERTA_CRITICA       = 'ALERTA_CRITICA'

    TIPO_CHOICES = [
        (TIPO_PRELLENAR_FORMULARIO, 'Pre-llenar formulario'),
        (TIPO_CREAR_REGISTRO,       'Crear registro'),
        (TIPO_MODIFICAR_REGISTRO,   'Modificar registro'),
        (TIPO_NAVEGAR_MODULO,       'Navegar a módulo'),
        (TIPO_GENERAR_REPORTE,      'Generar reporte'),
        (TIPO_VALIDAR_RESULTADO,    'Validar resultado de laboratorio'),
        (TIPO_ALERTA_CRITICA,       'Alerta de valor crítico'),
    ]

    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.CASCADE,
        related_name='acciones_pris',
        verbose_name="Empresa",
    )
    usuario_solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acciones_pris_solicitadas',
        verbose_name="Usuario que activó PRIS",
        help_text="El usuario que dio la instrucción de voz o texto a PRIS.",
    )
    usuario_confirmador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acciones_pris_confirmadas',
        verbose_name="Usuario que confirmó/rechazó",
        help_text="El usuario que dio el clic final de Confirmar o Rechazar.",
    )

    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
        verbose_name="Tipo de acción",
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE,
        db_index=True,
        verbose_name="Estado",
    )

    modulo_destino = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Módulo destino",
        help_text="Ej: 'laboratorio.recepcion', 'farmacia.pdv'",
    )
    instruccion_original = models.TextField(
        verbose_name="Instrucción original (voz/texto)",
        help_text="Texto exacto del dictado o comando enviado a PRIS.",
    )
    payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Datos propuestos",
        help_text="JSON con los campos que PRIS propone pre-llenar o ejecutar.",
    )
    resultado = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Resultado de ejecución",
        help_text="Respuesta del sistema tras confirmar la acción (IDs creados, errores, etc.).",
    )

    fecha_propuesta = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de propuesta")
    fecha_resolucion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de resolución")
    expira_en = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expira en",
        help_text="Si no se confirma antes de esta fecha, pasa a estado EXPIRADO.",
    )

    class Meta:
        app_label = 'core'
        verbose_name = "Acción PRIS"
        verbose_name_plural = "Acciones PRIS"
        ordering = ['-fecha_propuesta']
        indexes = [
            models.Index(fields=['estado', 'empresa'], name='pris_estado_empresa_idx'),
            models.Index(fields=['usuario_solicitante', 'estado'], name='pris_user_estado_idx'),
        ]

    def __str__(self):
        return f"[{self.estado}] {self.get_tipo_display()} — {self.modulo_destino} ({self.fecha_propuesta:%Y-%m-%d %H:%M})"

    def confirmar(self, usuario, resultado=None):
        """Confirma la acción. Solo el usuario con permiso en el módulo puede hacerlo."""
        from django.utils import timezone
        self.estado = self.ESTADO_CONFIRMADO
        self.usuario_confirmador = usuario
        self.fecha_resolucion = timezone.now()
        if resultado:
            self.resultado = resultado
        self.save(update_fields=['estado', 'usuario_confirmador', 'fecha_resolucion', 'resultado'])

    def rechazar(self, usuario, motivo=''):
        """Rechaza la acción y registra al usuario que rechazó."""
        from django.utils import timezone
        self.estado = self.ESTADO_RECHAZADO
        self.usuario_confirmador = usuario
        self.fecha_resolucion = timezone.now()
        if motivo:
            self.resultado = {'motivo_rechazo': motivo}
        self.save(update_fields=['estado', 'usuario_confirmador', 'fecha_resolucion', 'resultado'])
