"""
URLs del módulo de Seguridad
"""

from django.urls import path
from . import views

app_name = 'seguridad'

urlpatterns = [
    # ========== AUTENTICACIÓN 2FA ==========
    path('2fa/', views.configuracion_2fa, name='configuracion_2fa'),
    path('2fa/activar-totp/', views.activar_totp, name='activar_totp'),
    path('2fa/confirmar-totp/<int:dispositivo_id>/', views.confirmar_totp, name='confirmar_totp'),
    path('2fa/desactivar-totp/<int:dispositivo_id>/', views.desactivar_totp, name='desactivar_totp'),
    path('2fa/codigos-backup/', views.mostrar_codigos_backup, name='mostrar_codigos_backup'),
    path('2fa/regenerar-codigos/', views.regenerar_codigos_backup, name='regenerar_codigos_backup'),
    
    # ========== GESTIÓN DE SESIONES ==========
    path('sesiones/', views.sesiones_activas, name='sesiones_activas'),
    path('sesiones/cerrar/<int:sesion_id>/', views.cerrar_sesion_remota, name='cerrar_sesion_remota'),
    path('sesiones/cerrar-todas/', views.cerrar_todas_las_sesiones, name='cerrar_todas_las_sesiones'),
    
    # ========== AUDITORÍA ==========
    path('auditoria/', views.dashboard_auditoria, name='dashboard_auditoria'),
    path('auditoria/logs/', views.logs_auditoria, name='logs_auditoria'),
    path('rastro-paciente/', views.rastro_paciente, name='rastro_paciente'),
    
    # ========== API ENDPOINTS ==========
    path('api/verificar-2fa/', views.api_verificar_codigo_2fa, name='api_verificar_2fa'),
    path('api/estadisticas/', views.api_estadisticas_seguridad, name='api_estadisticas'),
    path('api/panic/', views.panic_button, name='panic_button'),
]
