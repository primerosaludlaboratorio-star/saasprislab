"""
Vistas de Operaciones / Logística.
MVP: Dashboard de rutas y recolección (geolocalización) basado en OrdenDeServicio.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.models import OrdenDeServicio


@login_required
def rutas_recoleccion(request):
    """
    Dashboard operativo para ver órdenes con geolocalización y preparar recolección/entrega.
    MVP: listado y métricas básicas (sin mapas todavía).
    """
    empresa = getattr(request.user, 'empresa', None)

    ordenes = (
        OrdenDeServicio.objects.filter(empresa=empresa)
        .order_by("-fecha_creacion")[:200]
    )

    ordenes_con_geo = [o for o in ordenes if o.latitud is not None and o.longitud is not None]

    return render(
        request,
        "core/rutas_recoleccion.html",
        {
            "empresa": empresa,
            "ordenes": ordenes,
            "ordenes_con_geo": ordenes_con_geo,
            "total_ordenes": len(ordenes),
            "total_con_geo": len(ordenes_con_geo),
        },
    )


@login_required
def monitor_rutas(request):
    """
    Alias estable del Monitor de Rutas.
    Mantiene compatibilidad con enlaces legacy y reutiliza el dashboard operativo actual.
    """
    return rutas_recoleccion(request)
