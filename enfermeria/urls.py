"""
URLs para el módulo de Enfermería
"""
from django.urls import path
from . import views

app_name = 'enfermeria'

urlpatterns = [
    path('', views.dashboard_enfermeria, name='dashboard_enfermeria'),
    path('lista-triage/', views.lista_pacientes_triage, name='lista_pacientes_triage'),
    path('capturar-signos/<int:cita_id>/', views.capturar_signos_vitales, name='capturar_signos_vitales'),
    path('historial/<int:paciente_id>/', views.historial_signos_paciente, name='historial_signos_paciente'),
    path('graficas/<int:paciente_id>/', views.graficas_tendencias, name='graficas_tendencias'),
    path('alertas/', views.alertas_signos_criticos, name='alertas_signos_criticos'),
]
