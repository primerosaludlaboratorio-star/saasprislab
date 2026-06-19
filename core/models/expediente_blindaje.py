"""
═══════════════════════════════════════════════════════════════════════════════
ARQUITECTURA DE BLINDAJE v2.0 — Expediente Médico Legalmente Inexpugnable
NOM-004-SSA3-2012 · NOM-024-SSA3-2012 · Firma Electrónica Simple
═══════════════════════════════════════════════════════════════════════════════

Este módulo implementa las 3 capas de blindaje:

1. 🔒 CAPA DE INMUTABILIDAD (Audit Trail Forense)
   - Snapshot JSONB de cada estado de nota
   - Encadenamiento SHA256 tipo blockchain
   - Verificación criptográfica de integridad

2. ✒️ CAPA DE FIRMA VINCULANTE (PIN-Lock)
   - LAB_VALIDATION_PIN como disparador de cierre
   - Estado CERRADO/INMUTABLE
   - Validación de Cédula Profesional para recetas

3. 🧪 CAPA DE INTEGRACIÓN LIMS v7.5
   - Motor de tokens (analito:, perfil:, paquete:)
   - Validación de preparación (ayuno, preparación especial)
═══════════════════════════════════════════════════════════════════════════════
"""

import hashlib
import json
import uuid
from datetime import datetime
from decimal import Decimal

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone


# =============================================================================
# CAPA 1: INMUTABILIDAD — BLOCKCHAIN DE NOTAS CLÍNICAS
# =============================================================================

