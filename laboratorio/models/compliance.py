"""Compliance operativo ISO 15189: no conformidades/CAPA y EQA/PEEC."""

from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.tenant import TenantModel


class NoConformidad(TenantModel):
    """Registro auditable de no conformidad y su ciclo CAPA."""

    empresa = models.ForeignKey('core.Empresa', on_delete=models.PROTECT, related_name='no_conformidades')

    ORIGEN_CHOICES = [
        ('AUDITORIA_INTERNA', 'Auditoria interna'),
        ('AUDITORIA_EXTERNA', 'Auditoria externa'),
        ('QUEJA', 'Queja o reclamacion'),
        ('QC', 'Control de calidad'),
        ('EQA', 'EQA / PEEC'),
        ('SENTINEL', 'Sentinel'),
        ('INCIDENTE', 'Incidente operativo'),
        ('OTRO', 'Otro'),
    ]
    SEVERIDAD_CHOICES = [('MENOR', 'Menor'), ('MAYOR', 'Mayor'), ('CRITICA', 'Critica')]
    ESTADO_CHOICES = [
        ('ABIERTA', 'Abierta'),
        ('INVESTIGACION', 'En investigacion'),
        ('ACCION_CORRECTIVA', 'Accion correctiva'),
        ('VERIFICACION', 'En verificacion'),
        ('CERRADA', 'Cerrada'),
    ]

    folio = models.UUIDField(default=uuid4, unique=True, editable=False)
    titulo = models.CharField(max_length=240)
    descripcion = models.TextField()
    origen = models.CharField(max_length=30, choices=ORIGEN_CHOICES)
    severidad = models.CharField(max_length=10, choices=SEVERIDAD_CHOICES, default='MENOR')
    estado = models.CharField(max_length=24, choices=ESTADO_CHOICES, default='ABIERTA', db_index=True)
    detectada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='no_conformidades_detectadas'
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='no_conformidades_asignadas',
        null=True, blank=True,
    )
    causa_raiz = models.TextField(blank=True, default='')
    correccion_inmediata = models.TextField(blank=True, default='')
    accion_correctiva = models.TextField(blank=True, default='')
    evidencia_verificacion = models.TextField(blank=True, default='')
    fecha_compromiso = models.DateField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True, editable=False)
    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='no_conformidades_cerradas', null=True, blank=True, editable=False,
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['empresa', 'estado'], name='lab_nc_emp_estado_idx'),
            models.Index(fields=['empresa', 'severidad'], name='lab_nc_emp_sev_idx'),
        ]

    def clean(self):
        if self.estado in {'ACCION_CORRECTIVA', 'VERIFICACION', 'CERRADA'} and not self.causa_raiz:
            raise ValidationError({'causa_raiz': 'La causa raiz es obligatoria antes de definir acciones.'})
        if self.estado in {'VERIFICACION', 'CERRADA'} and not self.accion_correctiva:
            raise ValidationError({'accion_correctiva': 'La accion correctiva es obligatoria.'})
        if self.estado == 'CERRADA' and not self.evidencia_verificacion:
            raise ValidationError({'evidencia_verificacion': 'La evidencia de verificacion es obligatoria para cerrar.'})

    def transition(self, estado, usuario, notas=''):
        """Avanza el flujo CAPA y registra el cambio en una bitacora inmutable."""
        allowed = {
            'ABIERTA': {'INVESTIGACION'},
            'INVESTIGACION': {'ACCION_CORRECTIVA'},
            'ACCION_CORRECTIVA': {'VERIFICACION'},
            'VERIFICACION': {'CERRADA', 'ACCION_CORRECTIVA'},
            'CERRADA': set(),
        }
        if estado not in allowed.get(self.estado, set()):
            raise ValidationError(f'Transicion CAPA no permitida: {self.estado} -> {estado}.')
        previous = self.estado
        previous_closed_at = self.fecha_cierre
        previous_closed_by = self.cerrado_por
        self.estado = estado
        if estado == 'CERRADA':
            self.fecha_cierre = timezone.now()
            self.cerrado_por = usuario
        try:
            self.full_clean()
            self.save()
        except Exception:
            self.estado = previous
            self.fecha_cierre = previous_closed_at
            self.cerrado_por = previous_closed_by
            raise
        NoConformidadEvento.objects.create(
            no_conformidad=self, estado_anterior=previous, estado_nuevo=estado,
            usuario=usuario, notas=notas,
        )
        return self


