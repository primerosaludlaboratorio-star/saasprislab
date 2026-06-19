from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid


class RutaRecoleccion(models.Model):
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="rutas_recoleccion")
    vehiculo = models.CharField(max_length=120, blank=True, null=True)
    chofer = models.CharField(max_length=255)
    sucursal_origen = models.ForeignKey("core.Sucursal", on_delete=models.SET_NULL, null=True, blank=True, related_name="rutas_origen")
    sucursal_destino = models.ForeignKey("core.Sucursal", on_delete=models.SET_NULL, null=True, blank=True, related_name="rutas_destino")
    hora_salida = models.DateTimeField()

    notas = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ruta de Recolección"
        verbose_name_plural = "Rutas de Recolección"
        ordering = ["-hora_salida"]

    def __str__(self) -> str:
        return f"{self.chofer} - {self.hora_salida:%Y-%m-%d %H:%M}"


class VisitaDomicilio(models.Model):
    ESTATUS_PENDIENTE = "PENDIENTE"
    ESTATUS_ASIGNADA = "ASIGNADA"
    ESTATUS_EN_RUTA = "EN_RUTA"
    ESTATUS_COMPLETADA = "COMPLETADA"
    ESTATUS_CHOICES = [
        (ESTATUS_PENDIENTE, "Pendiente"),
        (ESTATUS_ASIGNADA, "Asignada"),
        (ESTATUS_EN_RUTA, "En ruta"),
        (ESTATUS_COMPLETADA, "Completada"),
    ]

    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, related_name="visitas_domicilio")
    ruta = models.ForeignKey(RutaRecoleccion, on_delete=models.SET_NULL, null=True, blank=True, related_name="visitas")

    # Relación con Orden/Cita (una u otra)
    orden = models.ForeignKey("core.OrdenDeServicio", on_delete=models.SET_NULL, null=True, blank=True, related_name="visitas_domicilio")
    cita = models.ForeignKey("consultorio.AgendaCita", on_delete=models.SET_NULL, null=True, blank=True, related_name="visitas_domicilio")

    direccion = models.TextField()
    latitud = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default=ESTATUS_PENDIENTE)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Visita a Domicilio"
        verbose_name_plural = "Visitas a Domicilio"
        ordering = ["-fecha_creacion"]

    def __str__(self) -> str:
        return f"Visita {self.id} ({self.estatus})"