class ExpedienteNotaSHA(models.Model):
    """
    Registro inmutable de notas clínicas con encadenamiento SHA256.
    
    Cada vez que se guarda una nota SOAP, se genera un snapshot JSONB
    y un hash que depende del hash anterior (blockchain simplificado).
    
    Fórmula: Hash_Actual = SHA256(Snapshot + Hash_Anterior + Timestamp)
    """
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador — Editable'),
        ('PRELIMINAR', 'Preliminar — Pendiente de firma'),
        ('SELLADA', 'Sellada — Firmada con PIN'),
        ('INMUTABLE', 'Inmutable — No modificable'),
    ]
    
    # Relaciones
    nota_soap = models.ForeignKey(
        'NotaClinicaSOAP',
        on_delete=models.PROTECT,
        related_name='expediente_shas',
        verbose_name="Nota SOAP"
    )
    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.CASCADE,
        related_name='expediente_notas_sha',
        verbose_name="Empresa"
    )
    paciente = models.ForeignKey(
        'Paciente',
        on_delete=models.PROTECT,
        related_name='expediente_notas_sha',
        verbose_name="Paciente"
    )
    medico = models.ForeignKey(
        'Usuario',
        on_delete=models.PROTECT,
        related_name='expedientes_generados',
        verbose_name="Médico Responsable"
    )
    
    # Datos de la nota (snapshot inmutable)
    version = models.PositiveIntegerField(default=1, verbose_name="Versión")
    snapshot_jsonb = models.JSONField(
        verbose_name="Snapshot JSONB",
        help_text="Estado completo de la nota en formato JSON"
    )
    estado_nota = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='BORRADOR',
        verbose_name="Estado de la Nota"
    )
    
    # Blockchain de integridad
    hash_sha256 = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Hash SHA256",
        help_text="Hash criptográfico del snapshot"
    )
    hash_anterior = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="Hash Anterior",
        help_text="Hash del registro previo en la cadena"
    )
    cadena_valida = models.BooleanField(
        default=True,
        verbose_name="Cadena Válida",
        help_text="False si se detecta ruptura en el encadenamiento"
    )
    
    # Metadatos
    timestamp_creacion = models.DateTimeField(auto_now_add=True)
    timestamp_edicion = models.DateTimeField(auto_now=True)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    # Firma (Capa 2)
    firmado_con_pin = models.BooleanField(default=False, verbose_name="Firmado con PIN")
    pin_hash = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Hash del PIN",
        help_text="SHA256 del PIN usado para firmar (no almacenamos el PIN)"
    )
    timestamp_firma = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        app_label = 'core'
        verbose_name = "Expediente Nota SHA (Blockchain)"
        verbose_name_plural = "Expedientes Notas SHA (Blockchain)"
        ordering = ['nota_soap', '-version']
        unique_together = [['nota_soap', 'version']]
        indexes = [
            models.Index(fields=['empresa', 'paciente', '-timestamp_creacion']),
            models.Index(fields=['hash_sha256']),
            models.Index(fields=['estado_nota', 'firmado_con_pin']),
        ]
    
    def __str__(self):
        return f"Nota {self.nota_soap_id} v{self.version} — {self.estado_nota} — {self.hash_sha256[:16]}..."
    
    def calcular_hash(self):
        """
        Calcula el hash SHA256 del snapshot + hash anterior + timestamp.
        Fórmula: SHA256(Snapshot + Hash_Anterior + Timestamp)
        
        ⚠️ SERIALIZACIÓN CANÓNICA: Usamos sort_keys=True y separators=(',', ':')
        para garantizar que el hash sea idéntico independientemente del orden
        de inserción de las claves en el diccionario.
        """
        # Normalizar el snapshot para hash consistente
        snapshot_str = json.dumps(
            self.snapshot_jsonb,
            sort_keys=True,
            ensure_ascii=False,
            separators=(',', ':'),  # Sin espacios, formato compacto consistente
            default=str
        )
        
        # Construir el bloque
        bloque = f"{snapshot_str}|{self.hash_anterior or 'GENESIS'}|{self.timestamp_creacion.isoformat()}"
        
        return hashlib.sha256(bloque.encode('utf-8')).hexdigest()
    
    def verificar_integridad(self):
        """
        Verifica que el hash almacenado coincida con el calculado.
        """
        hash_calculado = self.calcular_hash()
        return self.hash_sha256 == hash_calculado
    
    def verificar_cadena(self, hash_esperado_anterior=None):
        """
        Verifica la integridad de la cadena de hashes.
        Si hash_esperado_anterior es None, busca el registro anterior.
        """
        if self.version == 1:
            # Genesis block
            self.cadena_valida = True
            return True
        
        if hash_esperado_anterior is None:
            # Buscar versión anterior
            anterior = ExpedienteNotaSHA.objects.filter(
                nota_soap=self.nota_soap,
                version=self.version - 1
            ).first()
            if anterior:
                hash_esperado_anterior = anterior.hash_sha256
        
        if hash_esperado_anterior and self.hash_anterior != hash_esperado_anterior:
            self.cadena_valida = False
            return False
        
        self.cadena_valida = True
        return True
    
    def save(self, *args, **kwargs):
        # Si es nuevo, generar hash
        if not self.pk:
            if not self.hash_sha256:
                self.hash_sha256 = self.calcular_hash()
            
            # Buscar hash anterior si no se proporcionó
            if not self.hash_anterior and self.version > 1:
                anterior = ExpedienteNotaSHA.objects.filter(
                    nota_soap=self.nota_soap,
                    version=self.version - 1
                ).first()
                if anterior:
                    self.hash_anterior = anterior.hash_sha256
            elif self.version == 1:
                self.hash_anterior = None  # Genesis
        
        super().save(*args, **kwargs)


