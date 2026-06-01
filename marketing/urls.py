from django.urls import path
from . import views
from . import views_tracking

app_name = 'marketing'  # Namespace crítico

urlpatterns = [
    # Público — pixel / beacon (204, sin cuerpo); debe permanecer ligero
    path(
        "api/track/",
        views_tracking.track_pixel_204,
        name="marketing_track_pixel",
    ),
    path("", views.dashboard_marketing, name="dashboard_marketing"),
    path("entrenamiento/", views.entrenamiento_ia, name="entrenamiento_ia"),
    
    # Campañas
    path("campanas/", views.lista_campanas, name="lista_campanas"),
    path("campanas/crear/", views.crear_campana, name="crear_campana"),
    path("campanas/<int:campana_id>/editar/", views.editar_campana, name="editar_campana"),
    path("campanas/dashboard/", views.dashboard_campanas, name="dashboard_campanas"),
    
    # Cupones
    path("cupones/", views.lista_cupones, name="lista_cupones"),
    path("cupones/generar/", views.generar_cupon, name="generar_cupon"),
    
    # Contactos
    path("contactos/", views.lista_contactos, name="lista_contactos"),
    path("contactos/importar/", views.importar_contactos, name="importar_contactos"),
    
    # APIs
    path("api/generar-cupon/", views.api_generar_cupon, name="api_generar_cupon"),
    path("api/aplicar-cupon/", views.api_aplicar_cupon, name="api_aplicar_cupon"),
    path("api/crear-campana/", views.api_crear_campana, name="api_crear_campana"),

    # IA de Reactivación
    path("ia/reactivacion/", views.dashboard_reactivacion_ia, name="reactivacion_ia"),
    path("api/ia/pacientes-inactivos/", views.api_detectar_pacientes_inactivos, name="api_pacientes_inactivos"),
]

