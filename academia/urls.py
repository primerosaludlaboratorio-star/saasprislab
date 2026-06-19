from django.urls import path

from . import views

app_name = "academia"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("cursos/<slug:slug>/", views.curso_detalle, name="curso_detalle"),
    path("api/", views.api_root, name="api_root"),
    path("api/videos/<int:video_id>/reproducir/", views.api_video_reproducir, name="api_video_reproducir"),
    path("api/videos/<int:video_id>/heartbeat/", views.api_heartbeat, name="api_heartbeat"),
    path("accesos/otorgar/", views.otorgar_acceso, name="otorgar_acceso"),
    path("reportes/colaborador/<int:usuario_id>/", views.reporte_colaborador, name="reporte_colaborador"),
]