class SnapshotNotaMiddleware:
    """
    Middleware para capturar snapshots de notas SOAP automáticamente.
    Se conecta a la señal post_save de NotaClinicaSOAP.
    """
    
    @staticmethod
    def generar_snapshot(nota_soap):
        """
        Genera un snapshot JSONB completo de la nota SOAP.
        
        ⚠️ SERIALIZACIÓN CANÓNICA: Aplicamos sort_keys=True y separators=(',', ':')
        para garantizar consistencia matemática del hash.
        """
        snapshot_dict = {
            'id': nota_soap.id,
            'paciente_id': nota_soap.paciente_id,
            'empresa_id': nota_soap.empresa_id,
            'medico_id': nota_soap.medico_id,
            'subjetivo': nota_soap.subjetivo,
            'objetivo': nota_soap.objetivo,
            'analisis': nota_soap.analisis,
            'plan': nota_soap.plan,
            'diagnostico_principal': nota_soap.diagnostico_principal,
            'diagnosticos_secundarios': nota_soap.diagnosticos_secundarios,
            'archivos_adjuntos': nota_soap.archivos_adjuntos,
            'signos_vitales_snapshot': getattr(nota_soap, 'signos_vitales_snapshot', None),
            'fecha_consulta': nota_soap.fecha_consulta.isoformat() if nota_soap.fecha_consulta else None,
            'ultima_modificacion': nota_soap.ultima_modificacion.isoformat() if nota_soap.ultima_modificacion else None,
        }
        
        # Serialización canónica: orden consistente de claves y separadores mínimos
        # Esto garantiza que el hash sea idéntico sin importar el orden de inserción
        snapshot_json = json.dumps(
            snapshot_dict, 
            sort_keys=True, 
            separators=(',', ':'),  # Sin espacios, formato compacto
            default=str
        )
        
        # Convertir de vuelta a dict para almacenar en JSONField
        return json.loads(snapshot_json)
    
    @classmethod
    def crear_expediente_sha(cls, nota_soap, estado='BORRADOR', ip=None, user_agent=None):
        """
        Crea un nuevo registro ExpedienteNotaSHA para una nota.
        """
        # Calcular siguiente versión
        ultima_version = ExpedienteNotaSHA.objects.filter(
            nota_soap=nota_soap
        ).order_by('-version').first()
        
        version = (ultima_version.version + 1) if ultima_version else 1
        hash_anterior = ultima_version.hash_sha256 if ultima_version else None
        
        snapshot = cls.generar_snapshot(nota_soap)
        
        with transaction.atomic():
            expediente = ExpedienteNotaSHA.objects.create(
                nota_soap=nota_soap,
                empresa=nota_soap.empresa,
                paciente=nota_soap.paciente,
                medico=nota_soap.medico,
                version=version,
                snapshot_jsonb=snapshot,
                estado_nota=estado,
                hash_anterior=hash_anterior,
                ip_origen=ip,
                user_agent=user_agent,
            )
            return expediente


# =============================================================================
# CAPA 2: FIRMA VINCULANTE — PIN-LOCK Y CIERRE INMUTABLE
# =============================================================================

