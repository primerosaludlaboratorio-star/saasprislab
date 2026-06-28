"""
core/models/rrhh.py
Recursos Humanos: Empleados, Evaluaciones 39-A, Desempeño, Asistencia.
Depende de: base.py
"""
from django.db import models

from core.validators import validate_document_upload
from .base import Empresa, Sucursal, Usuario


# ==============================================================================
# BLOQUE 3: RECURSOS HUMANOS Y AUDITORÍA FORENSE
# ==============================================================================
class Empleado(models.Model):
    """Ficha completa de empleado para gestión de RH y blindaje legal."""
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='ficha_empleado',
        verbose_name="Usuario del Sistema"
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='empleados')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sucursal Asignada")

    puesto = models.CharField(max_length=150, verbose_name="Puesto de Trabajo")
    fecha_ingreso = models.DateField(verbose_name="Fecha de Ingreso")
    fecha_fin_periodo_prueba = models.DateField(null=True, blank=True, verbose_name="Fin de Periodo de Prueba (Art. 39-A)")
    activo = models.BooleanField(default=True, verbose_name="Empleado Activo")

    rol_permisos = models.CharField(
        max_length=50,
        choices=[
            ('ADMIN', 'Administrador'),
            ('CAJERO', 'Cajero'),
            ('MEDICO', 'Médico'),
            ('QUIMICO', 'Químico'),
            ('RECEPCION', 'Recepción'),
            ('GERENTE', 'Gerente'),
        ],
        verbose_name="Rol de Permisos"
    )

    telefono_emergencia = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono de Emergencia")
    contacto_emergencia = models.CharField(max_length=255, blank=True, null=True, verbose_name="Contacto de Emergencia")

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ['usuario__last_name', 'usuario__first_name']

    @property
    def nombre_completo(self):
        """Nombre completo del empleado (delegado al usuario)."""
        return self.usuario.get_full_name() or self.usuario.username

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.puesto} ({self.sucursal.nombre if self.sucursal else 'Sin Sucursal'})"


class Bitacora39A(models.Model):
    """Bitácora de evaluación semanal durante periodo de prueba (Art. 39-A)."""
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='evaluaciones_39a')
    periodo_semanal = models.CharField(max_length=20, verbose_name="Periodo Semanal", help_text="Formato: 2024-S01, 2024-S02, etc.")
    fecha_inicio = models.DateField(verbose_name="Fecha Inicio Semana")
    fecha_fin = models.DateField(verbose_name="Fecha Fin Semana")

    puntualidad = models.IntegerField(default=0, verbose_name="Puntualidad (0-100)", help_text="Evaluación de asistencia y puntualidad")
    calidad_captura = models.IntegerField(default=0, verbose_name="Calidad de Captura (0-100)", help_text="Precisión y calidad en la captura de datos/resultados")
    atencion_cliente = models.IntegerField(default=0, verbose_name="Atención al Cliente (0-100)", help_text="Trato, comunicación y servicio al cliente")
    cumplimiento_procesos = models.IntegerField(default=0, verbose_name="Cumplimiento de Procesos (0-100)", help_text="Adherencia a protocolos y procedimientos establecidos")
    trabajo_equipo = models.IntegerField(default=0, verbose_name="Trabajo en Equipo (0-100)", help_text="Colaboración, comunicación y trabajo conjunto")

    evaluador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='evaluaciones_realizadas', verbose_name="Evaluador")
    calificacion_general = models.IntegerField(verbose_name="Calificación General (0-100)", help_text="Promedio de las 5 métricas")
    notas_objetivas = models.TextField(verbose_name="Notas Objetivas", help_text="Evaluación detallada del desempeño")
    recomendacion = models.CharField(
        max_length=20,
        choices=[
            ('CONTRATAR', 'Contratar'),
            ('PRORROGAR', 'Prorrogar Periodo de Prueba'),
            ('NO_CONTRATAR', 'No Contratar'),
        ],
        verbose_name="Recomendación"
    )
    aptitud_medica = models.BooleanField(default=False, verbose_name="Dictamen de Aptitud Médica")

    pdf_firmado = models.FileField(
        upload_to='bitacoras_39a/',
        blank=True,
        null=True,
        verbose_name="PDF Firmado Digitalmente",
        help_text="PDF de evaluación firmado electrónicamente como respaldo legal",
        validators=[validate_document_upload],
    )
    hash_pdf = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name="Hash SHA-256 del PDF",
        help_text="Hash para verificación de integridad del PDF"
    )

    fecha_evaluacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Bitácora 39-A (Evaluación Semanal)"
        verbose_name_plural = "Bitácoras 39-A"
        ordering = ['-fecha_inicio']
        unique_together = ('empleado', 'periodo_semanal')

    def __str__(self):
        return f"Evaluación {self.periodo_semanal} - {self.empleado.usuario.get_full_name()}"

    def calcular_promedio(self):
        """Calcula el promedio de las 5 métricas."""
        total = (
            self.puntualidad +
            self.calidad_captura +
            self.atencion_cliente +
            self.cumplimiento_procesos +
            self.trabajo_equipo
        )
        return round(total / 5, 2) if total > 0 else 0

    def save(self, *args, **kwargs):
        """Calcula automáticamente la calificación general al guardar."""
        if not self.calificacion_general:
            self.calificacion_general = int(self.calcular_promedio())
        super().save(*args, **kwargs)


