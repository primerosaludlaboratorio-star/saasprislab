"""
core/models/clinico.py
Módulo clínico: ConsultaMedica, Receta, CertificadoMedico, SignosVitales,
Historia Clínica, Notas SOAP, Imágenes, Consentimientos.
Depende de: base.py, catalogos.py, pacientes.py, ventas.py (Receta), laboratorio.py (OrdenDeServicio)
FKs cruzados usan string references.
"""
from django.db import models
import uuid

from core.validators import validate_image_upload, validate_audio_upload, validate_document_upload
from .base import Empresa, Sucursal, Usuario, get_google_drive_storage


# ==============================================================================
# MÓDULO CONSULTORIO MÉDICO (NOM-004-SSA3-2012)
# ==============================================================================
class CitaMedica(models.Model):
    """Sistema de Agendamiento de Citas Médicas."""
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADA', 'Confirmada'),
        ('EN_SALA', 'En Sala de Espera'),
        ('EN_CURSO', 'En Consulta'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
        ('NO_ASISTIO', 'No Asistió'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True)
    paciente = models.ForeignKey('Paciente', on_delete=models.PROTECT, related_name='citas')
    medico = models.ForeignKey('Medico', on_delete=models.SET_NULL, null=True, blank=True, related_name='citas')

    fecha_cita = models.DateField(verbose_name="Fecha de la Cita")
    hora_cita = models.TimeField(verbose_name="Hora de la Cita")
    duracion_estimada = models.IntegerField(default=30, verbose_name="Duración (minutos)")

    motivo = models.TextField(verbose_name="Motivo de la Cita")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')

    notas_paciente = models.TextField(null=True, blank=True, verbose_name="Notas del Paciente")
    notas_recepcion = models.TextField(null=True, blank=True, verbose_name="Notas de Recepción")

    recordatorio_enviado = models.BooleanField(default=False)
    fecha_recordatorio = models.DateTimeField(null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='citas_creadas')
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Cita Médica'
        verbose_name_plural = 'Citas Médicas'
        ordering = ['fecha_cita', 'hora_cita']
        indexes = [
            models.Index(fields=['fecha_cita', 'medico']),
            models.Index(fields=['estado']),
            models.Index(fields=['empresa', 'fecha_cita'], name='core_cita_emp_fecha_idx'),
            models.Index(fields=['empresa', 'estado'], name='core_cita_emp_estado_idx'),
            models.Index(fields=['paciente', 'fecha_cita'], name='core_cita_pac_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.paciente.nombre_completo} - {self.fecha_cita} {self.hora_cita}"

    @property
    def hora_fin_estimada(self):
        """Calcula la hora de finalización estimada."""
        from datetime import datetime, timedelta
        dt = datetime.combine(self.fecha_cita, self.hora_cita)
        dt_fin = dt + timedelta(minutes=self.duracion_estimada)
        return dt_fin.time()


class HistoriaClinica(models.Model):
    """Historia Clínica del Paciente (NOM-004-SSA3-2012)."""
    FRECUENCIA_CHOICES = [
        ('NUNCA', 'Nunca'),
        ('OCASIONAL', 'Ocasional'),
        ('FRECUENTE', 'Frecuente'),
        ('DIARIO', 'Diario'),
    ]

    ACTIVIDAD_CHOICES = [
        ('SEDENTARIO', 'Sedentario'),
        ('LIGERA', 'Actividad Ligera'),
        ('MODERADA', 'Actividad Moderada'),
        ('INTENSA', 'Actividad Intensa'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    paciente = models.OneToOneField('Paciente', on_delete=models.PROTECT, related_name='historia_clinica')
    numero_expediente = models.CharField(max_length=50, verbose_name="Número de Expediente")

    ahf_diabetes = models.BooleanField(default=False, verbose_name="Diabetes")
    ahf_hipertension = models.BooleanField(default=False, verbose_name="Hipertensión")
    ahf_cancer = models.BooleanField(default=False, verbose_name="Cáncer")
    ahf_cardiopatias = models.BooleanField(default=False, verbose_name="Cardiopatías")
    ahf_otros = models.TextField(blank=True, verbose_name="Otros Antecedentes Familiares")

    apnp_tabaquismo = models.CharField(max_length=20, choices=FRECUENCIA_CHOICES, default='NUNCA', verbose_name="Tabaquismo")
    apnp_alcoholismo = models.CharField(max_length=20, choices=FRECUENCIA_CHOICES, default='NUNCA', verbose_name="Alcoholismo")
    apnp_drogas = models.CharField(max_length=20, choices=FRECUENCIA_CHOICES, default='NUNCA', verbose_name="Uso de Drogas")
    apnp_actividad_fisica = models.CharField(max_length=20, choices=ACTIVIDAD_CHOICES, default='SEDENTARIO', verbose_name="Actividad Física")
    apnp_alimentacion = models.TextField(blank=True, verbose_name="Hábitos Alimentarios")

    app_cirugias_previas = models.TextField(blank=True, verbose_name="Cirugías Previas")
    app_hospitalizaciones = models.TextField(blank=True, verbose_name="Hospitalizaciones")
    app_transfusiones = models.TextField(blank=True, verbose_name="Transfusiones")
    app_alergias = models.TextField(blank=True, verbose_name="Alergias (CRÍTICO)")
    app_enfermedades_cronicas = models.TextField(blank=True, verbose_name="Enfermedades Crónicas")

    ago_menarca = models.IntegerField(null=True, blank=True, verbose_name="Edad de Menarca")
    ago_gestas = models.IntegerField(null=True, blank=True, verbose_name="Gestas")
    ago_partos = models.IntegerField(null=True, blank=True, verbose_name="Partos")
    ago_cesareas = models.IntegerField(null=True, blank=True, verbose_name="Cesáreas")
    ago_abortos = models.IntegerField(null=True, blank=True, verbose_name="Abortos")
    ago_fum = models.DateField(null=True, blank=True, verbose_name="Fecha Última Menstruación")
    ago_metodo_planificacion = models.CharField(max_length=200, blank=True, verbose_name="Método de Planificación")

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='historias_creadas')
    fecha_modificacion = models.DateTimeField(auto_now=True)
    modificado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='historias_modificadas')

    class Meta:
        app_label = 'core'
        verbose_name = 'Historia Clínica'
        verbose_name_plural = 'Historias Clínicas'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'numero_expediente'],
                name='historia_clinica_empresa_expediente_unique',
            ),
        ]

    def __str__(self):
        return f"HC-{self.numero_expediente} - {self.paciente.nombre_completo}"

    def save(self, *args, **kwargs):
        if not self.numero_expediente:
            from datetime import datetime
            año = datetime.now().year
            ultimos = HistoriaClinica.objects.filter(
                empresa=self.empresa,
                numero_expediente__startswith=f'HC-{año}-'
            ).count()
            self.numero_expediente = f'HC-{año}-{str(ultimos + 1).zfill(5)}'
        super().save(*args, **kwargs)