class NotaClinicaSellar(models.Model):
    """
    Extensión de NotaClinicaSOAP para firma vinculante con PIN-LAB.
    
    Implementa la Firma Electrónica Simple (FES) requerida por NOM-004.
    """
    nota_soap = models.OneToOneField(
        'NotaClinicaSOAP',
        on_delete=models.CASCADE,
        related_name='sello_firma',
        verbose_name="Nota SOAP"
    )
    
    # Estado de sellado
    ESTADO_SELLO_CHOICES = [
        ('EDITABLE', 'Editable — En redacción'),
        ('PRE_SELLADA', 'Pre-sellada — Pendiente de PIN'),
        ('SELLADA', 'Sellada — Firmada e inmutable'),
    ]
    estado_sello = models.CharField(
        max_length=15,
        choices=ESTADO_SELLO_CHOICES,
        default='EDITABLE',
        verbose_name="Estado de Sello"
    )
    
    # Datos de firma
    folio_unico = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Folio Único de Sello",
        help_text="Folio generado al momento de sellar"
    )
    pin_hash = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Hash SHA256 del PIN",
        help_text="Almacenamos el hash, no el PIN"
    )
    medico_firmante = models.ForeignKey(
        'Usuario',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='notas_selladas',
        verbose_name="Médico Firmante"
    )
    cedula_profesional = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Cédula Profesional"
    )
    especialidad = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especialidad del Médico"
    )
    
    # Timestamps
    timestamp_pre_sellado = models.DateTimeField(null=True, blank=True)
    timestamp_sellado = models.DateTimeField(null=True, blank=True)
    
    # PDF generado
    pdf_firmado = models.FileField(
        upload_to='expedientes/pdf_firmados/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="PDF Firmado"
    )
    hash_pdf = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Hash SHA256 del PDF"
    )
    
    # QR de verificación
    qr_verificacion = models.TextField(blank=True, verbose_name="QR de Verificación")
    token_verificacion = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    # Referencia al expediente SHA
    expediente_sha = models.ForeignKey(
        ExpedienteNotaSHA,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sellos',
        verbose_name="Expediente SHA de referencia"
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🔍 EVIDENCIA FORENSE DE FIRMA — Reparación Grieta #3
    # Captura metadatos del entorno en el momento exacto del sellado
    # para proveer evidencia legal de identidad, ubicación y dispositivo
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Origen de red
    ip_origen = models.GenericIPAddressField(
        null=True, 
        blank=True, 
        verbose_name="IP de Origen",
        help_text="Dirección IP desde donde se realizó la firma"
    )
    user_agent = models.CharField(
        max_length=500, 
        blank=True, 
        verbose_name="User Agent",
        help_text="Navegador y sistema operativo del dispositivo"
    )
    dispositivo_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ID de Dispositivo",
        help_text="Identificador único del dispositivo (si está disponible)"
    )
    
    # Geolocalización (si está disponible)
    ubicacion_latitud = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Latitud"
    )
    ubicacion_longitud = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Longitud"
    )
    ubicacion_precision = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Precisión (metros)",
        help_text="Precisión de la geolocalización en metros"
    )
    
    # Información de red adicional
    isp_proveedor = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Proveedor ISP",
        help_text="Proveedor de servicios de internet detectado"
    )
    pais_detectado = models.CharField(
        max_length=2,
        blank=True,
        verbose_name="País (ISO)",
        help_text="Código ISO del país detectado por IP"
    )
    
    class Meta:
        app_label = 'core'
        verbose_name = "Sello de Nota Clínica (PIN-Lock)"
        verbose_name_plural = "Sellos de Notas Clínicas (PIN-Lock)"
        ordering = ['-timestamp_sellado']
        indexes = [
            models.Index(fields=['estado_sello', 'timestamp_sellado']),
            models.Index(fields=['token_verificacion']),
            models.Index(fields=['folio_unico']),
            models.Index(fields=['ip_origen', 'timestamp_sellado']),  # 🔍 Forense: búsqueda por IP
        ]
    
    def __str__(self):
        return f"Sello {self.folio_unico or 'Sin folio'} — {self.estado_sello}"
    
    def generar_folio(self):
        """Genera un folio único basado en empresa, año y correlativo."""
        from django.utils import timezone as _tz
        año = _tz.localtime(_tz.now()).year
        prefijo = f"EXP-{self.nota_soap.empresa_id}-{año}-"
        
        # Contar sellos existentes de esta empresa
        count = NotaClinicaSellar.objects.filter(
            folio_unico__startswith=prefijo
        ).count()
        
        self.folio_unico = f"{prefijo}{str(count + 1).zfill(6)}"
        return self.folio_unico
    
    def pre_sellar(self, medico):
        """
        Marca la nota como pre-sellada, pendiente de confirmación con PIN.
        """
        if self.estado_sello == 'SELLADA':
            raise ValidationError("La nota ya está sellada e inmutable.")
        
        self.estado_sello = 'PRE_SELLADA'
        self.medico_firmante = medico
        self.timestamp_pre_sellado = timezone.now()
        
        # Obtener cédula y especialidad del perfil del médico
        if hasattr(medico, 'perfil_medico'):
            self.cedula_profesional = medico.perfil_medico.cedula_profesional
            self.especialidad = medico.perfil_medico.especialidad
        
        self.save()
        return self
    
    def sellar_con_pin(self, pin_limpio, ip_origen=None):
        """
        Sella la nota con el PIN del médico.
        Genera hash del PIN, crea snapshot inmutable, y marca como sellada.
        """
        if self.estado_sello == 'SELLADA':
            raise ValidationError("La nota ya está sellada.")
        
        if not self.medico_firmante:
            raise ValidationError("No hay médico asignado para firmar.")
        
        # Validar PIN contra el almacenado del médico (LAB_VALIDATION_PIN)
        # El PIN no se almacena en texto plano, se compara hashes
        if not self._validar_pin_medico(pin_limpio):
            raise ValidationError("PIN inválido. No se puede sellar la nota.")
        
        with transaction.atomic():
            # 1. Generar hash del PIN usado
            self.pin_hash = hashlib.sha256(pin_limpio.encode()).hexdigest()
            
            # 2. Generar folio único
            if not self.folio_unico:
                self.generar_folio()
            
            # 3. Crear snapshot inmutable en ExpedienteNotaSHA
            expediente = SnapshotNotaMiddleware.crear_expediente_sha(
                nota_soap=self.nota_soap,
                estado='SELLADA',
                ip=ip_origen,
                user_agent=None
            )
            self.expediente_sha = expediente
            
            # 4. Marcar como sellada
            self.estado_sello = 'SELLADA'
            self.timestamp_sellado = timezone.now()
            
            # 5. Generar QR de verificación
            self.qr_verificacion = self._generar_qr_verificacion()
            
            self.save()
            
            # 6. Marcar el expediente SHA como firmado
            expediente.firmado_con_pin = True
            expediente.pin_hash = self.pin_hash
            expediente.timestamp_firma = self.timestamp_sellado
            expediente.save()
        
        return self
    
    def _validar_pin_medico(self, pin_limpio):
        """
        Valida el PIN contra el perfil del médico.
        El PIN del médico se almacena como hash en su perfil.
        """
        # Obtener el perfil del médico
        perfil = getattr(self.medico_firmante, 'perfil_medico', None)
        if not perfil:
            return False
        
        # El campo pin_hash debe existir en el perfil del médico
        pin_hash_almacenado = getattr(perfil, 'lab_validation_pin_hash', None)
        if not pin_hash_almacenado:
            return False
        
        # Comparar hashes
        pin_hash_input = hashlib.sha256(pin_limpio.encode()).hexdigest()
        return pin_hash_input == pin_hash_almacenado
    
    def _generar_qr_verificacion(self):
        """Genera URL de verificación para el QR."""
        from django.conf import settings
        base_url = getattr(settings, 'SITE_URL', 'https://prislab.app')
        return f"{base_url}/verificar/{self.token_verificacion}"
    
    def verificar_integridad(self):
        """
        Verifica la integridad del sello comparando con el expediente SHA.
        """
        if not self.expediente_sha:
            return False
        
        return self.expediente_sha.verificar_integridad()