# ==============================================================================
# BLOQUE 3B: EVALUACIÓN DE DESEMPEÑO Y DESARROLLO DE TALENTO
# ==============================================================================
class Competencia(models.Model):
    """
    Competencias evaluables (Soft Skills y Hard Skills).

    DISEÑO: Catálogo global compartido entre todas las empresas.
    No tiene FK a Empresa por diseño — las competencias son transversales
    y se comparten para mantener consistencia en evaluaciones de desempeño.
    Solo superusuarios pueden crear/editar/eliminar competencias desde el admin.
    """
    TIPO_CHOICES = [
        ('BLANDA', 'Soft Skill (Competencia Blanda)'),
        ('TECNICA', 'Hard Skill (Competencia Técnica)'),
    ]

    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Competencia")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Competencia")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    activa = models.BooleanField(default=True, verbose_name="Competencia Activa")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Competencia"
        verbose_name_plural = "Competencias"
        ordering = ['tipo', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class EvaluacionDesempeno(models.Model):
    """Evaluación de desempeño completa con matriz 9-Box."""
    CUADRANTE_9BOX_CHOICES = [
        ('FUTURO_LIDER', 'Futuro Líder (Alto Potencial, Alto Desempeño)'),
        ('ESTRELLA', 'Estrella (Alto Potencial, Alto Desempeño)'),
        ('PERFORMER', 'Performer (Medio Potencial, Alto Desempeño)'),
        ('ENIGMA', 'Enigma (Alto Potencial, Bajo Desempeño)'),
        ('SOLIDO', 'Sólido (Medio Potencial, Medio Desempeño)'),
        ('EN_DESARROLLO', 'En Desarrollo (Medio Potencial, Bajo Desempeño)'),
        ('BAJO_RENDIMIENTO', 'Bajo Rendimiento (Bajo Potencial, Bajo Desempeño)'),
        ('DIVIDENDO', 'Dividendo (Bajo Potencial, Medio Desempeño)'),
        ('TRANSFERIR', 'Transferir (Bajo Potencial, Alto Desempeño)'),
    ]

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='evaluaciones_desempeno', verbose_name="Empleado Evaluado")
    evaluador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='evaluaciones_desempeno_realizadas', verbose_name="Evaluador")
    fecha = models.DateField(auto_now_add=True, verbose_name="Fecha de Evaluación")
    periodo = models.CharField(max_length=50, verbose_name="Periodo de Evaluación", help_text="Ej: Q1 2026, 2026-Enero")

    promedio_competencias = models.FloatField(default=0.0, verbose_name="Promedio Competencias (0-100)", help_text="Promedio de calificaciones de competencias")
    cumplimiento_kpis = models.FloatField(default=0.0, verbose_name="Cumplimiento KPIs (0-100)", help_text="Ventas, Errores, Métricas Objetivas")

    cuadrante_9box = models.CharField(max_length=50, choices=CUADRANTE_9BOX_CHOICES, blank=True, verbose_name="Cuadrante 9-Box")
    potencial_score = models.FloatField(default=0.0, verbose_name="Puntuación de Potencial (0-100)")
    desempeno_score = models.FloatField(default=0.0, verbose_name="Puntuación de Desempeño (0-100)")

    feedback_ia = models.TextField(blank=True, null=True, verbose_name="Feedback de IA", help_text="Resumen generado automáticamente por PRIS")
    observaciones_evaluador = models.TextField(blank=True, null=True, verbose_name="Observaciones del Evaluador")

    estado = models.CharField(
        max_length=20,
        choices=[
            ('BORRADOR', 'Borrador'),
            ('COMPLETADA', 'Completada'),
            ('REVISADA', 'Revisada por Empleado'),
        ],
        default='BORRADOR',
        verbose_name="Estado"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Evaluación de Desempeño"
        verbose_name_plural = "Evaluaciones de Desempeño"
        ordering = ['-fecha', '-fecha_creacion']

    def __str__(self):
        return f"Evaluación {self.periodo} - {self.empleado.usuario.get_full_name()}"

    def calcular_cuadrante_9box(self):
        """Calcula el cuadrante 9-Box basado en Potencial y Desempeño."""
        potencial = self.potencial_score
        desempeno = self.desempeno_score

        if desempeno >= 80 and potencial >= 80:
            return 'FUTURO_LIDER'
        elif desempeno >= 70 and potencial >= 70:
            return 'ESTRELLA'
        elif desempeno >= 70 and 50 <= potencial < 70:
            return 'PERFORMER'
        elif desempeno < 60 and potencial >= 70:
            return 'ENIGMA'
        elif 50 <= desempeno < 70 and 50 <= potencial < 70:
            return 'SOLIDO'
        elif desempeno < 60 and 50 <= potencial < 70:
            return 'EN_DESARROLLO'
        elif desempeno < 50 and potencial < 50:
            return 'BAJO_RENDIMIENTO'
        elif 50 <= desempeno < 70 and potencial < 50:
            return 'DIVIDENDO'
        elif desempeno >= 70 and potencial < 50:
            return 'TRANSFERIR'
        else:
            return 'SOLIDO'


class DetalleEvaluacion(models.Model):
    """Detalle de calificación por competencia en una evaluación."""
    evaluacion = models.ForeignKey(EvaluacionDesempeno, on_delete=models.CASCADE, related_name='detalles', verbose_name="Evaluación")
    competencia = models.ForeignKey(Competencia, on_delete=models.PROTECT, related_name='detalles_evaluaciones', verbose_name="Competencia")
    calificacion = models.IntegerField(verbose_name="Calificación (1-5)", help_text="1=Muy Bajo, 2=Bajo, 3=Medio, 4=Alto, 5=Muy Alto")
    observacion = models.TextField(blank=True, null=True, verbose_name="Observación")

    class Meta:
        app_label = 'core'
        verbose_name = "Detalle de Evaluación"
        verbose_name_plural = "Detalles de Evaluación"
        unique_together = ['evaluacion', 'competencia']

    def __str__(self):
        return f"{self.competencia.nombre}: {self.calificacion}/5"


class PlanDesarrollo(models.Model):
    """Plan de Desarrollo Individual (PDI) generado automáticamente desde evaluación."""
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('COMPLETADO', 'Completado'),
        ('VENCIDO', 'Vencido'),
    ]

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='planes_desarrollo', verbose_name="Empleado")
    evaluacion_origen = models.ForeignKey(EvaluacionDesempeno, on_delete=models.CASCADE, related_name='planes_desarrollo', verbose_name="Evaluación Origen")
    fecha_creacion = models.DateField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_limite = models.DateField(verbose_name="Fecha Límite", help_text="Fecha límite para completar el plan")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE', verbose_name="Estado")

    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    fecha_completado = models.DateField(blank=True, null=True, verbose_name="Fecha de Completado")

    class Meta:
        app_label = 'core'
        verbose_name = "Plan de Desarrollo Individual"
        verbose_name_plural = "Planes de Desarrollo Individual"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"PDI - {self.empleado.usuario.get_full_name()} ({self.evaluacion_origen.periodo})"

    def esta_vencido(self):
        """Verifica si el plan está vencido."""
        from django.utils import timezone
        return self.estado != 'COMPLETADO' and self.fecha_limite < timezone.now().date()


