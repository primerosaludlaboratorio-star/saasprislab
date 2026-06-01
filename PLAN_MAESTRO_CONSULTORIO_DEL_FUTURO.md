# 🚀 PLAN MAESTRO: CONSULTORIO DEL FUTURO
## RE-INGENIERÍA TOTAL (AI + FORENSE + NEGOCIO)

**Fecha**: 25/01/2026  
**Filosofía**: *"El médico atiende, el sistema obedece, protege y monetiza."*  
**Objetivo**: Transformar el consultorio de formulario simple a **Asistente Clínico Proactivo**

---

## 📊 AUDITORÍA DEL ESTADO ACTUAL

### ✅ LO QUE YA TENEMOS

#### Modelos Existentes (`consultorio/models.py`):
- ✅ `AgendaCita` - Agendamiento básico
- ✅ `ConsultaMedica` - Captura de consulta
- ✅ `Somatometria` - Signos vitales
- ✅ `NotaMedica` - Nota médica simple

#### Modelos en Core (`core/models.py`):
- ✅ `Receta` - Sistema de recetas con firma digital
- ✅ `NotaClinicaSOAP` - Nota estructurada SOAP
- ✅ `PreOrdenLaboratorio` - Pre-órdenes de laboratorio

### ❌ LO QUE FALTA (CRÍTICO)

| Funcionalidad | Estado | Riesgo |
|---------------|--------|--------|
| **Grabación de Audio** | ❌ NO EXISTE | Legal Alto (NOM-004) |
| **Encriptación de Datos** | ❌ NO EXISTE | Seguridad Crítica |
| **Firma Digital Médica** | ⚠️ PARCIAL | Legal Medio |
| **Intención de Venta** | ❌ NO EXISTE | Negocio Alto |
| **Gastos Personales Médico** | ❌ NO EXISTE | Privacidad Media |
| **Offline Storage** | ❌ NO EXISTE | Resiliencia Alta |

---

## 🏗️ ARQUITECTURA DE LOS 5 NIVELES

### NIVEL 1: LA CAJA NEGRA 2.0 (SEGURIDAD NACIONAL)

**Objetivo**: Blindaje legal absoluto según NOM-004-SSA3-2012 y NOM-024-SSA3-2012

