from django.urls import path
from core import views
from core.api_contracts.ninja_api import api as api_contracts_v3
from core.views.cron_tasks import (
    cron_check_metrologia,
    cron_check_stock_critico,
    cron_verify_escudo_clinico,
)
from farmacia.views.corte_caja_api import api_corte_caja_unificado
from ._helpers import lazy_view

urlpatterns = [
    # FASE 3: Contratos API estrictos — Django Ninja
    path('api/v3/', api_contracts_v3.urls),

    # FASE 8: Corte de caja unificado (Lab + Farmacia)
    path('api/caja/corte-unificado/', api_corte_caja_unificado, name='corte_caja_unificado'),

    # PRIS SENTINEL SHIELD — Telemetría Frontend
    path('api/sentinel/shield-telemetry/', views.api_shield_telemetry, name='sentinel_shield_telemetry'),
    path('api/sentinel/reset/', views.api_sentinel_reset, name='sentinel_reset'),
    path('api/sentinel/diagnostico/', views.api_sentinel_diagnostico, name='sentinel_diagnostico'),

    # Notificaciones transversales
    path('api/notificaciones/crear/', lazy_view('core.views.notificaciones.api_crear_notificacion'), name='api_crear_notificacion'),

    # Log de errores frontend
    path('api/log-frontend-error/', views.log_frontend_error, name='log_frontend_error'),

    # CRON internos (triggerados por scheduler VPS)
    path('cron/check-metrologia/', cron_check_metrologia, name='cron_check_metrologia'),
    path('cron/check-stock-critico/', cron_check_stock_critico, name='cron_check_stock_critico'),
    path('cron/verify-escudo-clinico/', cron_verify_escudo_clinico, name='cron_verify_escudo_clinico'),
]
