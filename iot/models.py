"""
Modelos para el módulo de IoT y Kiosco de Auto-Verificación.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Q


class Kiosco(models.Model):
    """
    Representa un dispositivo Kiosco (tablet) conectado al sistema.
    """
    nombre = models.CharField(
        max_length=100,
        help_text='Nombre identificador del kiosco (ej: "Kiosco Recepción 1")'
    )
    
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text='Dirección IP del dispositivo (para identificación)'
    )
    
    mac_address = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        help_text='Dirección MAC del dispositivo'
    )
    
    ubicacion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Ubicación física del kiosco (ej: "Sala de Espera Principal")'
    )
    
    activo = models.BooleanField(
        default=True,
        help_text='Indica si el kiosco está activo y disponible'
    )
    
    ultima_conexion = models.DateTimeField(
        null=True,
        blank=True,
        help_text='\u00daltima vez que el kiosco se conect\u00f3 al sistema'
    )
    
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    # Configuración
    intervalo_polling = models.IntegerField(
        default=2,
        help_text='Intervalo de polling en segundos (cuánto tiempo espera entre consultas)'
    )
    
    class Meta:
        verbose_name = 'Kiosco'
        verbose_name_plural = 'Kioscos'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.ubicacion or 'Sin ubicación'})"
    
    def actualizar_conexion(self):
        """Actualiza la fecha de última conexión."""
        self.ultima_conexion = timezone.now()
        self.save(update_fields=['ultima_conexion'])


class VerificacionKiosco(models.Model):
    """
    Representa una verificación pendiente o completada en un kiosco.
    """
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_CONFIRMADO = 'CONFIRMADO'
    ESTADO_RECHAZADO = 'RECHAZADO'
    ESTADO_EXPIRADO = 'EXPIRADO'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente de Confirmación'),
        (ESTADO_CONFIRMADO, 'Confirmado por Paciente'),
        (ESTADO_RECHAZADO, 'Rechazado por Paciente'),
        (ESTADO_EXPIRADO, 'Expirado (sin respuesta)'),
    ]
    
    orden = models.ForeignKey(
        'core.OrdenDeServicio',
        on_delete=models.CASCADE,
        related_name='verificaciones_kiosco',
        help_text='Orden de servicio LIMS (core) asociada'
    )
    
    kiosco = models.ForeignKey(
        Kiosco,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verificaciones',
        help_text='Kiosco donde se mostrará la verificación'
    )
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE,
        help_text='Estado actual de la verificación'
    )
    
    # Datos a mostrar en el kiosco (JSON)
    datos_mostrar = models.JSONField(
        default=dict,
        help_text='Datos que se mostrarán al paciente en el kiosco (nombre, estudios, etc.)'
    )
    
    # Datos confirmados por el paciente
    datos_confirmados = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text='Datos confirmados por el paciente (si hay cambios)'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora en que el paciente confirmó'
    )
    
    fecha_expiracion = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora en que expira la verificación (si no se confirma)'
    )
    
    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='verificaciones_kiosco_creadas',
        help_text='Usuario que envió la verificación al kiosco'
    )
    
    class Meta:
        verbose_name = 'Verificación de Kiosco'
        verbose_name_plural = 'Verificaciones de Kiosco'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Verificación {self.orden.id} - {self.get_estado_display()}"
    
    def confirmar(self, datos_confirmados=None):
        """Marca la verificación como confirmada."""
        self.estado = self.ESTADO_CONFIRMADO
        self.fecha_confirmacion = timezone.now()
        if datos_confirmados:
            self.datos_confirmados = datos_confirmados
        self.save()
    
    def rechazar(self):
        """Marca la verificación como rechazada."""
        self.estado = self.ESTADO_RECHAZADO
        self.save()
    
    def expirar(self):
        """Marca la verificación como expirada."""
        self.estado = self.ESTADO_EXPIRADO
        self.save()
    
    def esta_expirada(self):
        """Verifica si la verificación ha expirado."""
        if self.fecha_expiracion:
            return timezone.now() > self.fecha_expiracion
        return False


class TransaccionHL7(models.Model):
    """
    Idempotencia cl?nica para mensajes HL7/ASTM/JSON: evita doble integraci?n
    del mismo resultado (mismo orden/analito/valor y contexto de red).
    """
    hash_mensaje = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text='SHA-256 hex del mensaje can?nico (orden + analito + valor + IP).',
    )
    equipo = models.ForeignKey(
        'laboratorio.Equipo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacciones_hl7',
    )
    orden_de_servicio = models.ForeignKey(
        'core.OrdenDeServicio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacciones_hl7',
    )
    analito_id = models.PositiveIntegerField(null=True, blank=True)
    codigo_equipo = models.CharField(max_length=80, blank=True, default='')
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    # Clave lógica por equipo + retransmisión (MSH-10 + código + nº orden); vacío si no hay equipo/MCID.
    transaccion_id = models.CharField(max_length=190, blank=True, default='', db_index=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Transacci?n HL7 (idempotencia)'
        verbose_name_plural = 'Transacciones HL7 (idempotencia)'
        ordering = ['-creado']
        indexes = [
            models.Index(fields=['-creado'], name='iot_txhl7_creado_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=('equipo', 'transaccion_id'),
                condition=Q(equipo__isnull=False) & ~Q(transaccion_id=''),
                name='unique_hl7_transaccion',
            ),
        ]

    def __str__(self):
        return f'TX-HL7 {self.hash_mensaje[:12]}?'