class NoConformidadEvento(models.Model):
    """Bitacora append-only del ciclo de vida CAPA."""

    no_conformidad = models.ForeignKey(NoConformidad, on_delete=models.PROTECT, related_name='eventos')
    estado_anterior = models.CharField(max_length=24)
    estado_nuevo = models.CharField(max_length=24)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    notas = models.TextField(blank=True, default='')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['creado_en']

    def delete(self, *args, **kwargs):
        raise ValidationError('La bitacora CAPA es append-only y no se puede eliminar.')


class RondaEQA(TenantModel):
    """Ronda de evaluacion externa de calidad (EQA/PEEC)."""

    empresa = models.ForeignKey('core.Empresa', on_delete=models.PROTECT, related_name='rondas_eqa')

    ESTADO_CHOICES = [
        ('PLANIFICADA', 'Planificada'),
        ('MUESTRA_RECIBIDA', 'Muestra recibida'),
        ('ENVIADA', 'Resultados enviados'),
        ('EVALUADA', 'Evaluada'),
        ('CERRADA', 'Cerrada'),
    ]
    proveedor = models.CharField(max_length=240)
    programa = models.CharField(max_length=240)
    codigo_ronda = models.CharField(max_length=120)
    fecha_recepcion = models.DateField(null=True, blank=True)
    fecha_limite = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PLANIFICADA', db_index=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    evidencia = models.TextField(blank=True, default='')
    observaciones = models.TextField(blank=True, default='')
    no_conformidad = models.ForeignKey(
        NoConformidad, on_delete=models.SET_NULL, null=True, blank=True, related_name='rondas_eqa'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'programa', 'codigo_ronda'], name='lab_eqa_emp_prog_codigo_uniq')
        ]
        indexes = [models.Index(fields=['empresa', 'estado'], name='lab_eqa_emp_estado_idx')]

    def clean(self):
        if self.fecha_limite and self.fecha_recepcion and self.fecha_limite < self.fecha_recepcion:
            raise ValidationError({'fecha_limite': 'La fecha limite no puede preceder a la recepcion.'})
        if self.estado in {'EVALUADA', 'CERRADA'} and not self.evidencia:
            raise ValidationError({'evidencia': 'La evidencia del proveedor es obligatoria al evaluar la ronda.'})


class ResultadoEQA(models.Model):
    """Resultado de un analito dentro de una ronda EQA, con z-score auditable."""

    EVALUACION_CHOICES = [('PENDIENTE', 'Pendiente'), ('SATISFACTORIO', 'Satisfactorio'), ('ALERTA', 'Alerta'), ('NO_SATISFACTORIO', 'No satisfactorio')]
    ronda = models.ForeignKey(RondaEQA, on_delete=models.PROTECT, related_name='resultados')
    analito = models.ForeignKey('lims.Analito', on_delete=models.PROTECT, related_name='resultados_eqa')
    resultado_laboratorio = models.DecimalField(max_digits=18, decimal_places=6)
    media_grupo = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    desviacion_grupo = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    z_score = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True, editable=False)
    evaluacion = models.CharField(max_length=20, choices=EVALUACION_CHOICES, default='PENDIENTE')
    comentario = models.TextField(blank=True, default='')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['ronda', 'analito'], name='lab_eqa_ronda_analito_uniq')]

    def evaluar(self):
        if self.media_grupo is None or not self.desviacion_grupo or self.desviacion_grupo <= 0:
            raise ValidationError('Se requieren media y desviacion de grupo positivas para evaluar EQA.')
        self.z_score = (self.resultado_laboratorio - self.media_grupo) / self.desviacion_grupo
        abs_z = abs(self.z_score)
        self.evaluacion = 'SATISFACTORIO' if abs_z <= 2 else 'ALERTA' if abs_z <= 3 else 'NO_SATISFACTORIO'
        self.save(update_fields=['z_score', 'evaluacion'])
        return self.evaluacion