# =============================================================================
# CAPA 3: INTEGRACIÓN LIMS v7.5 — MOTOR DE TOKENS
# =============================================================================

class TokenLIMSV7Manager:
    """
    Motor de resolución de tokens LIMS v7.5.
    
    Convierte tokens de texto (analito:, perfil:, paquete:) en órdenes
    de laboratorio con trazabilidad completa de reactivos.
    """
    
    TOKEN_PATTERNS = {
        'analito': r'analito:\s*(\w+)',
        'perfil': r'perfil:\s*(\w+)',
        'paquete': r'paquete:\s*(\w+)',
    }
    
    @classmethod
    def parsear_texto(cls, texto):
        """
        Extrae tokens del texto de la nota SOAP.
        Retorna lista de dicts con tipo y código.
        """
        import re
        tokens = []
        
        for tipo, pattern in cls.TOKEN_PATTERNS.items():
            matches = re.finditer(pattern, texto, re.IGNORECASE)
            for match in matches:
                tokens.append({
                    'tipo': tipo,
                    'codigo': match.group(1).upper(),
                    'match': match.group(0)
                })
        
        return tokens
    
    @classmethod
    def resolver_a_orden(cls, tokens, paciente, medico, empresa):
        """
        Convierte tokens en una OrdenDeServicio.
        """
        from .laboratorio import OrdenDeServicio, DetalleOrden
        
        with transaction.atomic():
            # Crear orden base
            orden = OrdenDeServicio.objects.create(
                paciente=paciente,
                medico_referente=medico,
                empresa=empresa,
                # ... otros campos
            )
            
            # Resolver cada token a detalles
            for token in tokens:
                detalles = cls._resolver_token(token, orden)
                # Los detalles se crean dentro de _resolver_token
            
            return orden
    
    @classmethod
    def _resolver_token(cls, token, orden):
        """
        Resuelve un token específico a analitos del LIMS.
        """
        if token['tipo'] == 'analito':
            # Buscar analito por código
            from lims.models import Analito
            analito = Analito.objects.filter(codigo=token['codigo']).first()
            if analito:
                return cls._crear_detalle_orden(orden, analito)
        
        elif token['tipo'] == 'perfil':
            # Buscar perfil y sus analitos
            from lims.models import Perfil
            perfil = Perfil.objects.filter(codigo=token['codigo']).first()
            if perfil:
                detalles = []
                for analito in perfil.analitos.all():
                    detalles.append(cls._crear_detalle_orden(orden, analito))
                return detalles
        
        elif token['tipo'] == 'paquete':
            # Buscar paquete y sus perfiles/analitos
            from lims.models import Paquete
            paquete = Paquete.objects.filter(codigo=token['codigo']).first()
            if paquete:
                detalles = []
                for perfil in paquete.perfiles.all():
                    for analito in perfil.analitos.all():
                        detalles.append(cls._crear_detalle_orden(orden, analito))
                return detalles
        
        return None
    
    @classmethod
    def _crear_detalle_orden(cls, orden, analito):
        """Crea un DetalleOrden para un analito."""
        from .laboratorio import DetalleOrden
        return DetalleOrden.objects.create(
            orden=orden,
            analito=analito,
            estado='PENDIENTE'
        )