class SignosVitales(models.Model):
    """Registro de Signos Vitales (NOM-004-SSA3-2012)."""
    paciente = models.ForeignKey('Paciente', on_delete=models.PROTECT, related_name='signos_vitales')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cita = models.OneToOneField(CitaMedica, on_delete=models.SET_NULL, null=True, blank=True, related_name='signos_vitales')

    presion_arterial_sistolica = models.IntegerField(null=True, blank=True, verbose_name="PA Sistólica (mmHg)")
    presion_arterial_diastolica = models.IntegerField(null=True, blank=True, verbose_name="PA Diastólica (mmHg)")
    frecuencia_cardiaca = models.IntegerField(null=True, blank=True, verbose_name="Frecuencia Cardíaca (lat/min)")
    frecuencia_respiratoria = models.IntegerField(null=True, blank=True, verbose_name="Frecuencia Respiratoria (resp/min)")
    temperatura = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="Temperatura (°C)")

    peso = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Peso (kg)")
    talla = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="Talla (m)")
    imc = models.DecimalField(max_digits=5, decimal_places=2, editable=False, null=True, verbose_name="IMC (kg/m²)")
    perimetro_abdominal = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Perímetro Abdominal (cm)")

    saturacion_oxigeno = models.IntegerField(null=True, blank=True, verbose_name="SpO₂ (%)")
    glucosa_capilar = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Glucosa Capilar (mg/dL)")

    observaciones = models.TextField(blank=True, verbose_name="Observaciones")

    fecha_registro = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='signos_registrados')

    class Meta:
        app_label = 'core'
        verbose_name = 'Signos Vitales'
        verbose_name_plural = 'Registros de Signos Vitales'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.paciente.nombre_completo} - {self.fecha_registro.strftime('%d/%m/%Y %H:%M')}"

    def save(self, *args, **kwargs):
        if self.peso and self.talla and self.talla > 0:
            self.imc = self.peso / (self.talla ** 2)
        super().save(*args, **kwargs)

    @property
    def clasificacion_imc(self):
        """Clasificación del IMC según OMS."""
        if not self.imc:
            return "No calculado"
        if self.imc < 18.5:
            return "Bajo peso"
        elif 18.5 <= self.imc < 25:
            return "Normal"
        elif 25 <= self.imc < 30:
            return "Sobrepeso"
        elif 30 <= self.imc < 35:
            return "Obesidad Grado I"
        elif 35 <= self.imc < 40:
            return "Obesidad Grado II"
        else:
            return "Obesidad Grado III (Mórbida)"

    @property
    def presion_arterial(self):
        """Retorna PA en formato estándar."""
        return f"{self.presion_arterial_sistolica}/{self.presion_arterial_diastolica}"


