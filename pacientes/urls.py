"""
URLs del Módulo Pacientes - Historial 360° + Portal del Paciente
Sistema de Expediente Clínico Electrónico (ECE)
"""
from django.urls import path
from pacientes import views, portal_views

app_name = 'pacientes'

urlpatterns = [
    # ===========================================================================
    # LISTADO Y BÚSQUEDA DE PACIENTES (STAFF)
    # ===========================================================================
    path('', views.lista_pacientes, name='lista_pacientes'),
    path('nuevo/', views.crear_paciente, name='crear_paciente'),
    path('buscar/', views.buscar_paciente, name='buscar_paciente'),
    
    # ===========================================================================
    # HISTORIAL 360° - VISTA PRINCIPAL (STAFF)
    # ===========================================================================
    path('<int:paciente_id>/historial-360/', 
         views.historial_360_paciente, 
         name='historial_360'),
    
    # ===========================================================================
    # VISTAS ESPECIALIZADAS (STAFF)
    # ===========================================================================
    path('<int:paciente_id>/timeline/', 
         views.timeline_consultas, 
         name='timeline_consultas'),
    
    path('<int:paciente_id>/graficas-signos/', 
         views.graficas_signos_vitales, 
         name='graficas_signos'),
    
    path('<int:paciente_id>/historia-clinica/', 
         views.historia_clinica_completa, 
         name='historia_clinica'),
    
    # ===========================================================================
    # API - DATOS DINÁMICOS (STAFF)
    # ===========================================================================
    path('api/<int:paciente_id>/datos-graficas/', 
         views.api_datos_graficas_signos, 
         name='api_datos_graficas'),
    
    # ===========================================================================
    # PORTAL DEL PACIENTE (PÚBLICO)
    # ===========================================================================
    path('portal/', portal_views.portal_login, name='portal_login'),
    path('portal/logout/', portal_views.portal_logout, name='portal_logout'),
    path('portal/solicitar-acceso/', portal_views.solicitar_acceso, name='solicitar_acceso'),
    
    # Dashboard y vistas del portal (requieren autenticación de paciente)
    path('portal/inicio/', portal_views.portal_dashboard, name='portal_dashboard'),
    path('portal/mis-consultas/', portal_views.portal_mis_consultas, name='portal_mis_consultas'),
    path('portal/mis-estudios/', portal_views.portal_mis_estudios, name='portal_mis_estudios'),
    path('portal/mis-recetas/', portal_views.portal_mis_recetas, name='portal_mis_recetas'),
    path('portal/mi-perfil/', portal_views.portal_mi_perfil, name='portal_mi_perfil'),
    path('portal/cambiar-password/', portal_views.portal_cambiar_password, name='portal_cambiar_password'),
    
    # Descargas
    path('portal/descargar-resultado/<int:orden_id>/', 
         portal_views.portal_descargar_resultado, 
         name='portal_descargar_resultado'),
]
