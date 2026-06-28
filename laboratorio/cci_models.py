"""
CCI — Control de calidad interno analítico (canónico laboratorio).
Evita conflicto laboratorio/models.py vs paquete models/; importar desde laboratorio.models al final.
"""
from django.db import models
from django.utils import timezone


class MaterialControl(models.Model):
    """Catálogo de material de control (suero, líquido, etc.)."""

    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        related_name='materiales_control',
        verbose_name='Empresa',
    )
    fabricante = models.CharField(max_length=200, verbose_name='Fabricante')
    nombre = models.CharField(max_length=300, verbose_name='Nombre / referencia')
    descripcion_niveles = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Niveles (texto)',
        help_text='Ej. L1 Normal, L2 patológico alto',
    )
    analito = models.ForeignKey(
        'lims.Analito',
        on_delete=models.CASCADE,
        related_name='materiales_control',
        verbose_name='Analito LIMS',
    )
    activo = models.BooleanField(default=True)

    class Meta:
        app_label = 'laboratorio'
        verbose_name = 'Material de control (CCI)'
        verbose_name_plural = 'Materiales de control (CCI)'
        ordering = ['empresa', 'fabricante', 'nombre']
        indexes = [
            models.Index(fields=['empresa', 'analito', 'activo'], name='lab_mc_emp_an_act_idx'),
        ]

    def __str__(self) -> str:
        return f'{self.fabricante} — {self.nombre}'


class LoteMaterialControl(models.Model):
    """Lote físico con media (target) y SD declarados para un nivel."""

    material = models.ForeignKey(
        MaterialControl,
        on_delete=models.CASCADE,
        related_name='lotes',
        verbose_name='Material',
    )
    numero_lote = models.CharField(max_length=120, verbose_name='Número de lote')
    nivel = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Nivel',
        help_text='Ej. L1, L2, Alto',
    )
    media = models.DecimalField(max_digits=16, decimal_places=6, verbose_name='Media (target)')
    sd = models.DecimalField(max_digits=16, decimal_places=6, verbose_name='Desviación estándar')
    fecha_caducidad = models.DateField(null=True, blank=True, verbose_name='Caducidad')
    activo = models.BooleanField(default=True)

    class Meta:
        app_label = 'laboratorio'
        verbose_name = 'Lote de material de control'
        verbose_name_plural = 'Lotes de material de control'
        ordering = ['material', 'numero_lote']
        constraints = [
            models.UniqueConstraint(
                fields=['material', 'numero_lote', 'nivel'],
                name='lab_lotemc_mat_lote_nivel_uniq',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.material} / {self.numero_lote} ({self.nivel or "—"})'


class MedicionControlInterno(models.Model):
    """Medición CCI (sustituye flujo legacy disperso)."""

    ORIGEN_CHOICES = [
        ('HL7', 'HL7 / interfaz'),
        ('MANUAL', 'Captura manual'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        related_name='mediciones_cci',
    )
    equipo = models.ForeignKey(
        'laboratorio.Equipo',
        on_delete=models.CASCADE,
        related_name='mediciones_cci',
    )
    analito = models.ForeignKey(
        'lims.Analito',
        on_delete=models.CASCADE,
        related_name='mediciones_cci',
    )
    lote_material = models.ForeignKey(
        LoteMaterialControl,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mediciones',
    )
    valor = models.DecimalField(max_digits=16, decimal_places=6)
    z_score = models.DecimalField(max_digits=16, decimal_places=6, null=True, blank=True)
    reglas_disparadas = models.JSONField(default=list, blank=True)
    westgard_estado = models.CharField(max_length=20, blank=True, default='')
    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default='HL7')
    fecha_medicion = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        app_label = 'laboratorio'
        verbose_name = 'Medición control interno'
        verbose_name_plural = 'Mediciones control interno'
        ordering = ['-fecha_medicion']
        indexes = [
            models.Index(
                fields=['empresa', 'equipo', 'analito', '-fecha_medicion'],
                name='lab_mci_emp_eq_an_f_idx',
            ),
        ]

    def __str__(self) -> str:
        return f'CCI {self.analito_id} = {self.valor} @ {self.fecha_medicion:%Y-%m-%d %H:%M}'


class EstadoCanalAnalizador(models.Model):
    """Semáforo por empresa + equipo + analito."""

    NORMAL = 'NORMAL'
    ALERTA_QC = 'ALERTA_QC'
    BLOQUEO_METROLOGIA = 'BLOQUEO_METROLOGIA'
    ESTADO_CHOICES = [
        (NORMAL, 'Normal'),
        (ALERTA_QC, 'Alerta QC (Westgard rechazo)'),
        (BLOQUEO_METROLOGIA, 'Bloqueo metrología'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        related_name='estados_canal_analizador',
    )
    equipo = models.ForeignKey(
        'laboratorio.Equipo',
        on_delete=models.CASCADE,
        related_name='estados_canal',
    )
    analito = models.ForeignKey(
        'lims.Analito',
        on_delete=models.CASCADE,
        related_name='estados_canal',
    )
    estado_operativo = models.CharField(
        max_length=30,
        choices=ESTADO_CHOICES,
        default=NORMAL,
        db_index=True,
    )
    motivo = models.TextField(blank=True, default='')
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'laboratorio'
        verbose_name = 'Estado canal analizador'
        verbose_name_plural = 'Estados canal analizador'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'equipo', 'analito'],
                name='lab_estcanal_emp_eq_an_uniq',
            ),
        ]
        indexes = [
            models.Index(
                fields=['empresa', 'equipo', 'estado_operativo'],
                name='lab_estcanal_emp_eq_st_idx',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.equipo_id}/{self.analito_id}: {self.estado_operativo}'