class ConsultaMedica(models.Model):
    """Consulta Médica con Formato SOAP (NOM-004-SSA3-2012)."""
    ESTADO_CHOICES = [
        ('EN_CURSO', 'En Curso'),
        ('FINALIZADA', 'Finalizada'),
        ('CANCELADA', 'Cancelada'),
    ]

    TIPO_CONSULTA_CHOICES = [
        ('PRIMERA_VEZ', 'Primera Vez'),
        ('SUBSECUENTE', 'Subsecuente'),
        ('URGENCIA', 'Urgencia'),
    ]

    PRONOSTICO_CHOICES = [
        ('EXCELENTE', 'Excelente'),
        ('BUENO', 'Bueno'),
        ('REGULAR', 'Regular'),
        ('RESERVADO', 'Reservado'),
        ('MALO', 'Malo'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True)
    paciente = models.ForeignKey('Paciente', on_delete=models.PROTECT, related_name='consultas')
    medico = models.ForeignKey('Medico', on_delete=models.SET_NULL, null=True, blank=True, related_name='consultas')
    historia_clinica = models.ForeignKey(HistoriaClinica, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultas')

    folio_consulta = models.CharField(max_length=50, unique=True, verbose_name="Folio de Consulta")
    fecha_consulta = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora de Consulta")
    tipo_consulta = models.CharField(max_length=20, choices=TIPO_CONSULTA_CHOICES, default='SUBSECUENTE')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='EN_CURSO')

    cita = models.OneToOneField(CitaMedica, on_delete=models.SET_NULL, null=True, blank=True, related_name='consulta')
    signos_vitales = models.ForeignKey(SignosVitales, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultas')

    motivo_consulta = models.TextField(verbose_name="Motivo de Consulta")
    padecimiento_actual = models.TextField(verbose_name="Padecimiento Actual")

    exploracion_fisica = models.TextField(verbose_name="Exploración Física")

    diagnostico_principal = models.CharField(max_length=500, verbose_name="Diagnóstico Principal")
    diagnostico_cie10 = models.CharField(max_length=20, null=True, blank=True, verbose_name="Código CIE-10")
    diagnosticos_secundarios = models.TextField(null=True, blank=True, verbose_name="Diagnósticos Secundarios")

    plan_tratamiento = models.TextField(verbose_name="Plan de Tratamiento")
    estudios_solicitados = models.TextField(null=True, blank=True, verbose_name="Estudios Solicitados")
    pronostico = models.CharField(max_length=20, choices=PRONOSTICO_CHOICES, default='BUENO')
    fecha_proxima_cita = models.DateField(null=True, blank=True, verbose_name="Próxima Cita")

    receta = models.OneToOneField('Receta', on_delete=models.SET_NULL, null=True, blank=True, related_name='consulta')

    precio_consulta = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Precio de Consulta")
    pagada = models.BooleanField(default=False, verbose_name="Pagada")

    transcripcion_completa = models.TextField(
        null=True, blank=True,
        verbose_name="Transcripción Completa (Audio a Texto)",
        help_text="Transcripción generada por IA del audio de la consulta. Respaldo legal NOM-004."
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Consulta Médica'
        verbose_name_plural = 'Consultas Médicas'
        ordering = ['-fecha_consulta']
        permissions = [
            ('ver_historia_completa', 'Puede ver historia clínica completa'),
            ('generar_certificado', 'Puede generar certificados médicos'),
        ]
        indexes = [
            models.Index(fields=['empresa', 'fecha_consulta'], name='core_cons_emp_fecha_idx'),
            models.Index(fields=['empresa', 'estado'], name='core_cons_emp_estado_idx'),
            models.Index(fields=['paciente', 'fecha_consulta'], name='core_cons_pac_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.folio_consulta} - {self.paciente.nombre_completo} - {self.fecha_consulta.strftime('%d/%m/%Y')}"

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.estado == 'FINALIZADA' and not self.diagnostico_cie10:
            raise ValidationError({
                'diagnostico_cie10': 'No se puede finalizar una consulta sin un diagnóstico CIE-10.'
            })

    def save(self, *args, **kwargs):
        if self.estado == 'FINALIZADA':
            self.full_clean()
        if not self.folio_consulta:
            from datetime import datetime
            año = datetime.now().year
            # Prefijo incluye empresa_id para garantizar unicidad multi-tenant
            prefijo = f'CONS-{self.empresa_id}-{año}-'
            ultimas = ConsultaMedica.objects.filter(
                empresa=self.empresa,
                folio_consulta__startswith=prefijo
            ).count()
            self.folio_consulta = f'{prefijo}{str(ultimas + 1).zfill(5)}'
        if not self.historia_clinica and hasattr(self.paciente, 'historia_clinica'):
            self.historia_clinica = self.paciente.historia_clinica
        super().save(*args, **kwargs)


class CertificadoMedico(models.Model):
    """Certificados Médicos (Incapacidad, Aptitud, etc.). NOM-004-SSA3-2012."""
    TIPO_CHOICES = [
        ('INCAPACIDAD', 'Certificado de Incapacidad'),
        ('APTITUD', 'Certificado de Aptitud Física'),
        ('DEFUNCION', 'Certificado de Defunción'),
        ('NACIMIENTO', 'Certificado de Nacimiento'),
        ('SALUD', 'Certificado de Buena Salud'),
        ('OTRO', 'Otro'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    paciente = models.ForeignKey('Paciente', on_delete=models.PROTECT, related_name='certificados')
    medico = models.ForeignKey('Medico', on_delete=models.SET_NULL, null=True, blank=True, related_name='certificados')
    consulta = models.ForeignKey(ConsultaMedica, on_delete=models.SET_NULL, null=True, blank=True, related_name='certificados')

    folio_certificado = models.CharField(max_length=50, unique=True, verbose_name="Folio del Certificado")
    tipo_certificado = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Certificado")

    diagnostico = models.CharField(max_length=500, verbose_name="Diagnóstico")
    descripcion = models.TextField(verbose_name="Descripción del Certificado")
    dias_incapacidad = models.IntegerField(null=True, blank=True, verbose_name="Días de Incapacidad")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha de Fin")

    firma_digital = models.ImageField(upload_to='firmas_certificados/', null=True, blank=True, validators=[validate_image_upload])
    qr_verificacion = models.TextField(blank=True, verbose_name="Código QR de Verificación")
    token_verificacion = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    fecha_emision = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Certificado Médico'
        verbose_name_plural = 'Certificados Médicos'
        ordering = ['-fecha_emision']
        permissions = [
            ('emitir_certificado_defuncion', 'Puede emitir certificados de defunción'),
        ]

    def __str__(self):
        return f"{self.folio_certificado} - {self.get_tipo_certificado_display()}"

    def save(self, *args, **kwargs):
        if not self.folio_certificado:
            from datetime import datetime
            año = datetime.now().year
            tipo_corto = self.tipo_certificado[:3].upper()
            # Prefijo incluye empresa_id para garantizar unicidad multi-tenant
            prefijo = f'CERT-{self.empresa_id}-{tipo_corto}-{año}-'
            ultimos = CertificadoMedico.objects.filter(
                empresa=self.empresa,
                tipo_certificado=self.tipo_certificado,
                folio_certificado__startswith=prefijo
            ).count()
            self.folio_certificado = f'{prefijo}{str(ultimos + 1).zfill(5)}'
        super().save(*args, **kwargs)


# ==============================================================================
# BLOQUE 4: MÓDULO MÉDICO Y EXPEDIENTE CLÍNICO ELECTRÓNICO (ECE)
# ==============================================================================
class NotaClinicaSOAP(models.Model):
    """Nota clínica estructurada SOAP."""
    paciente = models.ForeignKey('Paciente', on_delete=models.PROTECT, related_name='notas_clinicas')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='notas_clinicas')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sucursal")
    medico = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='notas_clinicas_realizadas', verbose_name="Médico")

    fecha_consulta = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Consulta")

    subjetivo = models.TextField(verbose_name="Subjetivo", help_text="Lo que el paciente reporta")
    objetivo = models.TextField(verbose_name="Objetivo", help_text="Hallazgos físicos y exploración")
    analisis = models.TextField(verbose_name="Análisis", help_text="Diagnóstico o impresión diagnóstica")
    plan = models.TextField(verbose_name="Plan", help_text="Plan de tratamiento")

    archivos_adjuntos = models.JSONField(default=list, blank=True, verbose_name="Archivos Adjuntos", help_text="IDs de imágenes/documentos")
    signos_vitales_snapshot = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Snapshot signos vitales (triage)",
        help_text="JSON inmutable enlazado a la cadena SHA del expediente (H-009).",
    )
    diagnostico_principal = models.CharField(max_length=200, blank=True)
    diagnosticos_secundarios = models.TextField(blank=True)
    creado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='notas_creadas_soap', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultima_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Nota Clínica SOAP"
        verbose_name_plural = "Notas Clínicas SOAP"
        ordering = ['-fecha_consulta']

    def __str__(self):
        return f"Nota SOAP - {self.paciente.nombre_completo} - {self.fecha_consulta.strftime('%Y-%m-%d')}"


class PlantillaNotaClinica(models.Model):
    """Catálogo de plantillas predefinidas para notas clínicas."""
    nombre = models.CharField(max_length=150, verbose_name="Nombre de la Plantilla", help_text="Ej: 'Diabetes Tipo 2 - Rutina', 'Faringitis Común'")
    descripcion = models.TextField(blank=True, verbose_name="Descripción", help_text="Cuándo usar esta plantilla")

    subjetivo = models.TextField(verbose_name="Subjetivo (Plantilla)", help_text="Texto predefinido para síntomas comunes")
    objetivo = models.TextField(verbose_name="Objetivo (Plantilla)", help_text="Texto predefinido para hallazgos físicos")
    analisis = models.TextField(verbose_name="Análisis (Plantilla)", help_text="Texto predefinido para diagnóstico")
    plan = models.TextField(verbose_name="Plan (Plantilla)", help_text="Texto predefinido para tratamiento")

    es_publica = models.BooleanField(default=False, verbose_name="Plantilla Pública", help_text="Si es True, todos los médicos pueden usarla. Si es False, solo el creador.")
    creado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='plantillas_creadas', verbose_name="Médico Creador")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='plantillas_notas', verbose_name="Empresa")

    especialidad = models.CharField(max_length=150, blank=True, default='', verbose_name="Especialidad", help_text="Ej: Pediatría, Ginecología, General. Vacío = disponible para todos.")

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)
    veces_usada = models.IntegerField(default=0, verbose_name="Contador de Uso", help_text="Se incrementa cada vez que se aplica")

    class Meta:
        app_label = 'core'
        verbose_name = "Plantilla de Nota Clínica"
        verbose_name_plural = "Plantillas de Notas Clínicas (Catálogo)"
        ordering = ['-veces_usada', 'nombre']
        indexes = [
            models.Index(fields=['empresa', 'es_publica', 'activa']),
            models.Index(fields=['creado_por', '-veces_usada']),
        ]

    def __str__(self):
        return f"{self.nombre} ({'Pública' if self.es_publica else 'Privada'})"


class Antecedente(models.Model):
    """Antecedentes médicos del paciente."""
    TIPO_HEREDOFAMILIAR = 'HEREDOFAMILIAR'
    TIPO_PERSONAL_PATOLOGICO = 'PERSONAL_PATOLOGICO'
    TIPO_PERSONAL_NO_PATOLOGICO = 'PERSONAL_NO_PATOLOGICO'
    TIPO_CHOICES = [
        (TIPO_HEREDOFAMILIAR, 'Heredofamiliar'),
        (TIPO_PERSONAL_PATOLOGICO, 'Personal Patológico'),
        (TIPO_PERSONAL_NO_PATOLOGICO, 'Personal No Patológico'),
    ]

    paciente = models.ForeignKey('Paciente', on_delete=models.PROTECT, related_name='antecedentes')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, verbose_name="Tipo de Antecedente")
    descripcion = models.TextField(verbose_name="Descripción")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = "Antecedente"
        verbose_name_plural = "Antecedentes"
        ordering = ['tipo', '-fecha_registro']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.paciente.nombre_completo}"


