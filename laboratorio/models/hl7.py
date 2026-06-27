"""
MÓDULO DE LABORATORIO - Integración HL7/ASTM y cola de cuarentena.
"""
from django.db import models


class ResultadoHL7(models.Model):
    """
    Resultado recibido crudamente desde un analizador de laboratorio vía HL7/ASTM.
    Antes de integrarse a Resultado, pasa por validación QC y mapeo de parámetros.
    """
    ESTADO_CHOICES = [
        ('RECIBIDO', 'Recibido — Pendiente mapeo'),
        ('MAPEADO', 'Mapeado — Pendiente QC'),
        ('QC_OK', 'QC Aprobado — Listo para validar'),
        ('QC_FALLO', 'QC Fallido — Requiere revisión'),
        ('INTEGRADO', 'Integrado a Resultado'),
        ('RECHAZADO', 'Rechazado manualmente'),
    ]

    mensaje_crudo = models.TextField(help_text='Mensaje HL7/ASTM raw recibido del analizador')
    orden = models.ForeignKey(
        'laboratorio.Orden', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resultados_hl7'
    )
    parametro = models.ForeignKey(
        'laboratorio.Parametro', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resultados_hl7'
    )
    codigo_parametro_equipo = models.CharField(max_length=50, help_text='Código enviado por el equipo (ej: GLU, HGB)')
    valor_raw = models.CharField(max_length=100)
    unidad_raw = models.CharField(max_length=30, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='RECIBIDO', db_index=True)
    ip_equipo = models.GenericIPAddressField(null=True, blank=True)
    protocolo = models.CharField(
        max_length=10,
        choices=[
            ('HL7', 'HL7 v2.x'),
            ('ASTM', 'ASTM E1394'),
            ('JSON', 'JSON / API'),
        ],
        default='HL7',
    )
    fecha_recepcion = models.DateTimeField(auto_now_add=True)
    fecha_integracion = models.DateTimeField(null=True, blank=True)
    notas_qc = models.TextField(blank=True)

    class Meta:
        app_label = 'laboratorio'
        verbose_name = 'Resultado HL7/ASTM'
        verbose_name_plural = 'Resultados HL7/ASTM'
        ordering = ['-fecha_recepcion']
        indexes = [
            models.Index(fields=['estado', 'fecha_recepcion'], name='hl7_estado_fecha_idx'),
        ]


class ResultadoHL7Huerfano(models.Model):
    """
    Cola de cuarentena (dead letter) — Punto 13 v7.5.
    Resultados que no deben integrarse a ResultadoParametro hasta revisión QC:
    sin mapeo a Analito, unidad incompatible con catálogo, o valor no numérico.
    """
    MOTIVO_CHOICES = [
        ('SIN_MAPEO_ANALITO', 'Código equipo sin match en LIMS'),
        ('UNIDAD_INCOMPATIBLE', 'Unidad equipo distinta al catálogo'),
        ('VALOR_NO_NUMERICO', 'Valor no convertible a Decimal (analito numérico)'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='hl7_huerfanos',
    )
    motivo = models.CharField(max_length=40, choices=MOTIVO_CHOICES, db_index=True)
    codigo_equipo = models.CharField(max_length=80)
    valor_raw = models.CharField(max_length=200)
    unidad_equipo = models.CharField(max_length=80, blank=True)
    unidad_catalogo = models.CharField(max_length=120, blank=True)
    analito = models.ForeignKey(
        'lims.Analito',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hl7_huerfanos',
    )
    item_json = models.TextField(help_text='Ítem parseado + meta (JSON)')
    mensaje_contexto = models.TextField(blank=True, help_text='Extracto del mensaje crudo')
    ip_equipo = models.GenericIPAddressField(null=True, blank=True)
    protocolo = models.CharField(max_length=10, blank=True)
    numero_orden_equipo = models.CharField(max_length=80, blank=True)
    estado_revision = models.CharField(
        max_length=20,
        choices=[
            ('PENDIENTE', 'Pendiente revisión QC'),
            ('REVISADO', 'Revisado'),
        ],
        default='PENDIENTE',
        db_index=True,
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'laboratorio'
        verbose_name = 'HL7 — resultado en cuarentena'
        verbose_name_plural = 'HL7 — cola de cuarentena'
        ordering = ['-creado']
        indexes = [
            models.Index(fields=['empresa', 'estado_revision', '-creado'], name='hl7huerf_emp_est_idx'),
        ]

    def __str__(self):
        return f'{self.motivo} {self.codigo_equipo} @ {self.creado:%Y-%m-%d %H:%M}'