class RegistroAsistencia(models.Model):
    """Reloj checador digital con geolocalización/IP."""
    TIPO_ENTRADA = 'ENTRADA'
    TIPO_SALIDA = 'SALIDA'
    TIPO_BREAK_IN = 'BREAK_IN'
    TIPO_BREAK_OUT = 'BREAK_OUT'
    TIPO_CHOICES = [
        (TIPO_ENTRADA, 'Entrada'),
        (TIPO_SALIDA, 'Salida'),
        (TIPO_BREAK_IN, 'Inicio de Descanso'),
        (TIPO_BREAK_OUT, 'Fin de Descanso'),
    ]

    METODO_WEB = 'WEB'
    METODO_KIOSCO = 'KIOSCO'
    METODO_MOBILE = 'MOBILE'
    METODO_CHOICES = [
        (METODO_WEB, 'Web'),
        (METODO_KIOSCO, 'Kiosco'),
        (METODO_MOBILE, 'Móvil'),
    ]

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='registros_asistencia')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='asistencias')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sucursal")

    tipo_registro = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Registro")
    fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    metodo_registro = models.CharField(max_length=20, choices=METODO_CHOICES, default=METODO_WEB, verbose_name="Método de Registro")

    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="Dirección IP")
    ubicacion_gps = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ubicación GPS", help_text="Formato: lat,lng")

    class Meta:
        app_label = 'core'
        verbose_name = "Registro de Asistencia"
        verbose_name_plural = "Registros de Asistencia"
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"{self.empleado.usuario.get_full_name()} - {self.get_tipo_registro_display()} - {self.fecha_hora.strftime('%Y-%m-%d %H:%M')}"


