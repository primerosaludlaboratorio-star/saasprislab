"""
core/models/bienestar_staff.py
════════════════════════════════════════════════════════════════════════════════
FASE 9 — Módulo Bienestar Staff (NOM-035-STPS-2018)

⚠️  CAJA FUERTE INTERNA — AISLAMIENTO TOTAL
    Estos modelos NUNCA deben cruzar con:
    - Modelos de pacientes (Paciente, ExpedienteClinico, CitaMedica)
    - Módulo de Laboratorio
    - Módulo de Farmacia

    Solo se conectan con:
    - core.Usuario (empleado)
    - RRHH/Nómina
    - PRIS (solo para alertas de burnout, NUNCA contenido privado)

Cifrado:
    - django-cryptography: cifrado AES-256 simétrico (Fernet)
    - Los campos `contenido`, `notas_privadas`, `respuestas_json` son ILEGIBLES
      en la DB sin la clave simétrica DJANGO_CRYPTOGRAPHY_KEY
════════════════════════════════════════════════════════════════════════════════
"""

from django.db import models
from django.conf import settings
from core.fields import EncryptedTextField


# ── Choices compartidos ───────────────────────────────────────────────────────
NIVEL_RIESGO_CHOICES = [
    (1, 'Sin riesgo'),
    (2, 'Riesgo bajo'),
    (3, 'Riesgo medio'),
    (4, 'Riesgo alto'),
    (5, 'Riesgo muy alto'),
]

HUMOR_CHOICES = [
    (1, '😔 Muy mal'),
    (2, '😕 Mal'),
    (3, '😐 Regular'),
    (4, '🙂 Bien'),
    (5, '😀 Excelente'),
]


class EvaluacionNOM035(models.Model):
    """
    Evaluación periódica del cuestionario NOM-035-STPS-2018.
    55 ítems que miden: ambiente de trabajo, factores organizacionales,
    factores propios del trabajo, factores externos.

    Cifrado: respuestas_json es ilegible en DB sin DJANGO_CRYPTOGRAPHY_KEY.
    Resultado: solo score y nivel_riesgo son legibles para RRHH.
    """
    empleado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='evaluaciones_nom035',
        verbose_name='Empleado',
        limit_choices_to={'is_active': True},
    )
    fecha = models.DateField(auto_now_add=True)
    periodo = models.CharField(max_length=7, help_text='YYYY-MM')

    respuestas_json = EncryptedTextField(
        help_text='JSON con respuestas 1-5 para cada ítem. CIFRADO AES-256.',
        blank=True, default='',
    )

    score_total = models.IntegerField(default=0, help_text='Suma de respuestas')
    nivel_riesgo = models.IntegerField(choices=NIVEL_RIESGO_CHOICES, default=1)
    completada = models.BooleanField(default=False)
    notas_evaluador = models.TextField(blank=True, default='')
    aplicada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='evaluaciones_aplicadas', blank=True,
    )

    class Meta:
        app_label = 'core'
        verbose_name = 'Evaluación NOM-035'
        verbose_name_plural = 'Evaluaciones NOM-035'
        ordering = ['-fecha']
        unique_together = [['empleado', 'periodo']]

    def __str__(self):
        return f'NOM-035 | {self.empleado.username} | {self.periodo} | Riesgo: {self.nivel_riesgo}'

    @property
    def alerta_requerida(self) -> bool:
        return self.nivel_riesgo >= 3


class DiarioEmocionalStaff(models.Model):
    """
    Diario emocional privado del empleado. Completamente cifrado.
    Solo el empleado puede leer sus propias entradas.
    PRIS puede leer metadatos (humor, fecha) para detección de patrones.
    """
    empleado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='diario_emocional_staff',
    )
    fecha = models.DateField()
    humor_general = models.IntegerField(choices=HUMOR_CHOICES)
    nivel_estres = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 11)],
        help_text='Nivel de estrés del 1 al 10',
    )

    contenido = EncryptedTextField(
        blank=True, default='',
        help_text='Texto libre cifrado. SOLO legible por el empleado.',
    )

    horas_sueno = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    actividad_fisica = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Diario Emocional (Staff)'
        verbose_name_plural = 'Diarios Emocionales (Staff)'
        ordering = ['-fecha']
        unique_together = [['empleado', 'fecha']]

    def __str__(self):
        return f'Diario | {self.empleado.username} | {self.fecha} | Humor: {self.humor_general}'


