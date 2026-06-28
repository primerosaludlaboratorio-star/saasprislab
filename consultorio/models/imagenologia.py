"""
Modelos de reportes de ultrasonido e imágenes.
"""
from django.db import models


# ==============================================================================
# ULTRASONIDO MÉDICO
# ==============================================================================
class ReporteUltrasonido(models.Model):
    """Informe de estudio de ultrasonido generado por el médico."""
    TIPO_ABDOMINAL    = 'ABDOMINAL'
    TIPO_OBSTETRICO   = 'OBSTETRICO'
    TIPO_PELVICO      = 'PELVICO'
    TIPO_TIROIDES     = 'TIROIDES'
    TIPO_RENAL        = 'RENAL'
    TIPO_CARDIACO     = 'CARDIACO'
    TIPO_PARTES_BLANDAS = 'PARTES_BLANDAS'
    TIPO_OTRO         = 'OTRO'
    TIPO_CHOICES      = [
        (TIPO_ABDOMINAL,    'Ultrasonido Abdominal'),
        (TIPO_OBSTETRICO,   'Ultrasonido Obstétrico'),
        (TIPO_PELVICO,      'Ultrasonido Pélvico'),
        (TIPO_TIROIDES,     'Ultrasonido de Tiroides'),
        (TIPO_RENAL,        'Ultrasonido Renal'),
        (TIPO_CARDIACO,     'Ecocardiograma'),
        (TIPO_PARTES_BLANDAS, 'Partes Blandas'),
        (TIPO_OTRO,         'Otro'),
    ]

    ESTADO_BORRADOR   = 'BORRADOR'
    ESTADO_FIRMADO    = 'FIRMADO'
    ESTADO_ENTREGADO  = 'ENTREGADO'
    ESTADO_CHOICES    = [
        (ESTADO_BORRADOR,  'Borrador'),
        (ESTADO_FIRMADO,   'Firmado'),
        (ESTADO_ENTREGADO, 'Entregado al paciente'),
    ]

    empresa     = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='reportes_usg')
    paciente    = models.ForeignKey('core.Paciente', on_delete=models.CASCADE, related_name='reportes_usg')
    medico      = models.ForeignKey('core.Medico', on_delete=models.SET_NULL, null=True, related_name='reportes_usg')
    orden       = models.ForeignKey('core.OrdenDeServicio', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='reportes_usg', verbose_name="Orden de servicio vinculada")
    tipo        = models.CharField(max_length=20, choices=TIPO_CHOICES, default=TIPO_ABDOMINAL)
    estado      = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ESTADO_BORRADOR)

    semanas_gestacion = models.PositiveSmallIntegerField(null=True, blank=True,
                                                          verbose_name="Semanas de gestación (si aplica)")
    hallazgos   = models.TextField(verbose_name="Hallazgos / descripción del estudio")
    conclusion  = models.TextField(verbose_name="Conclusión / diagnóstico")
    recomendaciones = models.TextField(blank=True, verbose_name="Recomendaciones")

    fecha_estudio = models.DateTimeField(auto_now_add=True)
    fecha_firma   = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'consultorio'
        verbose_name = 'Reporte de Ultrasonido'
        verbose_name_plural = 'Reportes de Ultrasonido'
        ordering = ['-fecha_estudio']
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['paciente', '-fecha_estudio']),
        ]

    def __str__(self):
        return f"USG {self.get_tipo_display()} — {self.paciente} ({self.fecha_estudio:%Y-%m-%d})"


class ImagenUltrasonido(models.Model):
    """Imagen capturada durante un estudio de ultrasonido."""
    reporte     = models.ForeignKey(ReporteUltrasonido, on_delete=models.CASCADE, related_name='imagenes')
    imagen      = models.ImageField(upload_to='ultrasonido/', verbose_name="Imagen")
    descripcion = models.CharField(max_length=200, blank=True, verbose_name="Descripción de la imagen")
    orden_display = models.PositiveSmallIntegerField(default=1, verbose_name="Orden de visualización")
    fecha_captura = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'consultorio'
        verbose_name = 'Imagen de Ultrasonido'
        verbose_name_plural = 'Imágenes de Ultrasonido'
        ordering = ['reporte', 'orden_display']

    def __str__(self):
        return f"Imagen {self.orden_display} — {self.reporte}"
