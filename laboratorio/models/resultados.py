"""
MÓDULO DE LABORATORIO - Parámetros, resultados e historial clínico (ISO 15189).
PILAR 2: INMUTABILIDAD CLÍNICA (ISO 15189)
Incluye: Historial de Resultados para trazabilidad forense.
"""
import hashlib
import json

from django.conf import settings
from django.db import models

from .ordenes import Orden


class Parametro(models.Model):
    """
    Parámetro de un estudio con sus rangos de referencia.
    Permite múltiples parámetros por estudio (ej: Glucosa en ayunas, Glucosa postprandial).
    """
    estudio = models.ForeignKey(
        'laboratorio.Estudio',
        on_delete=models.CASCADE,
        related_name='parametros',
        help_text='Estudio al que pertenece este parámetro.',
    )
    nombre = models.CharField(
        max_length=150,
        help_text='Nombre del parámetro (ej: "Glucosa", "Hemoglobina").',
    )
    codigo_interfaz = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Código que envía el equipo de laboratorio (ej: "GLU", "HGB"). Usado para mapeo automático de resultados.',
    )
    valor_ref_min = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor mínimo de referencia para este parámetro.',
    )
    valor_ref_max = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor máximo de referencia para este parámetro.',
    )
    unidades = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Unidades de medición (ej. 'mg/dL', 'mmol/L').",
    )

    # Metadatos del catálogo clínico original
    TIPO_RESULTADO_CHOICES = [
        ('Numerico', 'Numérico'),
        ('Texto', 'Texto'),
        ('Opciones', 'Opciones predefinidas'),
    ]
    TIPO_REFERENCIA_CHOICES = [
        ('Rango numerico', 'Rango numérico'),
        ('Texto libre', 'Texto libre'),
        ('Sin referencia', 'Sin referencia'),
    ]
    abreviatura = models.CharField(
        max_length=30, blank=True, null=True,
        help_text='Código corto del parámetro (ej: leuct, RBC, HGB). Clave en HL7/ASTM.',
        db_index=True,
    )
    departamento = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Sección de laboratorio (Hematología, Bioquímica Clínica, etc.).',
        db_index=True,
    )
    tipo_muestra = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Tipo de muestra requerida (ej: SANGRE TOTAL-TUBO LILA).',
    )
    tipo_resultado = models.CharField(
        max_length=20, choices=TIPO_RESULTADO_CHOICES, default='Numerico',
        help_text='Forma de captura del resultado.',
    )
    tipo_referencia = models.CharField(
        max_length=30, choices=TIPO_REFERENCIA_CHOICES, default='Rango numerico',
        help_text='Tipo de rango de referencia para este parámetro.',
    )
    decimales = models.SmallIntegerField(
        default=2,
        help_text='Número de decimales al reportar/validar el resultado.',
    )
    formula = models.CharField(
        max_length=500, blank=True, null=True,
        help_text='Fórmula de cálculo si el parámetro es derivado (ej: VCM = HCT/RBC*10).',
    )
    imprimir_en_negritas = models.BooleanField(
        default=False,
        help_text='Si True, el resultado se imprime en negritas en el reporte PDF.',
    )
    valor_normalidad_texto = models.TextField(
        blank=True, null=True,
        help_text='Rango de referencia en texto libre para parámetros cualitativos.',
    )
    resultado_opciones = models.CharField(
        max_length=500, blank=True, null=True,
        help_text='Opciones de resultado separadas por | (para tipo Opciones).',
    )
    es_antibiograma = models.BooleanField(
        default=False,
        help_text='Si True, el resultado es un antibiograma (sensibilidad a antibióticos).',
    )
    imprimir_metodo = models.BooleanField(
        default=False,
        help_text='Si True, el método analítico se imprime en el reporte PDF.',
    )
    notas = models.TextField(
        blank=True, null=True,
        help_text='Notas adicionales del parámetro para el reporte.',
    )
    indicaciones = models.TextField(
        blank=True, null=True,
        help_text='Instrucciones de preparación del paciente para este parámetro.',
    )
    orden_impresion = models.PositiveSmallIntegerField(
        default=0,
        help_text='Orden de aparición en el reporte PDF. Menor número = primero.',
    )
    etiqueta_interfaz = models.CharField(
        max_length=30, blank=True, null=True,
        help_text='Nombre de la etiqueta en el analizador (puede diferir del código interfaz).',
    )

    class Meta:
        verbose_name = 'Parámetro'
        verbose_name_plural = 'Parámetros'
        ordering = ['estudio__nombre', 'orden_impresion', 'nombre']
        indexes = [
            models.Index(fields=['codigo_interfaz'], name='lab_param_codigo_interfaz_idx'),
            models.Index(fields=['estudio', 'orden_impresion'], name='lab_param_estudio_orden_idx'),
        ]

    def __str__(self) -> str:
        return f'{self.nombre} ({self.estudio.nombre})'


