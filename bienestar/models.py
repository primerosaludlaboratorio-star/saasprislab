from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

Usuario = get_user_model()


# ==============================================================================
# MÓDULO 'ESPACIO SEGURO' - BIENESTAR Y SALUD MENTAL
# ==============================================================================
class DiarioEmocional(models.Model):
    """
    Diario emocional privado con detección de riesgo.
    Sistema de alertas para situaciones críticas.
    """
    NIVEL_RIESGO_CHOICES = [
        ('VERDE', 'Bienestar/Normal (Privado)'),
        ('AMARILLO', 'Estrés/Ansiedad (Sugerir contenido)'),
        ('ROJO_VIDA', 'Riesgo de suicidio/autolesión (ALERTA JONATHAN)'),
        ('ROJO_VIOLENCIA', 'Violencia doméstica/externa (ALERTA JONATHAN)'),
        ('ROJO_ACOSO', 'Acoso laboral/sexual (ALERTA JONATHAN)'),
        ('ROJO_SUSTANCIAS', 'Consumo crítico (ALERTA JONATHAN)'),
    ]
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='entradas_diario',
        verbose_name="Usuario",
        help_text="Usuario que escribe esta entrada"
    )
    fecha = models.DateField(
        default=timezone.now,
        verbose_name="Fecha",
        help_text="Fecha de la entrada"
    )
    contenido_privado = models.TextField(
        verbose_name="Contenido Privado",
        help_text="Contenido del diario (simula cifrado visual en admin)"
    )
    sentimiento_ia = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Sentimiento IA",
        help_text="Análisis de sentimiento generado por IA"
    )
    nivel_riesgo = models.CharField(
        max_length=20,
        choices=NIVEL_RIESGO_CHOICES,
        default='VERDE',
        verbose_name="Nivel de Riesgo",
        help_text="Nivel de riesgo detectado (CRÍTICO: alerta a Jonathan)"
    )
    
    # Metadatos
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Actualización"
    )
    alerta_enviada = models.BooleanField(
        default=False,
        verbose_name="Alerta Enviada",
        help_text="Indica si se envió alerta a Jonathan por nivel de riesgo crítico"
    )
    
    # Blindaje H-011: Campos para anonimización NOM-035
    anonimizado = models.BooleanField(
        default=False,
        verbose_name="Anonimizado (NOM-035)",
        help_text="Indica si el registro fue anonimizado por retención de datos"
    )
    fecha_anonimizacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Anonimización",
        help_text="Fecha en que se anonimizó el registro"
    )
    
    class Meta:
        verbose_name = "Entrada de Diario Emocional"
        verbose_name_plural = "Entradas de Diario Emocional"
        ordering = ['-fecha', '-fecha_creacion']
        unique_together = [['usuario', 'fecha']]  # Una entrada por usuario por día
    
    def __str__(self):
        riesgo_icon = {
            'VERDE': '🟢',
            'AMARILLO': '🟡',
            'ROJO_VIDA': '🔴',
            'ROJO_VIOLENCIA': '🔴',
            'ROJO_ACOSO': '🔴',
            'ROJO_SUSTANCIAS': '🔴',
        }
        icon = riesgo_icon.get(self.nivel_riesgo, '⚪')
        return f"{icon} {self.usuario.username} - {self.fecha} ({self.get_nivel_riesgo_display()})"
    
    def es_critico(self):
        """Verifica si el nivel de riesgo es crítico (requiere alerta)."""
        return self.nivel_riesgo.startswith('ROJO_')


class RecursoCrecimiento(models.Model):
    """
    Recursos de crecimiento personal (videos, PDFs, artículos).
    Contenido de ayuda para diferentes áreas de bienestar.
    """
    CATEGORIA_CHOICES = [
        ('FINANZAS', 'Finanzas'),
        ('EMOCIONAL', 'Emocional'),
        ('SALUD', 'Salud'),
        ('PROFESIONAL', 'Profesional'),
        ('RELACIONES', 'Relaciones'),
        ('OTRO', 'Otro'),
    ]
    
    titulo = models.CharField(
        max_length=255,
        verbose_name="Título",
        help_text="Título del recurso"
    )
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default='OTRO',
        verbose_name="Categoría"
    )
    url_contenido = models.URLField(
        verbose_name="URL del Contenido",
        help_text="URL del video, PDF o artículo"
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción",
        help_text="Descripción breve del recurso"
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Recurso Activo"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    
    class Meta:
        verbose_name = "Recurso de Crecimiento"
        verbose_name_plural = "Recursos de Crecimiento"
        ordering = ['categoria', 'titulo']
    
    def __str__(self):
        return f"{self.get_categoria_display()} - {self.titulo}"
