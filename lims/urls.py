"""
URLs del módulo LIMS — 4 Ventanas independientes.

Prefijo base: /lims/
  Ventana A — Analitos:  /lims/analitos/
  Ventana B — Perfiles:  /lims/perfiles/
  Ventana C — Paquetes:  /lims/paquetes/
  Ventana D — Precios:   /lims/precios/
  APIs internas:         /lims/api/...
"""
from django.http import JsonResponse
from django.urls import path

from lims.views import analitos as va
from lims.views import perfiles as vb
from lims.views import paquetes as vc
from lims.views import precios  as vd


def _api_perfiles_lista(request):
    """Retorna la lista de perfiles activos para el selector de Ventana C."""
    from lims.models import PerfilLims
    from lims.views.tenant_lims import empresa_lims

    # FIX V8.2 LIMS TENANT
    empresa = empresa_lims(request)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa activa', 'perfiles': []}, status=403)
    perfiles = list(
        PerfilLims.objects.filter(empresa=empresa, activo=True)
        .order_by('nombre')
        .values('id', 'nombre')
    )
    return JsonResponse({'perfiles': perfiles})


urlpatterns = [

    # ── Ventana A: Analitos ───────────────────────────────────────────────────
    path('analitos/',                    va.lista,             name='lims_analitos'),
    path('analitos/<int:pk>/',           va.detalle,           name='lims_analito_detalle'),
    path('analitos/<int:pk>/editar/',    va.editar,            name='lims_analito_editar'),

    # APIs de rangos (AJAX) — ruta detalle antes que la colección
    path('api/analitos/<int:pk>/rangos/<int:rango_pk>/', va.api_rango_item, name='lims_api_rango_item'),
    path('api/analitos/<int:pk>/rangos/', va.api_rangos,       name='lims_api_rangos'),
    path('api/rangos/<int:rango_pk>/eliminar/', va.api_rango_eliminar, name='lims_api_rango_eliminar'),

    # ── Ventana B: Perfiles ───────────────────────────────────────────────────
    path('perfiles/',                    vb.lista,             name='lims_perfiles'),
    path('perfiles/nuevo/',              vb.nuevo,             name='lims_perfil_nuevo'),
    path('perfiles/<int:pk>/',           vb.detalle,           name='lims_perfil_detalle'),
    path('perfiles/<int:pk>/editar/',    vb.editar,            name='lims_perfil_editar'),

    # API Typeahead de analitos (usada por Ventana B y C)
    path('api/analitos/buscar/',         vb.api_buscar_analitos,  name='lims_api_buscar_analitos'),
    path('api/perfiles/',                _api_perfiles_lista,     name='lims_api_perfiles'),

    # APIs de composición de perfil
    path('perfiles/<int:pk>/api/agregar-analito/', vb.api_agregar_analito, name='lims_perfil_agregar_analito'),
    path('perfiles/<int:pk>/api/quitar-analito/<int:analito_pk>/', vb.api_quitar_analito, name='lims_perfil_quitar_analito'),

    # ── Ventana C: Paquetes ───────────────────────────────────────────────────
    path('paquetes/',                    vc.lista,             name='lims_paquetes'),
    path('paquetes/nuevo/',              vc.nuevo,             name='lims_paquete_nuevo'),
    path('paquetes/<int:pk>/',           vc.detalle,           name='lims_paquete_detalle'),
    path('paquetes/<int:pk>/editar/',    vc.editar,            name='lims_paquete_editar'),

    # APIs de composición de paquete
    path('paquetes/<int:pk>/api/agregar-analito/', vc.api_agregar_analito, name='lims_paquete_agregar_analito'),
    path('paquetes/<int:pk>/api/quitar-analito/<int:analito_pk>/', vc.api_quitar_analito, name='lims_paquete_quitar_analito'),
    path('paquetes/<int:pk>/api/agregar-perfil/',  vc.api_agregar_perfil,  name='lims_paquete_agregar_perfil'),
    path('paquetes/<int:pk>/api/quitar-perfil/<int:perfil_pk>/',   vc.api_quitar_perfil,   name='lims_paquete_quitar_perfil'),

    # ── Ventana D: Precios ────────────────────────────────────────────────────
    path('precios/',                     vd.lista,             name='lims_precios'),
    path('precios/<int:precio_pk>/actualizar/', vd.actualizar_precio, name='lims_precio_actualizar'),
    path('precios/ajuste-masivo/',       vd.ajuste_masivo,     name='lims_ajuste_masivo'),
    path('api/precios/buscar-analitos/', vd.api_buscar_analitos_precios, name='lims_api_precios_buscar_analitos'),
    path('api/precios/agregar-analito/', vd.api_agregar_analito_precio, name='lims_api_precios_agregar_analito'),
]