class Resultado(models.Model):
    """
    Resultado capturado para un estudio dentro de una orden.
    Soporta validación automática de valores anormales.
    """
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name='resultados',
    )
    estudio = models.ForeignKey(
        'laboratorio.Estudio',
        on_delete=models.PROTECT,
        related_name='resultados',
    )
    valor_obtenido = models.CharField(
        max_length=100,
        help_text='Valor reportado para este estudio (texto libre).',
    )
    valor = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Alias para valor_obtenido (compatibilidad).',
    )
    es_anormal = models.BooleanField(
        default=False,
        help_text='Marca si el resultado está fuera del rango de referencia (aparecerá con * en PDF).',
    )
    notas_ia = models.TextField(
        blank=True,
        null=True,
        help_text='Observación específica de la AI para este parámetro.',
    )
    # ── ISO 15189 — Campos de validación crítica ──────────────────────────────
    es_critico = models.BooleanField(
        default=False, db_index=True,
        help_text='True cuando el valor supera umbrales de pánico (ISO 15189).',
    )
    alerta_critica_enviada = models.BooleanField(
        default=False,
        help_text='True cuando ya se notificó al QC/médico sobre este valor crítico.',
    )
    rango_usado = models.ForeignKey(
        'laboratorio.RangoReferenciaParametro',
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='resultados_validados',
        help_text='Rango dinámico ISO 15189 que se usó para la validación.',
    )
    parametro_ref = models.ForeignKey(
        'laboratorio.Parametro',
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='resultados_parametro',
        help_text='Parámetro de referencia (para laboratorio detallado).',
    )
    origen_hl7 = models.ForeignKey(
        'laboratorio.ResultadoHL7',
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='resultados_integrados',
        help_text='Resultado HL7/ASTM origen si fue integrado desde equipo.',
    )

    class Meta:
        verbose_name = 'Resultado de Estudio'
        verbose_name_plural = 'Resultados de Estudios'
        ordering = ['orden_id', 'estudio__nombre']
        indexes = [
            models.Index(fields=['orden', 'parametro_ref'], name='lab_resultado_orden_param_idx'),
            models.Index(fields=['es_critico'], name='lab_resultado_critico_idx'),
        ]

    def __str__(self) -> str:
        return f'{self.estudio.nombre} = {self.valor_obtenido} (Orden {self.orden_id})'

    def save(self, *args, **kwargs):
        """
        Auto-valida el resultado contra rangos dinámicos ISO 15189 (si existen)
        y fallback a rangos estáticos del Estudio.
        """
        # Sincronizar alias
        if self.valor_obtenido and not self.valor:
            self.valor = self.valor_obtenido

        if self.estudio and self.valor_obtenido:
            try:
                from laboratorio.services.iso15189 import validar_resultado, disparar_alerta_critica

                # Intentar obtener parametro_ref desde el estudio
                parametro_id = getattr(self.parametro_ref, 'id', None)

                # Obtener datos del paciente para rangos dinámicos
                edad = None
                sexo = None
                try:
                    orden = self.orden
                    if hasattr(orden, 'paciente') and orden.paciente:
                        from datetime import date
                        if orden.paciente.fecha_nacimiento:
                            hoy = date.today()
                            fn = orden.paciente.fecha_nacimiento
                            edad = (hoy - fn).days / 365.25
                        sexo = getattr(orden.paciente, 'sexo', None)
                except (AttributeError, TypeError, ValueError):
                    # Errores específicos al acceder a datos del paciente
                    pass

                if parametro_id:
                    validacion = validar_resultado(
                        parametro_id=parametro_id,
                        valor_str=self.valor_obtenido,
                        edad_paciente=edad,
                        sexo_paciente=sexo,
                    )
                    self.es_anormal = validacion.es_anormal
                    self.es_critico = validacion.es_critico

                    if validacion.es_critico and not self.alerta_critica_enviada:
                        orden_id = getattr(self, 'orden_id', None)
                        disparar_alerta_critica(
                            resultado_id=self.pk or 0,
                            validacion=validacion,
                            orden_id=orden_id,
                            parametro_nombre=getattr(self.parametro_ref, 'nombre', ''),
                        )
                        self.alerta_critica_enviada = True
                else:
                    # Fallback estático
                    valor_num = float(self.valor_obtenido.replace(',', '').strip())
                    est = self.estudio
                    if est.valor_minimo is not None and valor_num < float(est.valor_minimo):
                        self.es_anormal = True
                    elif est.valor_maximo is not None and valor_num > float(est.valor_maximo):
                        self.es_anormal = True
                    else:
                        self.es_anormal = False

            except (ValueError, AttributeError):
                pass

        super().save(*args, **kwargs)