# ==============================================================================
# SISTEMA DE TRASPASOS/TRANSFERENCIAS ENTRE SUCURSALES
# ==============================================================================
class TransferenciaInventario(models.Model):
    """
    Transferencia de productos entre sucursales.
    Flujo: BORRADOR → ENVIADA → RECIBIDA → COMPLETADA
    """
    ESTADO_BORRADOR = 'BORRADOR'
    ESTADO_ENVIADA = 'ENVIADA'
    ESTADO_EN_TRANSITO = 'EN_TRANSITO'
    ESTADO_RECIBIDA = 'RECIBIDA'
    ESTADO_COMPLETADA = 'COMPLETADA'
    ESTADO_CANCELADA = 'CANCELADA'
    
    ESTADO_CHOICES = [
        (ESTADO_BORRADOR, 'Borrador'),
        (ESTADO_ENVIADA, 'Enviada'),
        (ESTADO_EN_TRANSITO, 'En Tránsito'),
        (ESTADO_RECIBIDA, 'Recibida'),
        (ESTADO_COMPLETADA, 'Completada'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]
    
    # Identificación
    folio = models.CharField(max_length=50, unique=True, editable=False)
    token_rastreo = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Multi-tenant
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='transferencias')
    
    # Sucursales
    sucursal_origen = models.ForeignKey(
        'core.Sucursal', 
        on_delete=models.PROTECT, 
        related_name='transferencias_salientes'
    )
    sucursal_destino = models.ForeignKey(
        'core.Sucursal', 
        on_delete=models.PROTECT, 
        related_name='transferencias_entrantes'
    )
    
    # Estado y tracking
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_BORRADOR)
    
    # Usuarios involucrados
    solicitado_por = models.ForeignKey(
        'core.Usuario', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='transferencias_solicitadas'
    )
    enviado_por = models.ForeignKey(
        'core.Usuario', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='transferencias_enviadas'
    )
    recibido_por = models.ForeignKey(
        'core.Usuario', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='transferencias_recibidas'
    )
    
    # Fechas y tracking temporal
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    
    # Información adicional
    motivo = models.TextField(blank=True, help_text="Razón de la transferencia")
    observaciones_origen = models.TextField(blank=True)
    observaciones_destino = models.TextField(blank=True)
    
    # Transporte
    transportista = models.CharField(max_length=255, blank=True)
    guia_transporte = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = 'Transferencia de Inventario'
        verbose_name_plural = 'Transferencias de Inventario'
        ordering = ['-fecha_creacion']
        permissions = [
            ('autorizar_transferencia', 'Puede autorizar transferencias'),
            ('cancelar_transferencia', 'Puede cancelar transferencias'),
        ]
    
    def __str__(self):
        return f"{self.folio} - {self.sucursal_origen} → {self.sucursal_destino}"
    
    def save(self, *args, **kwargs):
        if not self.folio:
            from django.utils import timezone as _tz
            fecha = _tz.localtime(_tz.now()).strftime('%Y%m%d')
            ultimo = TransferenciaInventario.objects.filter(
                folio__startswith=f'TRANS-{fecha}'
            ).count()
            self.folio = f'TRANS-{fecha}-{ultimo + 1:04d}'
        super().save(*args, **kwargs)
    
    def puede_enviar(self):
        """Valida si la transferencia puede ser enviada"""
        return self.estado == self.ESTADO_BORRADOR and self.detalles.exists()
    
    def puede_recibir(self):
        """Valida si la transferencia puede ser recibida"""
        return self.estado in [self.ESTADO_ENVIADA, self.ESTADO_EN_TRANSITO]
    
    def total_items(self):
        """Total de productos diferentes en la transferencia"""
        return self.detalles.count()
    
    def total_cantidad(self):
        """Cantidad total de unidades"""
        return self.detalles.aggregate(
            total=models.Sum('cantidad')
        )['total'] or 0


class DetalleTransferencia(models.Model):
    """
    Detalle de productos en una transferencia.
    Registra cantidad solicitada vs. cantidad recibida.
    """
    transferencia = models.ForeignKey(
        TransferenciaInventario, 
        on_delete=models.CASCADE, 
        related_name='detalles'
    )
    producto = models.ForeignKey('core.Producto', on_delete=models.PROTECT)
    lote = models.ForeignKey('core.Lote', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Cantidades
    cantidad_solicitada = models.DecimalField(max_digits=10, decimal_places=4)
    cantidad_enviada = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    cantidad_recibida = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Valorización (costo promedio al momento de la transferencia)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    daños_reportados = models.TextField(blank=True)
    
    # Orden dentro de la transferencia
    orden = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Detalle de Transferencia'
        verbose_name_plural = 'Detalles de Transferencia'
        ordering = ['orden', 'producto__nombre']
    
    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad_solicitada}"
    
    def subtotal(self):
        """Valor monetario del detalle"""
        return self.cantidad_solicitada * self.costo_unitario
    
    def diferencia_cantidad(self):
        """Diferencia entre solicitado y recibido"""
        return self.cantidad_recibida - self.cantidad_solicitada
    
    def tiene_diferencias(self):
        """Valida si hay diferencias en cantidades"""
        return self.cantidad_recibida != self.cantidad_solicitada


class LogTransferencia(models.Model):
    """
    Log de cambios de estado de una transferencia (auditoría).
    """
    transferencia = models.ForeignKey(
        TransferenciaInventario, 
        on_delete=models.CASCADE, 
        related_name='logs'
    )
    usuario = models.ForeignKey('core.Usuario', on_delete=models.SET_NULL, null=True)
    estado_anterior = models.CharField(max_length=20, blank=True)
    estado_nuevo = models.CharField(max_length=20)
    comentario = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Log de Transferencia'
        verbose_name_plural = 'Logs de Transferencias'
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.transferencia.folio} - {self.estado_nuevo}"