#### Modelo: `EvidenciaForense`
```python
# consultorio/models.py

from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
import hashlib
import json
from datetime import datetime

class EvidenciaForense(models.Model):
    """
    Almacenamiento forense de audio de consultas con encriptación asimétrica.
    
    CRÍTICO NOM-004: El audio es evidencia legal inmutable.
    La llave privada NO está en el sistema (Cold Storage).
    """
    TIPO_AUDIO = 'AUDIO'
    TIPO_VIDEO = 'VIDEO'
    TIPO_DOCUMENTO = 'DOCUMENTO'
    TIPO_CHOICES = [
        (TIPO_AUDIO, 'Audio de Consulta'),
        (TIPO_VIDEO, 'Video de Consulta'),
        (TIPO_DOCUMENTO, 'Documento Adjunto'),
    ]
    
    # Relación
    consulta = models.ForeignKey(
        'ConsultaMedica',
        on_delete=models.PROTECT,  # NUNCA eliminar evidencia
        related_name='evidencias_forenses',
        verbose_name="Consulta Médica"
    )
    
    # Identificación
    tipo_evidencia = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default=TIPO_AUDIO
    )
    
    # Almacenamiento Seguro
    archivo_encriptado = models.FileField(
        upload_to='evidencias_forenses/%Y/%m/%d/',
        verbose_name="Archivo Encriptado",
        help_text="Audio/video encriptado con llave pública"
    )
    
    # Integridad Blockchain-Style
    hash_sha256 = models.CharField(
        max_length=64,
        verbose_name="Hash SHA-256",
        help_text="Huella digital del archivo original (antes de encriptar)"
    )
    timestamp_certificado = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Timestamp Certificado",
        help_text="Fecha y hora inmutable de creación"
    )
    
    # Metadata
    duracion_segundos = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Duración (segundos)"
    )
    tamano_bytes = models.BigIntegerField(
        verbose_name="Tamaño del Archivo (bytes)"
    )
    
    # Acceso Controlado
    accedido_por = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='AccesoEvidencia',
        related_name='evidencias_accedidas',
        verbose_name="Usuarios que Han Accedido"
    )
    
    # Resiliencia (Offline)
    sincronizado = models.BooleanField(
        default=False,
        verbose_name="Sincronizado desde Offline",
        help_text="True si fue subido desde almacenamiento local offline"
    )
    fecha_sincronizacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Sincronización"
    )
    
    class Meta:
        verbose_name = "Evidencia Forense"
        verbose_name_plural = "Evidencias Forenses"
        ordering = ['-timestamp_certificado']
        indexes = [
            models.Index(fields=['consulta', '-timestamp_certificado']),
            models.Index(fields=['hash_sha256']),
        ]
    
    def __str__(self):
        return f"Evidencia {self.get_tipo_evidencia_display()} - Consulta #{self.consulta_id}"
    
    @staticmethod
    def encriptar_archivo(archivo_bytes, llave_publica):
        """
        Encripta el archivo con la llave pública.
        La llave privada está en Cold Storage (USB, HSM).
        """
        cipher = Fernet(llave_publica)
        archivo_encriptado = cipher.encrypt(archivo_bytes)
        return archivo_encriptado
    
    @staticmethod
    def calcular_hash(archivo_bytes):
        """
        Calcula el hash SHA-256 del archivo original.
        Permite verificar integridad sin necesidad de desencriptar.
        """
        return hashlib.sha256(archivo_bytes).hexdigest()
    
    def generar_metadata_blockchain(self):
        """
        Genera un JSON con metadata inmutable estilo blockchain.
        """
        return {
            'hash': self.hash_sha256,
            'timestamp': self.timestamp_certificado.isoformat(),
            'consulta_id': self.consulta_id,
            'medico_id': self.consulta.medico_id,
            'paciente_id': self.consulta.paciente_id,
            'tipo': self.tipo_evidencia,
            'tamano': self.tamano_bytes,
        }


class AccesoEvidencia(models.Model):
    """
    Registro forense de cada acceso a evidencia (quién, cuándo, por qué).
    
    Requisito Legal: En caso de auditoría o demanda, poder demostrar
    que NADIE accedió indebidamente al audio.
    """
    evidencia = models.ForeignKey(
        EvidenciaForense,
        on_delete=models.CASCADE,
        related_name='registros_acceso'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='accesos_evidencia'
    )
    
    # Trazabilidad
    fecha_hora_acceso = models.DateTimeField(auto_now_add=True)
    motivo_acceso = models.CharField(
        max_length=255,
        verbose_name="Motivo del Acceso",
        help_text="Ej: Revisión de caso clínico, Auditoría COFEPRIS, Orden Judicial"
    )
    autorizacion_judicial = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Número de Autorización Judicial",
        help_text="Solo si el acceso fue por orden judicial"
    )
    
    # Seguridad
    ip_address = models.GenericIPAddressField(
        verbose_name="Dirección IP del Acceso"
    )
    user_agent = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="User Agent"
    )
    
    class Meta:
        verbose_name = "Acceso a Evidencia"
        verbose_name_plural = "Accesos a Evidencias"
        ordering = ['-fecha_hora_acceso']
    
    def __str__(self):
        return f"{self.usuario.get_full_name()} accedió a {self.evidencia} ({self.fecha_hora_acceso})"
```

---

### NIVEL 2: EL ESCRIBA DIGITAL (NOTA & ULTRASONIDO)

**Objetivo**: Velocidad de atención sin sacrificar calidad

