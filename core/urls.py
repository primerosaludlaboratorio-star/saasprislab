# core/urls.py
# URLs del módulo core con namespace

from django.urls import path
from core import views
from core.views import blindaje_expediente as blindaje_views

app_name = 'core'

urlpatterns = [
    # Historial de Resultados
    path('historial-resultados/', views.historial_resultados, name='historial_resultados'),
    path('historial-resultados/<int:paciente_id>/', views.historial_resultados, name='historial_resultados_paciente'),
    path('historial-resultados/<int:paciente_id>/api/grafica/<int:estudio_id>/', views.api_resultados_grafica, name='api_resultados_grafica'),
    path('historial-resultados/<int:paciente_id>/comparar/', views.comparar_resultados, name='comparar_resultados'),
    
    # Búsqueda de Pacientes
    path('buscar-paciente/', views.buscar_paciente, name='buscar_paciente'),
    
    # 🔒 BLINDAJE v2.0 — Arquitectura de Blindaje de Expedientes
    path('blindaje/nota/<int:nota_id>/pre-sellar/', blindaje_views.pre_sellar_nota, name='pre_sellar_nota'),
    path('blindaje/nota/<int:nota_id>/sellar/', blindaje_views.sellar_con_pin, name='sellar_con_pin'),
    path('blindaje/nota/<int:nota_id>/verificar/', blindaje_views.verificar_nota, name='verificar_nota'),
    path('blindaje/nota/<int:nota_id>/desbloquear/', blindaje_views.desbloqueo_forense, name='desbloqueo_forense'),
    path('blindaje/medico/configurar-pin/', blindaje_views.configurar_pin_lab, name='configurar_pin_lab'),
    path('blindaje/cie10/buscar/', blindaje_views.buscar_cie10, name='buscar_cie10'),
    path('verificar/<uuid:token>/', blindaje_views.verificar_publico, name='verificar_publico'),
]
