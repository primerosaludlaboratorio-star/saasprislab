from django.urls import path

from . import views

app_name = "logistica"

urlpatterns = [
    # Rutas de recolección
    path("", views.monitor_rutas, name="monitor_rutas"),
    path("mapa/", views.mapa_rutas, name="mapa_rutas"),
    path("visita/<int:visita_id>/asignar/", views.asignar_visita, name="asignar_visita"),
    
    # Sistema de Traspasos/Transferencias
    path("transferencias/", views.lista_transferencias, name="lista_transferencias"),
    path("transferencias/crear/", views.crear_transferencia, name="crear_transferencia"),
    path("transferencias/<int:transferencia_id>/", views.detalle_transferencia, name="detalle_transferencia"),
    path("transferencias/<int:transferencia_id>/agregar-producto/", views.agregar_producto_transferencia, name="agregar_producto_transferencia"),
    path("transferencias/<int:transferencia_id>/enviar/", views.enviar_transferencia, name="enviar_transferencia"),
    path("transferencias/<int:transferencia_id>/recibir/", views.recibir_transferencia, name="recibir_transferencia"),
    path("rastrear/<uuid:token>/", views.rastrear_transferencia, name="rastrear_transferencia"),
]