# ==============================================================================
# BLOQUE: NÓMINA
# ==============================================================================
class PeriodoNomina(models.Model):
    """
    Período de nómina (quincena, semana, etc.).
    Actúa como encabezado de todo el proceso de pago.
    """
    FRECUENCIA_CHOICES = [
        ('SEMANAL',   'Semanal'),
        ('QUINCENAL', 'Quincenal'),
        ('MENSUAL',   'Mensual'),
    ]
    ESTADO_CHOICES = [
        ('ABIERTO',    'En captura'),
        ('CERRADO',    'Cerrado — en revisión'),
        ('PAGADO',     'Pagado'),
        ('CANCELADO',  'Cancelado'),
    ]

    empresa    = models.ForeignKey(Empresa,  on_delete=models.PROTECT, related_name='periodos_nomina', verbose_name="Empresa")
    sucursal   = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Sucursal")
    nombre     = models.CharField(max_length=100, verbose_name="Nombre del período", help_text="Ej: Quincena 1 — Febrero 2026")
    frecuencia = models.CharField(max_length=15, choices=FRECUENCIA_CHOICES, default='QUINCENAL', verbose_name="Frecuencia de pago")
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    fecha_fin    = models.DateField(verbose_name="Fecha de fin")
    fecha_pago   = models.DateField(null=True, blank=True, verbose_name="Fecha de pago")
    estado       = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='ABIERTO', verbose_name="Estado")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    creado_por   = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Creado por")
    creado       = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Período de Nómina'
        verbose_name_plural = 'Períodos de Nómina'
        ordering = ['-fecha_inicio']
        unique_together = [('empresa', 'nombre')]

    def __str__(self):
        return f"{self.nombre} ({self.get_frecuencia_display()}) — {self.get_estado_display()}"

    @property
    def total_neto(self):
        from django.db.models import Sum
        return self.recibos.aggregate(t=Sum('neto_pagar'))['t'] or 0


class ReciboNomina(models.Model):
    """
    Recibo individual de nómina por empleado y período.
    Registra percepciones, deducciones e IMSS.
    """
    periodo   = models.ForeignKey(PeriodoNomina, on_delete=models.CASCADE, related_name='recibos', verbose_name="Período")
    empleado  = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name='recibos_nomina', verbose_name="Empleado")
    empresa   = models.ForeignKey(Empresa,  on_delete=models.PROTECT, verbose_name="Empresa")

    # Percepciones
    sueldo_base       = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Sueldo base")
    horas_extra       = models.DecimalField(max_digits=5,  decimal_places=2, default=0, verbose_name="Horas extra")
    importe_he        = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Importe horas extra")
    bonificacion      = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Bonificación / comisión")
    percepciones_extras = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Otras percepciones")
    total_percepciones = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total de percepciones")

    # Deducciones
    imss         = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cuota IMSS trabajador")
    isr          = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="ISR retenido")
    infonavit    = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="INFONAVIT")
    prestamo     = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Descuento por préstamo")
    otras_deducciones = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Otras deducciones")
    total_deducciones = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total de deducciones")

    # Neto
    neto_pagar = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Neto a pagar")

    # Estado
    pagado      = models.BooleanField(default=False, verbose_name="Pagado")
    fecha_pago  = models.DateField(null=True, blank=True, verbose_name="Fecha de pago efectivo")
    metodo_pago = models.CharField(max_length=30, blank=True, verbose_name="Método de pago",
                                   help_text="EFECTIVO, TRANSFERENCIA, CHEQUE")
    referencia_pago = models.CharField(max_length=100, blank=True, verbose_name="Referencia / folio de transferencia")

    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    creado        = models.DateTimeField(auto_now_add=True)
    actualizado   = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Recibo de Nómina'
        verbose_name_plural = 'Recibos de Nómina'
        ordering = ['-periodo__fecha_inicio', 'empleado']
        unique_together = [('periodo', 'empleado')]

    def __str__(self):
        return f"Recibo {self.periodo.nombre} — {self.empleado.usuario.get_full_name()}"

    def calcular_totales(self):
        """Recalcula totales de percepciones, deducciones y neto."""
        from decimal import Decimal
        self.total_percepciones = (
            self.sueldo_base + self.importe_he +
            self.bonificacion + self.percepciones_extras
        )
        self.total_deducciones = (
            self.imss + self.isr + self.infonavit +
            self.prestamo + self.otras_deducciones
        )
        self.neto_pagar = self.total_percepciones - self.total_deducciones
        return self

    def save(self, *args, **kwargs):
        self.calcular_totales()
        super().save(*args, **kwargs)


