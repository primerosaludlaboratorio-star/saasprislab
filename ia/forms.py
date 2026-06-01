"""
Formularios del Módulo de Inteligencia Artificial.
"""

from django import forms
from .models import CotizacionOCR, TranscripcionVoz


class ProcesarRecetaForm(forms.ModelForm):
    """
    Formulario para subir y procesar una receta médica con OCR.
    """
    class Meta:
        model = CotizacionOCR
        fields = ['imagen_receta']
        widgets = {
            'imagen_receta': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'id_imagen_receta'
            })
        }
        labels = {
            'imagen_receta': '📸 Imagen de la Receta'
        }
        help_texts = {
            'imagen_receta': 'Sube una foto clara de la receta médica (JPG, PNG, PDF)'
        }


class TranscribirAudioForm(forms.ModelForm):
    """
    Formulario para subir y transcribir audio médico.
    """
    class Meta:
        model = TranscripcionVoz
        fields = ['audio']
        widgets = {
            'audio': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'audio/*,.wav,.mp3,.m4a',
                'id': 'id_audio'
            })
        }
        labels = {
            'audio': '🎙️ Archivo de Audio'
        }
        help_texts = {
            'audio': 'Sube un archivo de audio de la consulta (WAV, MP3, M4A)'
        }


class ConsultaAsistenteForm(forms.Form):
    """
    Formulario para consultar al asistente médico con IA.
    """
    pregunta = forms.CharField(
        label='💬 Pregunta al Asistente',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Ejemplo: ¿Cómo se diagnostica la diabetes tipo 2?'
        }),
        help_text='Haz cualquier pregunta sobre diagnósticos, tratamientos, o procedimientos médicos.'
    )
    
    contexto = forms.CharField(
        label='📋 Contexto Adicional (Opcional)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Paciente masculino, 45 años, diabético...'
        }),
        help_text='Proporciona información del paciente para respuestas más específicas.'
    )