#### Modelo: `PlantillaConsulta`
```python
class PlantillaConsulta(models.Model):
    """
    Plantillas dinámicas que cambian según el tipo de consulta.
    """
    TIPO_GENERAL = 'GENERAL'
    TIPO_ULTRASONIDO = 'ULTRASONIDO'
    TIPO_PEDIATRIA = 'PEDIATRIA'
    TIPO_GINECOLOGIA = 'GINECOLOGIA'
    TIPO_CHOICES = [
        (TIPO_GENERAL, 'Consulta General'),
        (TIPO_ULTRASONIDO, 'Ultrasonido'),
        (TIPO_PEDIATRIA, 'Pediatría'),
        (TIPO_GINECOLOGIA, 'Ginecología'),
    ]
    
    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        related_name='plantillas_consulta'
    )
    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre de la Plantilla"
    )
    tipo_consulta = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default=TIPO_GENERAL
    )
    
    # Campos Dinámicos (JSON)
    campos_personalizados = models.JSONField(
        default=dict,
        verbose_name="Campos Personalizados",
        help_text="Ej: {'medidas_fetales': ['LCN', 'DBP', 'Femur'], 'hallazgos': ['Placenta', 'Liquido']}"
    )
    
    # Texto Predefinido
    texto_subjetivo = models.TextField(blank=True, verbose_name="Subjetivo (Plantilla)")
    texto_objetivo = models.TextField(blank=True, verbose_name="Objetivo (Plantilla)")
    texto_analisis = models.TextField(blank=True, verbose_name="Análisis (Plantilla)")
    texto_plan = models.TextField(blank=True, verbose_name="Plan (Plantilla)")
    
    activa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Plantilla de Consulta"
        verbose_name_plural = "Plantillas de Consulta"
        ordering = ['tipo_consulta', 'nombre']
    
    def __str__(self):
        return f"{self.get_tipo_consulta_display()} - {self.nombre}"


class TranscripcionDictado(models.Model):
    """
    Almacena el dictado en texto libre que luego alimenta la nota estructurada.
    Permite al médico hablar naturalmente sin llenar 20 inputs.
    """
    consulta = models.OneToOneField(
        'ConsultaMedica',
        on_delete=models.CASCADE,
        related_name='transcripcion_dictado'
    )
    
    # Texto Crudo del Dictado
    texto_crudo = models.TextField(
        verbose_name="Texto del Dictado",
        help_text="Texto libre capturado por Web Speech API o Whisper AI"
    )
    
    # Extracción Inteligente (por IA)
    subjetivo_extraido = models.TextField(blank=True, verbose_name="Subjetivo (Extraído por IA)")
    objetivo_extraido = models.TextField(blank=True, verbose_name="Objetivo (Extraído por IA)")
    analisis_extraido = models.TextField(blank=True, verbose_name="Análisis (Extraído por IA)")
    plan_extraido = models.TextField(blank=True, verbose_name="Plan (Extraído por IA)")
    
    # Metadata
    fecha_dictado = models.DateTimeField(auto_now_add=True)
    procesado_por_ia = models.BooleanField(
        default=False,
        verbose_name="Procesado por IA",
        help_text="True si ya se extrajo estructura SOAP del texto crudo"
    )
    
    class Meta:
        verbose_name = "Transcripción de Dictado"
        verbose_name_plural = "Transcripciones de Dictados"
    
    def __str__(self):
        return f"Dictado - Consulta #{self.consulta_id}"
```

---

### NIVEL 3: EL MOTOR DE OPORTUNIDADES ("INTENCIÓN DE VENTA")

**Objetivo**: Monetizar la receta sin burocracia ni datos basura

