"""
Modelos para el módulo de Inteligencia Artificial (OCR y Voz).
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

from core.validators import validate_image_upload, validate_audio_upload


class CotizacionOCR(models.Model):
    """
    Resultado de una cotización automática usando OCR sobre una receta.
    """
    imagen_receta = models.ImageField(
        upload_to='recetas_ocr/%Y/%m/%d/',
        help_text='Imagen de la receta escaneada',
        validators=[validate_image_upload],
    )
    
    texto_extraido = models.TextField(
        help_text='Texto extraído por el OCR'
    )
    
    # Estudios detectados: [{estudio_id: 1, nombre: "Glucosa", confianza: 0.95}, ...]
    estudios_detectados = models.JSONField(
        default=list,
        help_text='Lista de estudios detectados con su nivel de confianza'
    )
    
    total_calculado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total calculado automáticamente'
    )
    
    confianza_promedio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Nivel de confianza promedio de la detección (0-1)'
    )
    
    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cotizaciones_ocr_creadas'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    # Si se convirtió en orden real
    orden_asociada = models.ForeignKey(
        'core.OrdenDeServicio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cotizacion_ocr',
        help_text='Orden LIMS (core) creada a partir de esta cotización'
    )
    
    class Meta:
        verbose_name = 'Cotización OCR'
        verbose_name_plural = 'Cotizaciones OCR'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Cotización OCR - {self.fecha_creacion.strftime('%Y-%m-%d %H:%M')} - ${self.total_calculado}"
    
    def procesar_imagen(self):
        """
        Ojo Biónico: Procesa la imagen de receta usando Fuzzy Matching.
        Detecta palabras clave y sugiere estudios automáticamente.
        """
        from difflib import SequenceMatcher
        from laboratorio.models import Estudio
        from core.models import Empresa
        
        # Simulación de extracción de texto (en producción usar OCR real)
        texto = self.texto_extraido.lower()
        
        # Palabras clave comunes en recetas
        palabras_clave_estudios = {
            'biometría': ['biometría hemática', 'biometria', 'hemograma', 'citometría'],
            'química': ['química sanguínea', 'quimica', 'química', 'perfil químico'],
            'general': ['química general', 'perfil general', 'química básica'],
            'hepático': ['perfil hepático', 'hepatico', 'enzimas hepáticas', 'transaminasas'],
            'lipídico': ['perfil lipídico', 'lipidico', 'colesterol', 'triglicéridos'],
            'renal': ['perfil renal', 'urea', 'creatinina', 'nitrógeno'],
            'electrolitos': ['electrolitos', 'sodio', 'potasio', 'cloro'],
            'glucosa': ['glucosa', 'azúcar', 'glicemia'],
            'vdrl': ['vdrl', 'sífilis', 'lúes'],
            'antígeno': ['antígeno prostático', 'psa', 'antigeno'],
            'eg': ['examen general de orina', 'ego', 'orina completa'],
        }
        
        estudios_detectados = []
        
        # Buscar coincidencias en el texto
        for palabra_clave, variantes in palabras_clave_estudios.items():
            # Buscar en texto
            if any(variante in texto for variante in variantes):
                # Buscar estudios relacionados en la base de datos
                # Si tiene empresa asociada, filtrar por empresa
                empresa_id = getattr(self.usuario_creador, 'empresa_id', None) if self.usuario_creador else None
                qs = Estudio.objects.all()
                if empresa_id:
                    qs = qs.filter(empresa_id=empresa_id) if hasattr(Estudio, 'empresa') else qs
                estudios_relacionados = qs.filter(
                    nombre__icontains=palabra_clave
                )[:5]  # Máximo 5 estudios por palabra clave
                
                for estudio in estudios_relacionados:
                    # Calcular similitud
                    similitud = max([
                        SequenceMatcher(None, texto, variante.lower()).ratio()
                        for variante in variantes
                    ])
                    
                    if similitud > 0.3:  # Umbral mínimo de similitud
                        estudios_detectados.append({
                            'estudio_id': estudio.id,
                            'nombre': estudio.nombre,
                            'precio': float(estudio.precio_base),
                            'confianza': min(similitud * 1.5, 1.0)  # Ajustar a 0-1
                        })
        
        # Actualizar modelo
        self.estudios_detectados = estudios_detectados
        
        # Calcular total
        self.total_calculado = sum(est['precio'] for est in estudios_detectados)
        
        # Calcular confianza promedio
        if estudios_detectados:
            self.confianza_promedio = sum(est['confianza'] for est in estudios_detectados) / len(estudios_detectados)
        else:
            self.confianza_promedio = Decimal('0.00')
        
        self.save()
        return estudios_detectados


class TranscripcionVoz(models.Model):
    """
    Resultado de una transcripción de voz usando Whisper o similar.
    """
    audio = models.FileField(
        upload_to='transcripciones_voz/%Y/%m/%d/',
        help_text='Archivo de audio grabado',
        validators=[validate_audio_upload],
    )
    
    texto_transcrito = models.TextField(
        help_text='Texto transcrito del audio'
    )
    
    # Entidades extraídas: {ayuno: "8 horas", alergias: ["Penicilina"], ...}
    entidades_extraidas = models.JSONField(
        default=dict,
        help_text='Entidades clave extraídas del texto (ayuno, alergias, medicamentos, etc.)'
    )
    
    confianza_transcripcion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Nivel de confianza de la transcripción (0-1)'
    )
    
    duracion_audio = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duración del audio en segundos'
    )
    
    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transcripciones_voz_creadas'
    )
    
    orden_asociada = models.ForeignKey(
        'core.OrdenDeServicio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transcripcion_voz',
        help_text='Orden LIMS (core) asociada a esta transcripción'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Transcripción de Voz'
        verbose_name_plural = 'Transcripciones de Voz'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Transcripción - {self.fecha_creacion.strftime('%Y-%m-%d %H:%M')}"
