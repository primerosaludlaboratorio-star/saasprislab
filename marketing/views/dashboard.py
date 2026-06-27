from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.models import Paciente
from marketing.models import CampanaMarketing, CuponMarketing


@login_required
def dashboard_marketing(request):
    """Dashboard principal de marketing."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    campanas = CampanaMarketing.objects.filter(empresa=empresa).order_by("-fecha_creacion")[:50]
    cupones = CuponMarketing.objects.filter(empresa=empresa).order_by("-fecha_creacion")[:50]
    pacientes = Paciente.objects.filter(empresa=empresa).order_by("nombre_completo")[:200]

    return render(
        request,
        "marketing/dashboard_marketing.html",
        {"campanas": campanas, "cupones": cupones, "pacientes": pacientes, "empresa": empresa},
    )


@login_required
def entrenamiento_ia(request):
    """Acceso directo a Academy / simulaciones."""
    empresa = getattr(request.user, "empresa", None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    return render(request, "marketing/entrenamiento_ia.html", {"empresa": empresa})


@login_required
def dashboard_reactivacion_ia(request):
    """Vista del dashboard de reactivación con IA."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return redirect('home')
    return render(request, "marketing/reactivacion_ia.html", {
        "empresa": empresa,
        "segmentos": [
            ('diabeticos', 'Diabéticos / Control de Glucosa', '🩸'),
            ('hipertensos', 'Hipertensos / Control Renal', '💊'),
            ('renales', 'Pacientes Renales', '🫘'),
            ('cardiaco', 'Control Cardíaco', '❤️'),
            ('todos', 'Todos los Pacientes Inactivos', '👥'),
        ],
    })
