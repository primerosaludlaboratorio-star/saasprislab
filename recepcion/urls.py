"""
URLs para el módulo de Recepción
"""
from django.urls import path
from . import views

app_name = 'recepcion'

urlpatterns = [
    path('', views.dashboard_recepcion, name='dashboard_recepcion'),
    path('registrar-paciente/', views.registrar_paciente, name='registrar_paciente'),
    path('buscar-paciente/', views.buscar_paciente, name='buscar_paciente'),
    path('agendar-cita/', views.agendar_cita, name='agendar_cita'),
    path('check-in/<int:cita_id>/', views.check_in_paciente, name='check_in_paciente'),
    path('lista-espera/', views.lista_espera, name='lista_espera'),
    path('cobrar/<int:cita_id>/', views.cobrar_consulta, name='cobrar_consulta'),
]