class ReglaPreparacionAnalito(models.Model):
    """
    Reglas de preparación para analitos (ayuno, preparación especial).
    """
    analito = models.OneToOneField(
        'lims.Analito',
        on_delete=models.CASCADE,
        related_name='regla_preparacion',
        verbose_name="Analito"
    )
    
    # Requisitos de preparación
    requiere_ayuno = models.BooleanField(default=False, verbose_name="Requiere Ayuno")
    horas_ayuno = models.PositiveIntegerField(
        default=8,
        verbose_name="Horas de Ayuno",
        help_text="Mínimo de horas de ayuno requeridas"
    )
    
    requiere_preparacion_especial = models.BooleanField(
        default=False,
        verbose_name="Requiere Preparación Especial"
    )
    instrucciones_preparacion = models.TextField(
        blank=True,
        verbose_name="Instrucciones de Preparación",
        help_text="Instrucciones detalladas para el paciente"
    )
    
    # Restricciones
    contraindicaciones = models.TextField(
        blank=True,
        verbose_name="Contraindicaciones",
        help_text="Condiciones donde no aplicar (ej: embarazo, diabetes)"
    )
    
    # Alertas
    alerta_medico = models.TextField(
        blank=True,
        verbose_name="Alerta al Médico",
        help_text="Mensaje de alerta al momento de prescribir"
    )
    
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'core'
        verbose_name = "Regla de Preparación de Analito"
        verbose_name_plural = "Reglas de Preparación de Analitos"
    
    def __str__(self):
        return f"{self.analito} — Ayuno: {self.horas_ayuno}h"
    
    def validar_paciente(self, paciente):
        """
        Valida si un paciente cumple con las reglas de preparación.
        Retorna dict con {valido: bool, alertas: list}
        """
        alertas = []
        
        if self.requiere_ayuno:
            alertas.append(f"Requiere ayuno de {self.horas_ayuno} horas")
        
        if self.requiere_preparacion_especial:
            alertas.append(f"Preparación especial: {self.instrucciones_preparacion[:100]}...")
        
        # Verificar contraindicaciones
        if self.contraindicaciones:
            # Aquí se podría implementar lógica de verificación médica
            pass
        
        return {
            'valido': True,  # Por defecto válido, alertas son informativas
            'alertas': alertas,
            'requiere_confirmacion': len(alertas) > 0
        }


class OrdenTokenLIMS(models.Model):
    """
    Registro de órdenes generadas desde tokens LIMS v7.5.
    Permite trazabilidad completa: Nota SOAP → Tokens → Orden LIMS → Reactivos
    """
    nota_soap = models.ForeignKey(
        'NotaClinicaSOAP',
        on_delete=models.CASCADE,
        related_name='ordenes_token_lims',
        verbose_name="Nota SOAP Origen"
    )
    orden_lims = models.ForeignKey(
        'OrdenDeServicio',
        on_delete=models.CASCADE,
        related_name='orden_token_origen',
        verbose_name="Orden LIMS Generada"
    )
    
    # Tokens usados
    tokens_json = models.JSONField(
        verbose_name="Tokens Utilizados",
        help_text="Lista de tokens {tipo, codigo} usados"
    )
    
    # Texto original parseado
    texto_original = models.TextField(
        verbose_name="Texto Original de la Nota",
        help_text="Snapshot del texto donde se detectaron los tokens"
    )
    
    # Validaciones
    preparacion_validada = models.BooleanField(
        default=False,
        verbose_name="Preparación Validada"
    )
    alertas_preparacion = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Alertas de Preparación"
    )
    
    # Timestamps
    timestamp_creacion = models.DateTimeField(auto_now_add=True)
    medico_generador = models.ForeignKey(
        'Usuario',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Médico que Generó"
    )
    
    class Meta:
        app_label = 'core'
        verbose_name = "Orden Token LIMS v7.5"
        verbose_name_plural = "Órdenes Token LIMS v7.5"
        ordering = ['-timestamp_creacion']
    
    def __str__(self):
        return f"Orden {self.orden_lims_id} desde Nota {self.nota_soap_id}"