class FirmaDigital(models.Model):
    """Firma digital del médico con cédula profesional."""
    medico = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='firmas_digitales', verbose_name="Médico")
    cedula_profesional = models.CharField(max_length=50, verbose_name="Cédula Profesional")
    imagen_firma = models.ImageField(upload_to='firmas/', verbose_name="Imagen de la Firma", validators=[validate_image_upload])
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True, verbose_name="Firma Activa")

    class Meta:
        app_label = 'core'
        verbose_name = "Firma Digital"
        verbose_name_plural = "Firmas Digitales"
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"Firma - {self.medico.get_full_name()} - {self.cedula_profesional}"


# ==============================================================================
# EXTENSIONES FORENSES (CAJA NEGRA CLÍNICA)
# ==============================================================================
class AudioConsulta(models.Model):
    """Grabación de audio de la sesión médica (Caja Negra)."""
    consulta = models.OneToOneField(ConsultaMedica, on_delete=models.CASCADE, related_name='audio_sesion')
    audio_archivo = models.FileField(
        upload_to='core.utils.paths.generar_ruta_drive_audio_forense',
        storage=get_google_drive_storage,
        verbose_name="Archivo de Audio",
        help_text="Audio de consulta médica almacenado en Google Drive con trazabilidad forense",
        validators=[validate_audio_upload],
    )
    duracion_segundos = models.IntegerField(verbose_name="Duración (segundos)")
    formato = models.CharField(max_length=10, default='wav', verbose_name="Formato")
    tamano_bytes = models.BigIntegerField(verbose_name="Tamaño (bytes)")

    hash_sha256 = models.CharField(max_length=64, unique=True, verbose_name="Hash SHA256")
    timestamp_inicio = models.DateTimeField(verbose_name="Inicio de Grabación")
    timestamp_fin = models.DateTimeField(verbose_name="Fin de Grabación")

    transcripcion_bruta = models.TextField(blank=True, verbose_name="Transcripción Automática")
    transcripcion_editada = models.TextField(blank=True, verbose_name="Transcripción Editada")
    transcripcion_procesada = models.BooleanField(default=False)

    navegador = models.CharField(max_length=200, blank=True)
    ip_origen = models.GenericIPAddressField(null=True)

    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Audio de Consulta'
        verbose_name_plural = 'Audios de Consultas'
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"Audio: {self.consulta.folio_consulta} - {self.duracion_segundos}s"

    @property
    def duracion_formato(self):
        """Retorna duración en formato MM:SS"""
        minutos = self.duracion_segundos // 60
        segundos = self.duracion_segundos % 60
        return f"{minutos:02d}:{segundos:02d}"


