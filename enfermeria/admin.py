from django.contrib import admin
from core.models import SignosVitales, CitaMedica


@admin.register(SignosVitales)
class SignosVitalesAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'presion_arterial_sistolica', 'presion_arterial_diastolica',
                    'temperatura', 'frecuencia_cardiaca', 'peso', 'imc', 'fecha_registro')
    list_filter = ('empresa', 'fecha_registro')
    search_fields = ('paciente__nombre', 'paciente__apellido_paterno')
    date_hierarchy = 'fecha_registro'
    readonly_fields = ('imc', 'fecha_registro')


@admin.register(CitaMedica)
class CitaMedicaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'fecha_cita', 'hora_cita', 'estado', 'empresa')
    list_filter = ('estado', 'empresa', 'fecha_cita')
    search_fields = ('paciente__nombre', 'paciente__apellido_paterno')
    date_hierarchy = 'fecha_cita'
