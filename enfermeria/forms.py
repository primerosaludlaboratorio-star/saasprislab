"""
Formularios para el modulo de Enfermeria
"""
from django import forms
from core.models import SignosVitales


class SignosVitalesForm(forms.ModelForm):
    """Formulario para captura de signos vitales."""

    class Meta:
        model = SignosVitales
        fields = [
            'peso', 'talla', 'presion_arterial_sistolica', 'presion_arterial_diastolica',
            'temperatura', 'frecuencia_cardiaca', 'frecuencia_respiratoria',
            'saturacion_oxigeno', 'glucosa_capilar', 'perimetro_abdominal', 'observaciones'
        ]
        widgets = {
            'peso': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'kg'}),
            'talla': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'm'}),
            'presion_arterial_sistolica': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'mmHg'}),
            'presion_arterial_diastolica': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'mmHg'}),
            'temperatura': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '°C'}),
            'frecuencia_cardiaca': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'lpm'}),
            'frecuencia_respiratoria': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'rpm'}),
            'saturacion_oxigeno': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '%'}),
            'glucosa_capilar': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'mg/dL'}),
            'perimetro_abdominal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'cm'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones...'}),
        }

    def clean(self):
        cleaned_data = super().clean()

        peso = cleaned_data.get('peso')
        if peso and (peso < 0.5 or peso > 300):
            self.add_error('peso', 'El peso debe estar entre 0.5 y 300 kg.')

        ps = cleaned_data.get('presion_arterial_sistolica')
        if ps and ps > 250:
            self.add_error('presion_arterial_sistolica', 'Valor inusualmente alto. Verificar.')

        temp = cleaned_data.get('temperatura')
        if temp and (temp < 33 or temp > 43):
            self.add_error('temperatura', 'Temperatura fuera de rango (33-43 C).')

        return cleaned_data