# ==============================================================================
# MÓDULO DE IMAGENOLOGÍA (ULTRASONIDO, RAYOS X)
# ==============================================================================
class EstudioImagen(models.Model):
    """Estudios de Imagenología (Ultrasonido, Rayos X, etc.)."""
    TIPO_ESTUDIO_CHOICES = [
        ('USG_ABDOMINAL', 'Ultrasonido Abdominal'),
        ('USG_PELVICO', 'Ultrasonido Pélvico'),
        ('USG_OBSTETRICO', 'Ultrasonido Obstétrico'),
        ('USG_MAMARIO', 'Ultrasonido Mamario'),
        ('USG_TIROIDES', 'Ultrasonido de Tiroides'),
        ('USG_HEPATICO', 'Ultrasonido Hepático'),
        ('USG_RENAL', 'Ultrasonido Renal'),
        ('USG_MUSCULO', 'Ultrasonido Músculo-Esquelético'),
        ('RAYOS_X_TORAX', 'Rayos X de Tórax'),
        ('RAYOS_X_ABDOMEN', 'Rayos X de Abdomen'),
        ('RAYOS_X_HUESOS', 'Rayos X Óseo'),
        ('OTRO', 'Otro'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    paciente = models.ForeignKey('Paciente', on_delete=models.PROTECT, related_name='estudios_imagen')
    consulta = models.ForeignKey(ConsultaMedica, on_delete=models.SET_NULL, null=True, blank=True, related_name='estudios_imagen')
    medico_interpretador = models.ForeignKey('Medico', on_delete=models.SET_NULL, null=True, related_name='estudios_interpretados')

    folio_estudio = models.CharField(max_length=50, unique=True, verbose_name="Folio del Estudio")
    tipo_estudio = models.CharField(max_length=30, choices=TIPO_ESTUDIO_CHOICES, verbose_name="Tipo de Estudio")
    fecha_estudio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha del Estudio")

    edad_paciente = models.IntegerField(verbose_name="Edad")
    peso_actual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    indicacion_clinica = models.TextField(verbose_name="Indicación Clínica")
    antecedentes_relevantes = models.TextField(blank=True, verbose_name="Antecedentes Relevantes")

    tecnica_utilizada = models.TextField(blank=True, verbose_name="Técnica Utilizada")
    equipo_utilizado = models.CharField(max_length=200, blank=True, verbose_name="Equipo")

    descripcion_hallazgos = models.TextField(verbose_name="Descripción de Hallazgos")
    interpretacion = models.TextField(verbose_name="Interpretación")
    conclusiones = models.TextField(verbose_name="Conclusiones")

    recomendaciones = models.TextField(blank=True, verbose_name="Recomendaciones")
    estudios_complementarios = models.TextField(blank=True, verbose_name="Estudios Complementarios Sugeridos")

    estado = models.CharField(max_length=20, choices=[
        ('BORRADOR', 'Borrador'),
        ('INTERPRETADO', 'Interpretado'),
        ('VALIDADO', 'Validado'),
        ('ENTREGADO', 'Entregado'),
    ], default='BORRADOR')

    validado_por = models.ForeignKey('Medico', on_delete=models.SET_NULL, null=True, blank=True, related_name='estudios_validados')
    fecha_validacion = models.DateTimeField(null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='estudios_creados')

    class Meta:
        app_label = 'core'
        verbose_name = 'Estudio de Imagen'
        verbose_name_plural = 'Estudios de Imagen'
        ordering = ['-fecha_estudio']
        permissions = [
            ('interpretar_estudios', 'Puede interpretar estudios de imagen'),
            ('validar_estudios', 'Puede validar estudios de imagen'),
        ]

    def __str__(self):
        return f"{self.folio_estudio} - {self.get_tipo_estudio_display()} - {self.paciente.nombre_completo}"

    def save(self, *args, **kwargs):
        if not self.folio_estudio:
            from datetime import datetime
            año = datetime.now().year
            tipo_corto = self.tipo_estudio.split('_')[0][:3].upper()
            ultimos = EstudioImagen.objects.filter(
                empresa=self.empresa,
                folio_estudio__startswith=f'IMG-{tipo_corto}-{año}-'
            ).count()
            self.folio_estudio = f'IMG-{tipo_corto}-{año}-{str(ultimos + 1).zfill(5)}'
        if not self.edad_paciente:
            self.edad_paciente = self.paciente.edad
        super().save(*args, **kwargs)


class ImagenDetalle(models.Model):
    """Imágenes individuales asociadas a un estudio de imagenología."""
    estudio = models.ForeignKey(EstudioImagen, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(
        upload_to='core.utils.paths.generar_ruta_drive',
        storage=get_google_drive_storage,
        verbose_name="Imagen",
        help_text="Imagen de estudio diagnóstico almacenada en Google Drive",
        validators=[validate_image_upload],
    )
    orden = models.IntegerField(default=1, verbose_name="Orden")
    descripcion = models.CharField(max_length=200, blank=True, verbose_name="Descripción")

    ancho = models.IntegerField(null=True, blank=True)
    alto = models.IntegerField(null=True, blank=True)
    tamano_bytes = models.IntegerField(null=True, blank=True)

    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Imagen de Estudio'
        verbose_name_plural = 'Imágenes de Estudios'
        ordering = ['estudio', 'orden']

    def __str__(self):
        return f"Imagen {self.orden} - {self.estudio.folio_estudio}"


class PlantillaEstudioImagen(models.Model):
    """Plantillas predefinidas para agilizar la interpretación de estudios."""
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la Plantilla")
    tipo_estudio = models.CharField(max_length=30, choices=EstudioImagen.TIPO_ESTUDIO_CHOICES, verbose_name="Tipo de Estudio")
    categoria = models.CharField(max_length=100, verbose_name="Categoría")

    tecnica_texto = models.TextField(blank=True)
    descripcion_hallazgos_texto = models.TextField(blank=True)
    interpretacion_texto = models.TextField(blank=True)
    conclusiones_texto = models.TextField(blank=True)

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    uso_publico = models.BooleanField(default=False, verbose_name="Disponible para todos los médicos")
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    veces_usada = models.IntegerField(default=0)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Plantilla de Estudio'
        verbose_name_plural = 'Plantillas de Estudios'
        ordering = ['tipo_estudio', 'categoria', 'nombre']

    def __str__(self):
        return f"{self.nombre} - {self.get_tipo_estudio_display()}"


# ==============================================================================
# HISTORIAL INMUTABLE DE CAMBIOS (FORENSE)
# ==============================================================================
class HistorialCambiosConsulta(models.Model):
    """Registro inmutable de cada modificación a una consulta médica."""
    consulta = models.ForeignKey(ConsultaMedica, on_delete=models.PROTECT, related_name='historial_cambios')

    campo_modificado = models.CharField(max_length=100, verbose_name="Campo Modificado")
    valor_anterior = models.TextField(verbose_name="Valor Anterior")
    valor_nuevo = models.TextField(verbose_name="Valor Nuevo")

    razon_cambio = models.TextField(verbose_name="Razón del Cambio")

    usuario_modificador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_origen = models.GenericIPAddressField(null=True)

    hash_integridad = models.CharField(max_length=64, verbose_name="Hash SHA256")

    class Meta:
        app_label = 'core'
        verbose_name = 'Historial de Cambios'
        verbose_name_plural = 'Historial de Cambios'
        ordering = ['-timestamp']
        permissions = [
            ('ver_historial_cambios', 'Puede ver historial de cambios de consultas'),
        ]

    def __str__(self):
        return f"{self.consulta.folio_consulta} - {self.campo_modificado} - {self.timestamp}"

    def save(self, *args, **kwargs):
        if not self.hash_integridad:
            import hashlib
            data = f"{self.consulta.id}{self.campo_modificado}{self.valor_anterior}{self.valor_nuevo}{self.timestamp}".encode()
            self.hash_integridad = hashlib.sha256(data).hexdigest()
        super().save(*args, **kwargs)


class LogAccesoExpediente(models.Model):
    """Registro de cada acceso a expedientes clínicos. HIPAA y NOM-024-SSA3-2012."""
    historia_clinica = models.ForeignKey(HistoriaClinica, on_delete=models.PROTECT, related_name='logs_acceso')
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)

    fecha_acceso = models.DateTimeField(auto_now_add=True)
    ip_origen = models.GenericIPAddressField(null=True)

    tipo_acceso = models.CharField(max_length=20, choices=[
        ('LECTURA', 'Lectura'),
        ('MODIFICACION', 'Modificación'),
        ('IMPRESION', 'Impresión'),
        ('EXPORTACION', 'Exportación'),
    ], verbose_name="Tipo de Acceso")

    seccion_accedida = models.CharField(max_length=100, verbose_name="Sección Accedida")
    justificacion = models.TextField(blank=True, verbose_name="Justificación")

    navegador = models.CharField(max_length=200, blank=True)
    sistema_operativo = models.CharField(max_length=100, blank=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Log de Acceso a Expediente'
        verbose_name_plural = 'Logs de Acceso a Expedientes'
        ordering = ['-fecha_acceso']
        indexes = [
            models.Index(fields=['historia_clinica', 'fecha_acceso']),
            models.Index(fields=['usuario', 'fecha_acceso']),
        ]

    def __str__(self):
        return f"{self.historia_clinica.numero_expediente} - {self.usuario} - {self.fecha_acceso}"


# ==============================================================================
# BLOQUE: CONSENTIMIENTO INFORMADO (TRAZABILIDAD LEGAL)
# ==============================================================================
class ConsentimientoInformado(models.Model):
    """Consentimiento informado digital con firma y verificacion de integridad."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='consentimientos')
    paciente = models.ForeignKey('Paciente', on_delete=models.PROTECT, related_name='consentimientos')
    orden = models.OneToOneField('OrdenDeServicio', on_delete=models.PROTECT, related_name='consentimiento', null=True, blank=True, help_text='Opcional: orden asociada al consentimiento')

    firma_digital = models.TextField(verbose_name='Firma Digital (base64)', help_text='Firma del paciente en formato base64', blank=True)
    acepta_privacidad = models.BooleanField(default=False, verbose_name='Acepta Aviso de Privacidad')
    acepta_procesamiento = models.BooleanField(default=False, verbose_name='Acepta Procesamiento de Datos')
    consentimiento_marketing = models.BooleanField(default=False, verbose_name='Acepta Comunicaciones de Marketing')

    hash_firma = models.CharField(max_length=64, blank=True, verbose_name='Hash SHA-256 de Integridad')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    fecha_firma = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Firma')

    class Meta:
        app_label = 'core'
        verbose_name = 'Consentimiento Informado'
        verbose_name_plural = 'Consentimientos Informados'
        ordering = ['-fecha_firma']

    def __str__(self):
        return f'Consentimiento - {self.paciente.nombre_completo} - {self.fecha_firma.strftime("%Y-%m-%d")}'

    def calcular_hash(self):
        import hashlib
        orden_id = self.orden_id if self.orden_id else 'SIN_ORDEN'
        data = f'{self.paciente_id}|{orden_id}|{self.firma_digital}|{self.acepta_privacidad}|{self.acepta_procesamiento}|{self.consentimiento_marketing}'
        return hashlib.sha256(data.encode()).hexdigest()

    def verificar_integridad(self):
        return self.hash_firma == self.calcular_hash()


class RegistroAuditoriaConsentimiento(models.Model):
    """Auditoria de cambios en consentimientos."""
    consentimiento = models.ForeignKey(ConsentimientoInformado, on_delete=models.CASCADE, related_name='auditoria')
    accion = models.CharField(max_length=20, choices=[('CREADO', 'Creado'), ('MODIFICADO', 'Modificado'), ('REVOCADO', 'Revocado')])
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    descripcion = models.TextField(blank=True)
    datos_nuevos = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'core'
        verbose_name = 'Auditoria de Consentimiento'
        verbose_name_plural = 'Auditorias de Consentimientos'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.accion} - Consentimiento {self.consentimiento_id}'
