"""
Modelos de agenda y lista de espera del consultorio.
"""
from django.conf import settings
from django.db import models


class AgendaCita(models.Model):
    ESTATUS_PROGRAMADA = "PROGRAMADA"
    ESTATUS_EN_SALA = "EN_SALA"
    ESTATUS_TERMINADA = "TERMINADA"
    ESTATUS_CHOICES = [
        (ESTATUS_PROGRAMADA, "Programada"),
        (ESTATUS_EN_SALA, "En sala"),
        (ESTATUS_TERMINADA, "Terminada"),
    ]

    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="citas_consultorio")
    sucursal = models.ForeignKey("core.Sucursal", on_delete=models.SET_NULL, null=True, blank=True, related_name="citas_consultorio")

    paciente = models.ForeignKey("core.Paciente", on_delete=models.PROTECT, related_name="citas_consultorio")
    medico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="citas_asignadas")

    fecha = models.DateField()
    hora = models.TimeField()
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default=ESTATUS_PROGRAMADA)

    notas = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cita (Agenda)"
        verbose_name_plural = "Citas (Agenda)"
        ordering = ["-fecha", "-hora"]

    def __str__(self) -> str:
        return f"{self.paciente} {self.fecha} {self.hora} ({self.estatus})"


class ListaEspera(models.Model):
    """
    Lista de espera inteligente.
    Cuando se cancela una cita, se notifica automáticamente al siguiente en la lista.
    """
    PRIORIDAD_CHOICES = [
        (1, 'Urgente'),
        (3, 'Alta'),
        (5, 'Normal'),
        (7, 'Baja'),
    ]

    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="lista_espera")
    paciente = models.ForeignKey("core.Paciente", on_delete=models.PROTECT, related_name="espera_consultorio")
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="lista_espera_consultorio"
    )

    motivo = models.TextField(blank=True, verbose_name="Motivo de consulta")
    fecha_preferida = models.DateField(null=True, blank=True, verbose_name="Fecha preferida")
    hora_preferida = models.TimeField(null=True, blank=True, verbose_name="Hora preferida")
    prioridad = models.IntegerField(
        default=5, choices=PRIORIDAD_CHOICES,
        verbose_name="Prioridad"
    )

    # Control de notificación
    notificado = models.BooleanField(default=False)
    fecha_notificacion = models.DateTimeField(null=True, blank=True)
    respuesta_paciente = models.CharField(
        max_length=20, blank=True,
        choices=[('ACEPTA', 'Acepta'), ('RECHAZA', 'Rechaza'), ('SIN_RESPUESTA', 'Sin respuesta')],
    )

    # Estado
    activo = models.BooleanField(default=True)
    atendido = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Paciente en Lista de Espera"
        verbose_name_plural = "Lista de Espera"
        ordering = ['prioridad', 'fecha_registro']

    def __str__(self):
        return f"{self.paciente} - Prioridad {self.get_prioridad_display()}"