#### Modelo: `IntencionVenta`
```python
class IntencionVenta(models.Model):
    """
    Ghost Data: Captura la INTENCIÓN del médico sin crear Orden/Venta real.
    
    Filosofía: El médico receta, el sistema sugiere, pero NO ensucia la BD
    hasta que haya una transacción real.
    
    Ventaja de Negocio: Permite detectar "oportunidades perdidas".
    """
    TIPO_LABORATORIO = 'LABORATORIO'
    TIPO_FARMACIA = 'FARMACIA'
    TIPO_CHOICES = [
        (TIPO_LABORATORIO, 'Estudios de Laboratorio'),
        (TIPO_FARMACIA, 'Medicamentos de Farmacia'),
    ]
    
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_CONCRETADA = 'CONCRETADA'
    ESTADO_PERDIDA = 'PERDIDA'
    ESTADO_CANCELADA = 'CANCELADA'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente de Concretar'),
        (ESTADO_CONCRETADA, 'Concretada (Venta Real)'),
        (ESTADO_PERDIDA, 'Perdida (No se vendió)'),
        (ESTADO_CANCELADA, 'Cancelada (Médico rectificó)'),
    ]
    
    # Origen
    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        related_name='intenciones_venta'
    )
    consulta = models.ForeignKey(
        'ConsultaMedica',
        on_delete=models.CASCADE,
        related_name='intenciones_venta',
        verbose_name="Consulta Origen"
    )
    paciente = models.ForeignKey(
        'core.Paciente',
        on_delete=models.CASCADE,
        related_name='intenciones_venta'
    )
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='intenciones_venta_generadas',
        verbose_name="Médico que Recetó"
    )
    
    # Clasificación
    tipo_intencion = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE
    )
    
    # Contenido (JSON)
    items_sugeridos = models.JSONField(
        verbose_name="Items Sugeridos",
        help_text="Lista de estudios o medicamentos: [{'id': 1, 'nombre': 'Glucosa', 'precio': 50.00}, ...]"
    )
    valor_total_estimado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor Total Estimado"
    )
    
    # Trazabilidad
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField(
        verbose_name="Fecha de Expiración",
        help_text="Después de esta fecha, se marca como PERDIDA (default: 24h)"
    )
    fecha_concrecion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Concreción",
        help_text="Cuándo se convirtió en Orden/Venta real"
    )
    
    # Vinculación (si se concretó)
    orden_real = models.ForeignKey(
        'core.OrdenDeServicio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intenciones_origen',
        verbose_name="Orden Real Generada"
    )
    receta_real = models.ForeignKey(
        'core.Receta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intenciones_origen',
        verbose_name="Receta Real Generada"
    )
    
    # Data Mining
    razon_perdida = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Razón de Pérdida",
        help_text="Ej: Paciente no tiene dinero, Producto no disponible, Precio alto"
    )
    
    class Meta:
        verbose_name = "Intención de Venta"
        verbose_name_plural = "Intenciones de Venta"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', '-fecha_creacion']),
            models.Index(fields=['medico', '-fecha_creacion']),
            models.Index(fields=['tipo_intencion', 'estado']),
        ]
    
    def __str__(self):
        return f"Intención {self.get_tipo_intencion_display()} - {self.paciente.nombre_completo} ({self.get_estado_display()})"
    
    def marcar_como_perdida(self, razon="Expiró el tiempo límite"):
        """
        Marca la intención como perdida y registra la razón.
        Permite análisis de oportunidades de negocio no concretadas.
        """
        self.estado = self.ESTADO_PERDIDA
        self.razon_perdida = razon
        self.save()
    
    def concretar(self, orden_real=None, receta_real=None):
        """
        Marca la intención como concretada y vincula con la venta real.
        """
        self.estado = self.ESTADO_CONCRETADA
        self.fecha_concrecion = timezone.now()
        if orden_real:
            self.orden_real = orden_real
        if receta_real:
            self.receta_real = receta_real
        self.save()
```

#### Task Programada: Limpieza Nocturna
```python
# consultorio/management/commands/limpiar_intenciones_expiradas.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from consultorio.models import IntencionVenta

class Command(BaseCommand):
    help = 'Marca como PERDIDAS las intenciones de venta expiradas (> 24h sin concretar)'
    
    def handle(self, *args, **options):
        ahora = timezone.now()
        
        intenciones_expiradas = IntencionVenta.objects.filter(
            estado=IntencionVenta.ESTADO_PENDIENTE,
            fecha_expiracion__lte=ahora
        )
        
        count = intenciones_expiradas.count()
        
        for intencion in intenciones_expiradas:
            intencion.marcar_como_perdida(razon="Expiró el tiempo límite de 24 horas")
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ {count} intenciones marcadas como PERDIDAS')
        )
```

**Configuración en `settings.py` (Celery Beat)**:
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'limpiar-intenciones-expiradas': {
        'task': 'consultorio.tasks.limpiar_intenciones_expiradas',
        'schedule': crontab(hour=2, minute=0),  # Todos los días a las 2:00 AM
    },
}
```

---

### NIVEL 4: SILO FINANCIERO PRIVADO (LA BÓVEDA DEL MÉDICO)

**Objetivo**: Privacidad total del médico sin afectar transparencia administrativa

#### Modelo: `GastoPersonalMedico`
```python
class GastoPersonalMedico(models.Model):
    """
    Gastos personales del médico (café, asistente, gasolina).
    
    CEGUERA ADMINISTRATIVA: El Admin General NO puede ver este módulo.
    Solo el médico y el superusuario tienen acceso.
    """
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='gastos_personales',
        limit_choices_to={'rol': 'MEDICO'},
        verbose_name="Médico"
    )
    
    # Datos del Gasto
    concepto = models.CharField(
        max_length=255,
        verbose_name="Concepto",
        help_text="Ej: Café, Comida, Gasolina, Pago Asistente"
    )
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto"
    )
    fecha_gasto = models.DateField(
        verbose_name="Fecha del Gasto"
    )
    
    # Evidencia (Opcional)
    ticket_foto = models.ImageField(
        upload_to='gastos_personales/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Foto del Ticket"
    )
    
    # Clasificación
    categoria = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Categoría",
        help_text="Ej: Alimentación, Transporte, Personal"
    )
    
    # Auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Gasto Personal del Médico"
        verbose_name_plural = "Gastos Personales de Médicos"
        ordering = ['-fecha_gasto']
        permissions = [
            ("ver_gastos_personales_propios", "Puede ver solo sus gastos personales"),
        ]
    
    def __str__(self):
        return f"{self.concepto} - ${self.monto} ({self.fecha_gasto})"


