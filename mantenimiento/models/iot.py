"""
CMMS V8.0 — Iot
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from .gemelo import ExpedienteEquipo

# =============================================================================
# SUBSISTEMA F — TELEMETRÍA IoT: Sensores de Temperatura / Humedad
# =============================================================================

class SensorIoT(models.Model):
    """
    Registro de un sensor físico (Temp/Hum/CO2) vinculado a un equipo
    o área de la instalación.

    Los sensores envían lecturas vía API REST (/api/iot/lectura/) o pueden
    cargarse manualmente. El campo `activo` sirve como kill-switch.
    """
    TIPO_CHOICES = [
        ('TEMPERATURA',         'Temperatura (°C)'),
        ('HUMEDAD',             'Humedad Relativa (%)'),
        ('TEMPERATURA_HUMEDAD', 'Temperatura + Humedad'),
        ('CO2',                 'CO2 (ppm)'),
    ]

    empresa    = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="sensores_iot", verbose_name="Empresa",
    )
    expediente = models.ForeignKey(
        ExpedienteEquipo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sensores", verbose_name="Equipo Vinculado",
        help_text="Equipo al que está físicamente instalado este sensor.",
    )
    codigo     = models.CharField(max_length=50, verbose_name="Código / Serial del Sensor")
    nombre     = models.CharField(max_length=150, verbose_name="Nombre / Ubicación")
    tipo       = models.CharField(max_length=25, choices=TIPO_CHOICES, verbose_name="Tipo")
    activo     = models.BooleanField(default=True, verbose_name="Activo")

    # Rangos de operación aceptables (ISO 15189 §6.4)
    temp_min_aceptable  = models.DecimalField(
        max_digits=5, decimal_places=1, default=2.0,
        verbose_name="Temperatura Mínima Aceptable (°C)",
    )
    temp_max_aceptable  = models.DecimalField(
        max_digits=5, decimal_places=1, default=8.0,
        verbose_name="Temperatura Máxima Aceptable (°C)",
    )
    hum_min_aceptable   = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        verbose_name="Humedad Mínima Aceptable (%)",
    )
    hum_max_aceptable   = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        verbose_name="Humedad Máxima Aceptable (%)",
    )

    fecha_instalacion = models.DateField(null=True, blank=True)
    notas             = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Sensor IoT"
        verbose_name_plural = "Sensores IoT"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo"],
                name="mantenimiento_sensoriot_empresa_codigo_uniq",
            )
        ]

    def __str__(self):
        return f"{self.codigo} — {self.nombre} ({self.get_tipo_display()})"


class LecturaSensorIoT(models.Model):
    """
    Lectura individual de un SensorIoT.

    Lógica de alerta automática (ejecutada en el signal post_save):
      Si temperatura > temp_max_aceptable OR temperatura < temp_min_aceptable:
        → Se crea automáticamente un TicketMantenimientoCMMS de PRIORIDAD CRITICA.
        → Se genera una NotificacionDiscrepancia al Director.
        → El flag `fuera_de_rango` se marca True para trazabilidad forense.
    """
    sensor      = models.ForeignKey(
        SensorIoT, on_delete=models.PROTECT,
        related_name="lecturas", verbose_name="Sensor",
    )
    empresa     = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE,
        related_name="lecturas_sensor", verbose_name="Empresa",
    )
    timestamp   = models.DateTimeField(default=timezone.now, verbose_name="Fecha/Hora Lectura",
                                        db_index=True)

    temperatura = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        verbose_name="Temperatura (°C)",
    )
    humedad     = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        verbose_name="Humedad Relativa (%)",
    )

    fuera_de_rango    = models.BooleanField(default=False, verbose_name="Fuera de Rango",
                                             db_index=True)
    ticket_generado   = models.ForeignKey(
        "mantenimiento.TicketMantenimientoCMMS",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lecturas_detonadoras",
        verbose_name="Ticket Generado por esta Lectura",
    )
    origen      = models.CharField(
        max_length=10,
        choices=[('API', 'API REST (IoT)'), ('MANUAL', 'Captura Manual')],
        default='API', verbose_name="Origen",
    )

    class Meta:
        verbose_name = "Lectura de Sensor IoT"
        verbose_name_plural = "Lecturas de Sensores IoT"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["sensor", "-timestamp"]),
            models.Index(fields=["empresa", "fuera_de_rango", "-timestamp"]),
        ]

    def __str__(self):
        t = f"{self.temperatura}°C" if self.temperatura is not None else "—"
        h = f"{self.humedad}%" if self.humedad is not None else "—"
        return f"{self.sensor.codigo} @ {self.timestamp:%d/%m %H:%M} | T:{t} H:{h}"