# ==============================================================================
# PILAR 2: INMUTABILIDAD CLÍNICA (ISO 15189)
# MODELO DE HISTORIAL DE RESULTADOS - LA CAJA NEGRA DEL LABORATORIO
# ==============================================================================

class HistorialResultados(models.Model):
    """
    Registro inmutable de cambios en resultados de laboratorio.
    
    Cumplimiento: ISO 15189 (Gestión de Calidad en Laboratorios Clínicos)
    Principio: La verdad original nunca se pierde. Todo cambio es rastreado.
    
    Casos de uso:
    - Corrección de errores de captura
    - Recalibración de equipos
    - Auditorías de COFEPRIS
    - Litigios médico-legales
    """
    
    # Relación con el resultado actual
    resultado_asociado = models.ForeignKey(
        'core.ResultadoParametro',
        on_delete=models.PROTECT,
        related_name='historial_cambios_lab',  # Changed to avoid clash
        verbose_name="Resultado Asociado",
        help_text="El resultado que fue modificado"
    )
    
    # Datos del cambio
    valor_anterior = models.TextField(
        verbose_name="Valor Anterior",
        help_text="Valor original antes del cambio (puede ser numérico o texto)"
    )
    valor_nuevo = models.TextField(
        verbose_name="Valor Nuevo",
        help_text="Valor después del cambio"
    )
    
    # Trazabilidad forense
    motivo_cambio = models.TextField(
        verbose_name="Motivo del Cambio",
        help_text="Explicación obligatoria del porqué se realizó la modificación"
    )
    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cambios_resultados_realizados',
        verbose_name="Usuario Responsable",
        help_text="Químico o supervisor que autorizó el cambio"
    )
    fecha_hora_cambio = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y Hora del Cambio",
        help_text="Timestamp inmutable del momento exacto del cambio"
    )
    
    # Contexto del cambio
    resultado_validado_previamente = models.BooleanField(
        default=False,
        verbose_name="Resultado Ya Validado",
        help_text="True si el resultado ya había sido validado antes del cambio (más crítico)"
    )
    resultado_entregado_previamente = models.BooleanField(
        default=False,
        verbose_name="Resultado Ya Entregado",
        help_text="True si el resultado ya fue entregado al paciente (altamente crítico)"
    )
    
    # Hash de integridad (opcional pero recomendado)
    hash_integridad = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name="Hash de Integridad",
        help_text="SHA-256 del cambio para verificación forense"
    )
    
    # Auditoría adicional
    ip_origen = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="IP de Origen",
        help_text="Dirección IP desde donde se realizó el cambio"
    )
    observaciones_supervisor = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones del Supervisor",
        help_text="Notas adicionales del supervisor que autorizó (si aplica)"
    )
    
    class Meta:
        verbose_name = "Historial de Resultado"
        verbose_name_plural = "Historial de Resultados"
        ordering = ['-fecha_hora_cambio']
        indexes = [
            models.Index(fields=['resultado_asociado', '-fecha_hora_cambio']),
            models.Index(fields=['usuario_responsable', '-fecha_hora_cambio']),
            models.Index(fields=['-fecha_hora_cambio']),
        ]
        permissions = [
            ("ver_historial_resultados", "Puede ver el historial completo de cambios de resultados"),
            ("modificar_resultados_validados", "Puede modificar resultados ya validados"),
        ]
    
    def __str__(self):
        return f"Cambio en Resultado #{self.resultado_asociado_id} por {self.usuario_responsable.username} el {self.fecha_hora_cambio.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe save() para generar hash de integridad automáticamente.
        """
        if not self.hash_integridad:
            self.hash_integridad = self.generar_hash_integridad()
        
        super().save(*args, **kwargs)
    
    def generar_hash_integridad(self):
        """
        Genera un hash SHA-256 del cambio para verificación forense.
        
        Componentes del hash:
        - ID del resultado
        - Valor anterior
        - Valor nuevo
        - Usuario responsable
        - Timestamp
        """
        datos_para_hash = {
            'resultado_id': self.resultado_asociado_id,
            'valor_anterior': self.valor_anterior,
            'valor_nuevo': self.valor_nuevo,
            'usuario_id': self.usuario_responsable_id,
            'timestamp': str(self.fecha_hora_cambio) if self.fecha_hora_cambio else ''
        }
        
        # Serializar a JSON ordenado (para consistencia)
        json_datos = json.dumps(datos_para_hash, sort_keys=True)
        
        # Generar hash SHA-256
        return hashlib.sha256(json_datos.encode('utf-8')).hexdigest()
    
    @classmethod
    def registrar_cambio(cls, resultado, valor_anterior, valor_nuevo, motivo, usuario, ip_origen=None):
        """
        Método de clase para registrar un cambio de forma segura.
        
        Args:
            resultado: Instancia de ResultadoParametro que cambia
            valor_anterior: Valor antes del cambio (string o número)
            valor_nuevo: Valor después del cambio
            motivo: Razón del cambio (obligatorio)
            usuario: Usuario responsable del cambio
            ip_origen: IP desde donde se realizó (opcional)
        
        Returns:
            Instancia de HistorialResultados creada
        """
        from core.models import OrdenDeServicio
        
        # Determinar si el resultado ya estaba validado o entregado
        orden = resultado.orden
        resultado_validado = resultado.validado
        resultado_entregado = orden.estado in ['ENTREGADO', 'RESULTADOS_LISTOS']
        
        # Crear registro histórico
        historial = cls(
            resultado_asociado=resultado,
            valor_anterior=str(valor_anterior),
            valor_nuevo=str(valor_nuevo),
            motivo_cambio=motivo,
            usuario_responsable=usuario,
            resultado_validado_previamente=resultado_validado,
            resultado_entregado_previamente=resultado_entregado,
            ip_origen=ip_origen
        )
        historial.save()
        
        return historial