# =============================================================================
# CATÁLOGO CIE-10 PARA DIAGNÓSTICOS CODIFICADOS
# =============================================================================

class CatalogoCIE10(models.Model):
    """
    Catálogo CIE-10 para diagnósticos codificados según NOM-004-SSA3-2012.
    """
    codigo = models.CharField(
        max_length=10,
        primary_key=True,
        verbose_name="Código CIE-10"
    )
    descripcion = models.CharField(
        max_length=500,
        verbose_name="Descripción"
    )
    descripcion_larga = models.TextField(
        blank=True,
        verbose_name="Descripción Larga"
    )
    
    # Categorización
    categoria = models.CharField(
        max_length=100,
        verbose_name="Categoría"
    )
    capitulo = models.CharField(
        max_length=10,
        verbose_name="Capítulo CIE-10"
    )
    
    # Metadatos
    es_principal = models.BooleanField(
        default=False,
        verbose_name="Puede ser Diagnóstico Principal"
    )
    sexo_restringido = models.CharField(
        max_length=1,
        blank=True,
        choices=[('M', 'Masculino'), ('F', 'Femenino')],
        verbose_name="Restricción de Sexo"
    )
    edad_minima = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Edad Mínima (años)"
    )
    edad_maxima = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Edad Máxima (años)"
    )
    
    activo = models.BooleanField(default=True)
    
    class Meta:
        app_label = 'core'
        verbose_name = "Catálogo CIE-10"
        verbose_name_plural = "Catálogo CIE-10"
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo', 'activo']),
            models.Index(fields=['categoria', 'activo']),
        ]
    
    def __str__(self):
        return f"{self.codigo} — {self.descripcion[:50]}"


# ═══════════════════════════════════════════════════════════════════════════════
# 🔒 REPARACIÓN GRIETA #2: HASH RAÍZ DIARIO — ANCLAJE EXTERNO
# ═══════════════════════════════════════════════════════════════════════════════