class UtilidadNetaMedico(models.Model):
    """
    Cálculo automático de utilidad neta del médico (solo visible para él).
    
    Fórmula: Utilidad Neta = Ingresos por Consultas - Gastos Personales
    """
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='utilidades_netas',
        limit_choices_to={'rol': 'MEDICO'}
    )
    
    # Período
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    
    # Cálculos
    total_consultas = models.IntegerField(
        default=0,
        verbose_name="Total de Consultas Realizadas"
    )
    ingresos_brutos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Ingresos Brutos (Consultas)"
    )
    gastos_personales = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Gastos Personales"
    )
    utilidad_neta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Utilidad Neta de Bolsillo"
    )
    
    # Metadata
    fecha_calculo = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Utilidad Neta del Médico"
        verbose_name_plural = "Utilidades Netas de Médicos"
        ordering = ['-fecha_fin']
        unique_together = [['medico', 'fecha_inicio', 'fecha_fin']]
    
    def __str__(self):
        return f"Utilidad {self.medico.get_full_name()} ({self.fecha_inicio} - {self.fecha_fin}): ${self.utilidad_neta}"
    
    @staticmethod
    def calcular_para_periodo(medico, fecha_inicio, fecha_fin):
        """
        Calcula la utilidad neta del médico para un período específico.
        """
        # Contar consultas
        consultas = ConsultaMedica.objects.filter(
            medico=medico,
            fecha_creacion__date__gte=fecha_inicio,
            fecha_creacion__date__lte=fecha_fin
        )
        total_consultas = consultas.count()
        
        # Calcular ingresos (asumiendo precio de consulta en configuración)
        # O sumar desde un modelo de Pago de Consultas
        ingresos_brutos = Decimal('0.00')  # TODO: Implementar lógica de ingresos
        
        # Sumar gastos personales
        gastos = GastoPersonalMedico.objects.filter(
            medico=medico,
            fecha_gasto__gte=fecha_inicio,
            fecha_gasto__lte=fecha_fin
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        
        # Calcular utilidad neta
        utilidad_neta = ingresos_brutos - gastos
        
        # Guardar o actualizar
        utilidad, created = UtilidadNetaMedico.objects.update_or_create(
            medico=medico,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            defaults={
                'total_consultas': total_consultas,
                'ingresos_brutos': ingresos_brutos,
                'gastos_personales': gastos,
                'utilidad_neta': utilidad_neta
            }
        )
        
        return utilidad
```

---

### NIVEL 5: CUMPLIMIENTO NORMATIVO (NOM-004-SSA3-2012)

**Objetivo**: Validez legal del expediente electrónico

#### Modelo: `FirmaDigitalConsulta`
```python
class FirmaDigitalConsulta(models.Model):
    """
    Firma digital inmutable de la nota médica.
    
    NOM-004-SSA3-2012: El expediente clínico debe estar firmado electrónicamente
    por el personal autorizado.
    """
    consulta = models.OneToOneField(
        'ConsultaMedica',
        on_delete=models.PROTECT,  # NUNCA eliminar firma
        related_name='firma_digital'
    )
    
    # Datos del Médico (Congelados al momento de firmar)
    medico_nombre_completo = models.CharField(
        max_length=255,
        verbose_name="Nombre Completo del Médico"
    )
    medico_cedula = models.CharField(
        max_length=50,
        verbose_name="Cédula Profesional"
    )
    medico_especialidad = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Especialidad"
    )
    
    # Timestamp Inmutable
    fecha_hora_firma = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y Hora de Firma (Inmutable)"
    )
    
    # Hash de la Nota (Integridad)
    hash_nota = models.CharField(
        max_length=64,
        verbose_name="Hash SHA-256 de la Nota",
        help_text="Permite detectar si la nota fue alterada después de firmada"
    )
    
    # Bloqueo de Edición
    nota_bloqueada = models.BooleanField(
        default=True,
        verbose_name="Nota Bloqueada para Edición"
    )
    
    class Meta:
        verbose_name = "Firma Digital de Consulta"
        verbose_name_plural = "Firmas Digitales de Consultas"
        ordering = ['-fecha_hora_firma']
    
    def __str__(self):
        return f"Firma de {self.medico_nombre_completo} - {self.fecha_hora_firma}"
    
    @staticmethod
    def calcular_hash_nota(consulta):
        """
        Calcula el hash SHA-256 de los campos principales de la consulta.
        """
        contenido = f"{consulta.motivo}{consulta.exploracion_fisica}{consulta.diagnostico_texto}{consulta.tratamiento}"
        return hashlib.sha256(contenido.encode('utf-8')).hexdigest()
    
    def verificar_integridad(self):
        """
        Verifica si la nota ha sido alterada después de firmada.
        """
        hash_actual = self.calcular_hash_nota(self.consulta)
        return hash_actual == self.hash_nota