class SesionCoachingStaff(models.Model):
    """
    Registro de sesión de coaching o apoyo psicológico.
    Las notas del coach están cifradas para proteger la confidencialidad.
    """
    TIPO_SESION = [
        ('COACHING', 'Coaching de desempeño'),
        ('APOYO', 'Apoyo psicológico'),
        ('SEGUIMIENTO', 'Seguimiento NOM-035'),
        ('DISCIPLINARIA', 'Sesión disciplinaria'),
        ('CAPACITACION', 'Capacitación'),
    ]
    ESTADO_CHOICES = [
        ('PROGRAMADA', 'Programada'),
        ('REALIZADA', 'Realizada'),
        ('CANCELADA', 'Cancelada'),
        ('NO_ASISTIO', 'No asistió'),
    ]

    empleado = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sesiones_coaching_recibidas',
    )
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='sesiones_coaching_impartidas',
    )
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_SESION)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PROGRAMADA')
    fecha_sesion = models.DateTimeField()
    duracion_minutos = models.IntegerField(default=60)

    notas_privadas = EncryptedTextField(
        blank=True, default='',
        help_text='Notas confidenciales del coach. CIFRADAS AES-256.',
    )

    compromisos = models.TextField(blank=True, default='', help_text='Compromisos no cifrados')
    proxima_sesion = models.DateField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Sesión de Coaching (Staff)'
        verbose_name_plural = 'Sesiones de Coaching (Staff)'
        ordering = ['-fecha_sesion']


class AlertaBurnout(models.Model):
    """
    Alerta automática generada por PRIS cuando detecta patrones de riesgo.
    SOLO contiene: empleado, fecha, tipo_alerta, nivel.
    NUNCA incluye contenido del diario ni respuestas de la evaluación.
    """
    TIPO_ALERTA = [
        ('HUMOR_BAJO', 'Humor bajo sostenido (>5 días)'),
        ('ESTRES_ALTO', 'Estrés elevado sostenido (>5 días)'),
        ('NOM035_RIESGO', 'Riesgo NOM-035 medio/alto'),
        ('AUSENCIAS', 'Patrón de ausencias frecuentes'),
        ('TURNO_EXCESO', 'Horas extra excesivas (>50h/semana)'),
    ]

    empleado = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='alertas_burnout',
    )
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_ALERTA)
    nivel_riesgo = models.IntegerField(choices=NIVEL_RIESGO_CHOICES)
    fecha = models.DateTimeField(auto_now_add=True)
    atendida = models.BooleanField(default=False)
    atendida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='alertas_burnout_atendidas',
    )
    notas_rrhh = models.TextField(blank=True, default='')

    class Meta:
        app_label = 'core'
        verbose_name = 'Alerta de Burnout'
        verbose_name_plural = 'Alertas de Burnout'
        ordering = ['-fecha']

    def __str__(self):
        return f'Burnout | {self.empleado.username} | {self.get_tipo_display()} | Riesgo: {self.nivel_riesgo}'


class ProgramaCapacitacion(models.Model):
    """Registro de capacitaciones del personal."""
    empleado = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='capacitaciones_staff',
    )
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    horas = models.IntegerField(default=1)
    completada = models.BooleanField(default=False)
    certificado_url = models.URLField(blank=True)
    impartida_por = models.CharField(max_length=200, blank=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Capacitación'
        verbose_name_plural = 'Capacitaciones'
        ordering = ['-fecha_inicio']