class HashRaizDiario(models.Model):
    """
    Hash raíz diario para anclaje externo (timestamping) del blockchain.
    
    Cada medianoche, el sistema genera un hash de todos los hashes del día
    y lo envía por email automático a una cuenta externa. Esto crea una
    evidencia de tiempo fuera del servidor, imposible de alterar retrospectivamente.
    
    Fórmula: Hash_Raiz = SHA256(Hash1 + Hash2 + ... + HashN + Fecha)
    
    Si alguien altera la base de datos, el hash diario ya no coincidirá
    con el email enviado hace tres meses, evidenciando la manipulación.
    """
    
    # Identificación temporal
    fecha = models.DateField(unique=True, verbose_name="Fecha")
    año = models.PositiveIntegerField(verbose_name="Año")
    mes = models.PositiveIntegerField(verbose_name="Mes")
    dia = models.PositiveIntegerField(verbose_name="Día")
    
    # Hash raíz del día
    hash_raiz = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Hash Raíz SHA256",
        help_text="Hash de todos los hashes del día"
    )
    
    # Contadores
    total_notas_selladas = models.PositiveIntegerField(
        default=0,
        verbose_name="Notas Selladas"
    )
    total_hashes_acumulados = models.PositiveIntegerField(
        default=0,
        verbose_name="Total de Hashes Acumulados"
    )
    
    # Evidencia de anclaje externo
    email_enviado_a = models.EmailField(
        blank=True,
        verbose_name="Email Enviado A",
        help_text="Dirección de email externa donde se envió el hash"
    )
    timestamp_envio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Timestamp de Envío"
    )
    email_message_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Message-ID del Email",
        help_text="ID del email para trazabilidad forense"
    )
    
    # Evidencia de publicación (opcional: blockchain público, IPFS, etc.)
    tx_id_blockchain = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="TX ID Blockchain",
        help_text="ID de transacción si se ancla en blockchain público"
    )
    url_ipfs = models.URLField(
        blank=True,
        verbose_name="URL IPFS",
        help_text="Hash IPFS si se publica en IPFS"
    )
    
    # Hash del día anterior (encadenamiento de días)
    hash_anterior_dia = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Hash Raíz del Día Anterior",
        help_text="Para encadenar días (cadena de bloques de días)"
    )
    
    # Metadatos
    timestamp_creacion = models.DateTimeField(auto_now_add=True)
    timestamp_calculo = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Timestamp de Cálculo"
    )
    ip_calculador = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP del Servidor Calculador"
    )
    
    class Meta:
        app_label = 'core'
        verbose_name = "Hash Raíz Diario (Anclaje)"
        verbose_name_plural = "Hashes Raíz Diarios (Anclaje)"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['fecha', 'hash_raiz']),
            models.Index(fields=['año', 'mes']),
            models.Index(fields=['timestamp_envio']),
        ]
    
    def __str__(self):
        return f"Hash Raíz {self.fecha} — {self.hash_raiz[:16]}..."
    
    def calcular_hash_raiz(self, hashes_del_dia):
        """
        Calcula el hash raíz del día a partir de todos los hashes.
        
        Args:
            hashes_del_dia: Lista de hashes SHA256 del día
        
        Returns:
            str: Hash SHA256 del concatenado ordenado
        """
        # Ordenar los hashes para consistencia
        hashes_ordenados = sorted(hashes_del_dia)
        
        # Concatenar con fecha
        bloque = f"{'|'.join(hashes_ordenados)}|{self.fecha.isoformat()}"
        
        # Agregar hash del día anterior si existe
        if self.hash_anterior_dia:
            bloque = f"{bloque}|{self.hash_anterior_dia}"
        
        return hashlib.sha256(bloque.encode('utf-8')).hexdigest()
    
    def verificar_integridad_anclaje(self):
        """
        Verifica que el hash raíz coincida con los hashes acumulados.
        """
        from core.models import ExpedienteNotaSHA
        
        # Obtener hashes del día
        inicio_dia = datetime.combine(self.fecha, datetime.min.time())
        fin_dia = datetime.combine(self.fecha, datetime.max.time())
        
        hashes_del_dia = list(ExpedienteNotaSHA.objects.filter(
            timestamp_creacion__range=(inicio_dia, fin_dia),
            firmado_con_pin=True
        ).values_list('hash_sha256', flat=True))
        
        hash_calculado = self.calcular_hash_raiz(hashes_del_dia)
        
        return {
            'valido': hash_calculado == self.hash_raiz,
            'hash_almacenado': self.hash_raiz,
            'hash_calculado': hash_calculado,
            'total_hashes_verificados': len(hashes_del_dia),
        }


# =============================================================================
# SEÑALES DE CONEXIÓN
# =============================================================================

def conectar_seniales():
    """
    Conecta las señales post_save para generar snapshots automáticamente.
    Se llama desde ready() en apps.py
    """
    from django.db.models.signals import post_save
    from django.dispatch import receiver
    
    @receiver(post_save, sender='core.NotaClinicaSOAP')
    def crear_snapshot_al_guardar(sender, instance, created, **kwargs):
        """
        Crea automáticamente un ExpedienteNotaSHA cada vez que se guarda una nota.
        """
        # Solo crear snapshot si la nota no está sellada
        sello = getattr(instance, 'sello_firma', None)
        if sello and sello.estado_sello == 'SELLADA':
            return  # No crear snapshots de notas selladas
        
        # Crear snapshot
        SnapshotNotaMiddleware.crear_expediente_sha(
            nota_soap=instance,
            estado='BORRADOR' if created else 'PRELIMINAR'
        )


# Importar señales al final para evitar circular imports
try:
    from django.apps import apps
    if apps.ready:
        conectar_seniales()
except Exception:
    pass  # Las señales se conectarán cuando Django esté listo
