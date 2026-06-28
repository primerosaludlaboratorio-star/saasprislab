from django.db import models
from django.utils import timezone
from datetime import timedelta

class PlanSaaS(models.Model):
    nombre = models.CharField(max_length=50, unique=True, help_text="Ej. Básico, Pro, Enterprise")
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_usuarios = models.IntegerField(default=10, help_text="Límite de usuarios por cuenta")
    incluye_iot = models.BooleanField(default=False, help_text="¿Permite Kioscos IoT?")
    incluye_api = models.BooleanField(default=False, help_text="¿Acceso a API de integración?")
    
    class Meta:
        verbose_name = 'Plan SaaS'
        verbose_name_plural = 'Planes SaaS'

    def __str__(self):
        return f"{self.nombre} (${self.precio_mensual})"


class SuscripcionTenant(models.Model):
    ESTADO_ACTIVA = 'ACTIVA'
    ESTADO_VENCIDA = 'VENCIDA'
    ESTADO_CANCELADA = 'CANCELADA'
    ESTADO_TRIAL = 'TRIAL'
    
    ESTADOS_CHOICES = [
        (ESTADO_ACTIVA, 'Activa'),
        (ESTADO_VENCIDA, 'Vencida (Bloqueada)'),
        (ESTADO_CANCELADA, 'Cancelada'),
        (ESTADO_TRIAL, 'Período de Prueba'),
    ]

    empresa = models.OneToOneField('core.Empresa', on_delete=models.CASCADE, related_name='suscripcion')
    plan = models.ForeignKey(PlanSaaS, on_delete=models.RESTRICT, related_name='suscripciones')
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default=ESTADO_TRIAL)
    
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_proximo_corte = models.DateTimeField(help_text="Fecha en que se cobrará o vencerá la suscripción")
    
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = 'Suscripción de Tenant'
        verbose_name_plural = 'Suscripciones de Tenants'

    def __str__(self):
        return f"{self.empresa.nombre} - {self.plan.nombre} ({self.estado})"

    def save(self, *args, **kwargs):
        if not self.fecha_proximo_corte:
            # Default: 14 días de Trial si no se especifica
            self.fecha_proximo_corte = timezone.now() + timedelta(days=14)
        super().save(*args, **kwargs)

    @property
    def esta_activa(self):
        if self.estado in [self.ESTADO_ACTIVA, self.ESTADO_TRIAL]:
            return True
        return False
