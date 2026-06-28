"""
Motor de Reglas de Negocio Configurables.
Permite al Director activar/desactivar reglas sin tocar codigo.
"""

from django.db import models
from django.conf import settings


class ReglaNegocio(models.Model):
    """Regla de negocio configurable."""
    CATEGORIA_CHOICES = [
        ('PAGO', 'Pagos y Cobranza'),
        ('LABORATORIO', 'Laboratorio'),
        ('FARMACIA', 'Farmacia'),
        ('SEGURIDAD', 'Seguridad'),
        ('ENVIO', 'Envio de Resultados'),
        ('INVENTARIO', 'Inventario'),
        ('GENERAL', 'General'),
    ]
    TIPO_CHOICES = [
        ('BLOQUEO', 'Bloquea accion si no se cumple'),
        ('ALERTA', 'Muestra alerta pero permite continuar'),
        ('AUTOMATICA', 'Se ejecuta automaticamente'),
    ]

    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='reglas_negocio')
    nombre = models.CharField(max_length=200, verbose_name='Nombre de la Regla')
    codigo = models.CharField(max_length=100, verbose_name='Codigo interno',
                               help_text='Ej: TRIPLE_LLAVE, CORTE_CIEGO, STOCK_MINIMO (único por empresa)')
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='GENERAL')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='BLOQUEO')

    activa = models.BooleanField(default=True, verbose_name='Activa')
    parametros = models.JSONField(default=dict, blank=True,
                                   help_text='Parametros configurables: {"tolerancia": 0.50, "dias_vencimiento": 30}')

    prioridad = models.IntegerField(default=10, help_text='Orden de evaluacion (menor = primero)')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    modificado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Regla de Negocio'
        verbose_name_plural = 'Reglas de Negocio'
        ordering = ['categoria', 'prioridad']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'codigo'],
                name='reglas_negocio_reglanegocio_empresa_codigo_uniq',
            ),
        ]

    def __str__(self):
        estado = 'ACTIVA' if self.activa else 'INACTIVA'
        return f'[{estado}] {self.nombre} ({self.codigo})'


class EjecucionRegla(models.Model):
    """Log de ejecucion de reglas (auditoria)."""
    regla = models.ForeignKey(ReglaNegocio, on_delete=models.CASCADE, related_name='ejecuciones')
    resultado = models.BooleanField(verbose_name='Paso la validacion')
    mensaje = models.TextField(blank=True)
    datos_contexto = models.JSONField(default=dict, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ejecucion de Regla'
        verbose_name_plural = 'Ejecuciones de Reglas'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.regla.codigo} → {"OK" if self.resultado else "FALLO"} ({self.fecha:%d/%m %H:%M})'
