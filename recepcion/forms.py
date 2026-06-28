"""
Formularios para el modulo de Recepcion
"""
from django import forms
from core.models import Paciente, CitaMedica, Medico


class PacienteForm(forms.ModelForm):
    """Formulario para registrar/editar pacientes."""

    acepta_privacidad_y_tratamiento = forms.BooleanField(
        required=True,
        label=(
            'Declaro haber leído el aviso de privacidad de la institución y acepto el tratamiento '
            'de mis datos personales para fines de atención médica y laboratorio clínico, '
            'conforme a la LFPDPPP.'
        ),
        error_messages={
            'required': (
                'Debe aceptar el aviso de privacidad y el tratamiento de datos para registrar al paciente.'
            ),
        },
        widget=forms.CheckboxInput(
            attrs={'class': 'form-check-input', 'required': True},
        ),
    )

    class Meta:
        model = Paciente
        fields = [
            'nombres', 'apellido_paterno', 'apellido_materno',
            'fecha_nacimiento', 'sexo', 'telefono', 'email',
            'consentimiento_marketing',
        ]
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre(s)'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Paterno'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Materno'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(55) 1234-5678'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@ejemplo.com'}),
            'consentimiento_marketing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'consentimiento_marketing': 'Acepto recibir comunicaciones de salud y marketing (LFPDPPP)',
        }
        help_texts = {
            'consentimiento_marketing': 'Puede revocar este consentimiento en cualquier momento desde su perfil.',
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)


class CitaMedicaForm(forms.ModelForm):
    """Formulario para agendar citas medicas."""

    class Meta:
        model = CitaMedica
        fields = ['paciente', 'medico', 'fecha_cita', 'hora_cita', 'motivo']
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-select'}),
            'medico': forms.Select(attrs={'class': 'form-select'}),
            'fecha_cita': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora_cita': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Motivo de la consulta'}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.empresa:
            self.fields['paciente'].queryset = Paciente.objects.filter(empresa=self.empresa).order_by('nombres', 'apellido_paterno')
            self.fields['medico'].queryset = Medico.objects.filter(empresa=self.empresa).order_by('nombre_completo')
        else:
            self.fields['paciente'].queryset = Paciente.objects.none()
            self.fields['medico'].queryset = Medico.objects.none()