class NotaEvolucion(models.Model):
    """
    Nota de evolución o adenda (NOM-004).
    
    Cuando una consulta ya está firmada, NO se edita.
    Se crea una Nota de Evolución que complementa.
    """
    consulta_original = models.ForeignKey(
        'ConsultaMedica',
        on_delete=models.CASCADE,
        related_name='notas_evolucion',
        verbose_name="Consulta Original (Firmada)"
    )
    
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='notas_evolucion_realizadas'
    )
    
    contenido = models.TextField(
        verbose_name="Contenido de la Nota de Evolución",
        help_text="Ej: 'Paciente regresó 2 días después con fiebre. Se ajusta tratamiento.'"
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Nota de Evolución"
        verbose_name_plural = "Notas de Evolución"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Evolución de Consulta #{self.consulta_original_id} - {self.fecha_creacion}"
```

---

## 📋 PLAN DE IMPLEMENTACIÓN (PASO A PASO)

### FASE 1: MODELOS Y MIGRACIONES (1-2 días)
1. ✅ Crear todos los modelos en `consultorio/models.py`
2. ✅ Ejecutar `makemigrations consultorio`
3. ✅ Ejecutar `migrate consultorio`
4. ✅ Registrar modelos en `consultorio/admin.py`

### FASE 2: INFRAESTRUCTURA DE ENCRIPTACIÓN (1 día)
1. Instalar dependencias: `pip install cryptography`
2. Generar par de llaves (pública/privada):
   ```python
   from cryptography.fernet import Fernet
   
   # Generar llave
   llave = Fernet.generate_key()
   print(f"Llave Pública (guardar en settings.py): {llave.decode()}")
   print("Llave Privada: GUARDAR EN USB O COLD STORAGE")
   ```
3. Configurar `settings.py`:
   ```python
   # Llave pública para encriptar (en el servidor)
   EVIDENCIA_FORENSE_PUBLIC_KEY = b'...'
   
   # La llave privada NO está aquí (Cold Storage)
   ```

### FASE 3: VIEWS Y TEMPLATES (2-3 días)
1. Crear vista de captura con Context Switch (General/Ultrasonido)
2. Implementar grabación de audio con Web Audio API
3. Implementar encriptación client-side antes de subir
4. Crear vista de Intenciones de Venta en Farmacia/Lab
5. Crear vista privada de Gastos Personales Médico

### FASE 4: TAREAS PROGRAMADAS (1 día)
1. Implementar comando `limpiar_intenciones_expiradas`
2. Configurar Celery Beat para ejecución nocturna
3. Crear dashboard de "Oportunidades Perdidas" para el dueño

### FASE 5: SEGURIDAD Y AUDITORÍA (1 día)
1. Implementar permisos personalizados para gastos personales
2. Crear middleware para bloquear edición de notas firmadas
3. Implementar sistema de verificación de integridad (hash)

---

## 🔒 SEGURIDAD Y PERMISOS

### Permisos Django Personalizados
```python
# consultorio/models.py

class ConsultaMedica(models.Model):
    # ...
    class Meta:
        permissions = [
            ("ver_gastos_personales_propios", "Puede ver solo sus gastos personales"),
            ("acceder_evidencia_forense", "Puede acceder a audio encriptado (requiere autorización)"),
            ("firmar_consultas", "Puede firmar digitalmente consultas"),
        ]
```

### Middleware de Bloqueo
```python
# consultorio/middleware.py

from django.http import HttpResponseForbidden

class BloqueoEdicionNotasFirmadasMiddleware:
    """
    Middleware que bloquea cualquier intento de editar una consulta firmada.
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Verificar si es una solicitud POST a editar consulta
        if request.method == 'POST' and 'consultorio/captura_consulta' in request.path:
            consulta_id = request.resolver_match.kwargs.get('cita_id')
            if consulta_id:
                from consultorio.models import ConsultaMedica, FirmaDigitalConsulta
                try:
                    consulta = ConsultaMedica.objects.get(id=consulta_id)
                    if FirmaDigitalConsulta.objects.filter(consulta=consulta).exists():
                        return HttpResponseForbidden(
                            "Esta consulta ya está firmada digitalmente y NO puede editarse. "
                            "Crea una Nota de Evolución si necesitas agregar información."
                        )
                except ConsultaMedica.DoesNotExist:
                    pass
        
        response = self.get_response(request)
        return response
```

---

## 📊 REPORTES DE NEGOCIO

### Dashboard de Oportunidades Perdidas
```python
# consultorio/views.py

@login_required
def dashboard_oportunidades_perdidas(request):
    """
    Dashboard para el dueño: ¿Qué recetaron los médicos que NO vendimos?
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden("Acceso denegado")
    
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Sum, Count
    
    # Últimos 30 días
    fecha_inicio = timezone.now() - timedelta(days=30)
    
    # Intenciones perdidas por tipo
    perdidas_lab = IntencionVenta.objects.filter(
        tipo_intencion=IntencionVenta.TIPO_LABORATORIO,
        estado=IntencionVenta.ESTADO_PERDIDA,
        fecha_creacion__gte=fecha_inicio
    ).aggregate(
        total=Count('id'),
        valor=Sum('valor_total_estimado')
    )
    
    perdidas_farmacia = IntencionVenta.objects.filter(
        tipo_intencion=IntencionVenta.TIPO_FARMACIA,
        estado=IntencionVenta.ESTADO_PERDIDA,
        fecha_creacion__gte=fecha_inicio
    ).aggregate(
        total=Count('id'),
        valor=Sum('valor_total_estimado')
    )
    
    # Top 10 items más recetados NO vendidos
    # (requiere parsear items_sugeridos JSON)
    
    context = {
        'perdidas_lab': perdidas_lab,
        'perdidas_farmacia': perdidas_farmacia,
        'fecha_inicio': fecha_inicio,
    }
    
    return render(request, 'consultorio/dashboard_oportunidades.html', context)
```

---

## ✅ CHECKLIST DE CUMPLIMIENTO NOM-004

- [ ] Audio de consulta encriptado con llave pública
- [ ] Llave privada almacenada fuera del sistema (Cold Storage)
- [ ] Hash SHA-256 de archivos para integridad
- [ ] Timestamp certificado inmutable
- [ ] Registro forense de cada acceso a evidencia
- [ ] Firma digital con datos del médico congelados
- [ ] Bloqueo de edición de notas firmadas
- [ ] Notas de Evolución para correcciones post-firma
- [ ] Almacenamiento offline con sincronización automática
- [ ] Permisos diferenciados por rol

---

## 🎯 MÉTRICAS DE ÉXITO

| Métrica | Objetivo | Medición |
|---------|----------|----------|
| **Tiempo de Captura** | Reducir 50% | De 10 min a 5 min por consulta |
| **Tasa de Concreción** | > 70% | Intenciones convertidas en ventas |
| **Oportunidades Detectadas** | 100% | Todas las recetas rastreadas |
| **Cumplimiento Legal** | 100% | Cero hallazgos en auditorías |
| **Satisfacción Médico** | > 90% | Encuesta post-implementación |

---

## 🚀 RESULTADO FINAL

**Con esta implementación, el Consultorio se transforma en:**

1. ✅ **Asistente Clínico Proactivo**: Sugiere, no obliga
2. ✅ **Fortaleza Legal Inquebrantable**: Blindaje NOM-004 absoluto
3. ✅ **Motor de Ventas Inteligente**: Sin ser invasivo
4. ✅ **Bóveda de Privacidad**: Ceguera administrativa selectiva
5. ✅ **Sistema Resiliente**: Funciona online y offline

**Jonathan, este es el Consultorio del Futuro. Un sistema que escucha, escribe, protege y monetiza sin que el médico tenga que hacer un solo clic extra.** 🚀⚕️