# ==============================================================================
# BLOQUE: HORARIOS Y CONTROL DE ASISTENCIA
# ==============================================================================
class HorarioTrabajo(models.Model):
    """Define el horario laboral de un empleado o grupo."""
    DIA_CHOICES = [
        ('LUN', 'Lunes'), ('MAR', 'Martes'), ('MIE', 'Miércoles'),
        ('JUE', 'Jueves'), ('VIE', 'Viernes'), ('SAB', 'Sábado'), ('DOM', 'Domingo'),
    ]

    empresa     = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='horarios_trabajo')
    empleado    = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='horarios', null=True, blank=True,
                                    help_text="Dejar vacío para horario general del departamento")
    nombre      = models.CharField(max_length=100, verbose_name="Nombre del turno",
                                    help_text="Ej: Turno Matutino, Guardia Nocturna")
    dia_semana  = models.CharField(max_length=3, choices=DIA_CHOICES, verbose_name="Día de la semana")
    hora_entrada = models.TimeField(verbose_name="Hora de entrada")
    hora_salida  = models.TimeField(verbose_name="Hora de salida")
    tolerancia_minutos = models.PositiveSmallIntegerField(default=10, verbose_name="Tolerancia (minutos)")
    activo      = models.BooleanField(default=True)
    creado      = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Horario de Trabajo'
        verbose_name_plural = 'Horarios de Trabajo'
        ordering = ['dia_semana', 'hora_entrada']
        indexes = [models.Index(fields=['empresa', 'activo'])]

    def __str__(self):
        empleado_str = self.empleado.usuario.get_full_name() if self.empleado else 'General'
        return f"{self.nombre} — {self.get_dia_semana_display()} ({empleado_str})"


class IncidenciaAsistencia(models.Model):
    """Registro de incidencias laborales: faltas, permisos, vacaciones, retardos."""
    TIPO_CHOICES = [
        ('FALTA',       'Falta'),
        ('RETARDO',     'Retardo'),
        ('PERMISO',     'Permiso con goce'),
        ('PERMISO_SG',  'Permiso sin goce'),
        ('VACACIONES',  'Vacaciones'),
        ('INCAPACIDAD', 'Incapacidad médica'),
        ('OTRO',        'Otro'),
    ]
    ESTADO_CHOICES = [
        ('PENDIENTE',  'Pendiente'),
        ('AUTORIZADA', 'Autorizada'),
        ('RECHAZADA',  'Rechazada'),
    ]

    empresa    = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='incidencias_asistencia')
    empleado   = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='incidencias')
    tipo       = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de incidencia")
    estado     = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PENDIENTE')
    fecha_inicio = models.DateField(verbose_name="Fecha inicio")
    fecha_fin    = models.DateField(verbose_name="Fecha fin")
    dias         = models.PositiveSmallIntegerField(default=1, verbose_name="Días")
    motivo       = models.TextField(blank=True, verbose_name="Motivo / justificación")
    documento_soporte = models.FileField(upload_to='incidencias/', null=True, blank=True,
                                          verbose_name="Documento de soporte")
    autorizado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='incidencias_autorizadas')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    observaciones   = models.TextField(blank=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Incidencia de Asistencia'
        verbose_name_plural = 'Incidencias de Asistencia'
        ordering = ['-fecha_solicitud']
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['empleado', '-fecha_inicio']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.empleado.usuario.get_full_name()} ({self.fecha_inicio})"

    def save(self, *args, **kwargs):
        if self.fecha_inicio and self.fecha_fin:
            self.dias = (self.fecha_fin - self.fecha_inicio).days + 1
        if self.estado != 'PENDIENTE' and not self.fecha_resolucion:
            from django.utils import timezone as tz
            self.fecha_resolucion = tz.now()
        super().save(*args, **kwargs)
