from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from core.models import Empresa, Usuario

from .models import AccesoAcademia, CursoAcademia, SesionVisualizacion, VideoAcademia
from .services import bunny_stream
from .services.access import academia_habilitada_para_empresa


def _empresa_actual(request):
    return getattr(request, "empresa_actual", None) or getattr(request.user, "empresa", None)


def _academia_habilitada_o_404(request):
    empresa = _empresa_actual(request)
    if getattr(request.user, "is_superuser", False):
        if empresa is None:
            empresa = Empresa.objects.filter(nombre__icontains="prislab").first() or Empresa.objects.first()
        return empresa
    if not academia_habilitada_para_empresa(empresa):
        raise Http404("Academia no disponible para esta empresa")
    return empresa


def _es_admin_academia(user) -> bool:
    return bool(
        getattr(user, "is_superuser", False)
        or getattr(user, "is_staff", False)
        or getattr(user, "rol", "").upper() in {"ADMIN", "DIRECTOR", "GERENTE"}
    )


def _curso_con_acceso_o_404(request, slug: str) -> CursoAcademia:
    empresa = _empresa_actual(request)
    curso = get_object_or_404(CursoAcademia, empresa=empresa, slug=slug, activo=True)
    if _es_admin_academia(request.user):
        return curso
    if not AccesoAcademia.objects.filter(
        empresa=empresa,
        usuario=request.user,
        curso=curso,
        activo=True,
        fecha_expiracion__gt=timezone.now(),
    ).exists():
        raise Http404("No tienes acceso a este curso")
    return curso


@login_required
def dashboard(request):
    empresa = _academia_habilitada_o_404(request)
    accesos = (
        AccesoAcademia.objects.filter(empresa=empresa, usuario=request.user, activo=True)
        .select_related("curso")
        .order_by("curso__titulo")
    )
    cursos = [a.curso for a in accesos if a.vigente()]
    cursos_admin = CursoAcademia.objects.filter(empresa=empresa, activo=True).order_by("titulo") if _es_admin_academia(request.user) else []
    return render(
        request,
        "academia/dashboard.html",
        {
            "cursos": cursos,
            "cursos_admin": cursos_admin,
            "es_admin_academia": _es_admin_academia(request.user),
        },
    )


@login_required
def curso_detalle(request, slug: str):
    _academia_habilitada_o_404(request)
    curso = _curso_con_acceso_o_404(request, slug)
    videos = curso.videos.all().order_by("orden", "id")
    video_id = request.GET.get("video")
    current_video = None
    if video_id:
        current_video = videos.filter(id=video_id).first()
    if current_video is None:
        current_video = videos.first()

    return render(
        request,
        "academia/curso_detalle.html",
        {
            "curso": curso,
            "videos": videos,
            "current_video": current_video,
            "api_base_url": reverse("academia:api_root").rstrip("/"),
        },
    )


@login_required
@require_GET
def api_root(request):
    _academia_habilitada_o_404(request)
    return JsonResponse(
        {
            "ok": True,
            "name": "academia",
            "urls": {
                "cursos": reverse("academia:dashboard"),
            },
        }
    )


@login_required
@require_GET
def api_video_reproducir(request, video_id: int):
    empresa = _academia_habilitada_o_404(request)
    video = get_object_or_404(VideoAcademia, empresa=empresa, id=video_id)

    if not _es_admin_academia(request.user):
        if not AccesoAcademia.objects.filter(
            empresa=empresa,
            usuario=request.user,
            curso=video.curso,
            activo=True,
            fecha_expiracion__gt=timezone.now(),
        ).exists():
            return JsonResponse({"detail": "No tienes acceso vigente a este curso"}, status=403)

    _, expires, embed_url = bunny_stream.generar_token_embed(video.bunny_video_id)
    return JsonResponse(
        {
            "embed_url": embed_url,
            "expires": expires,
            "video_id": video.id,
            "titulo": video.titulo,
        }
    )


@login_required
@require_POST
def api_heartbeat(request, video_id: int):
    empresa = _academia_habilitada_o_404(request)
    video = get_object_or_404(VideoAcademia, empresa=empresa, id=video_id)

    if not _es_admin_academia(request.user):
        if not AccesoAcademia.objects.filter(
            empresa=empresa,
            usuario=request.user,
            curso=video.curso,
            activo=True,
            fecha_expiracion__gt=timezone.now(),
        ).exists():
            return JsonResponse({"detail": "Acceso expirado"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}
    segundos = int(payload.get("segundos_reproducidos") or payload.get("segundos") or 0)
    if segundos <= 0:
        return JsonResponse({"ok": True, "segundos_acumulados": 0})

    sesion = (
        SesionVisualizacion.objects.filter(
            empresa=empresa,
            usuario=request.user,
            video=video,
            finalizada=False,
        )
        .order_by("-ultima_actividad")
        .first()
    )

    ahora = timezone.now()
    if sesion and (ahora - sesion.ultima_actividad) < timedelta(minutes=2):
        sesion.segundos_acumulados += segundos
        sesion.ultima_actividad = ahora
        sesion.save(update_fields=["segundos_acumulados", "ultima_actividad"])
    else:
        sesion = SesionVisualizacion.objects.create(
            empresa=empresa,
            usuario=request.user,
            video=video,
            segundos_acumulados=segundos,
            inicio=ahora,
            ultima_actividad=ahora,
        )

    return JsonResponse({"ok": True, "segundos_acumulados": sesion.segundos_acumulados})


@login_required
@require_POST
def otorgar_acceso(request):
    if not _es_admin_academia(request.user):
        return JsonResponse({"detail": "Sin permisos"}, status=403)

    empresa = _academia_habilitada_o_404(request)
    usuario_id = request.POST.get("usuario_id") or request.POST.get("usuario")
    curso_id = request.POST.get("curso_id") or request.POST.get("curso")
    dias_vigencia = int(request.POST.get("dias_vigencia") or 30)

    if not usuario_id or not curso_id:
        return JsonResponse({"detail": "usuario_id y curso_id son requeridos"}, status=400)

    usuario = Usuario.objects.filter(id=usuario_id, empresa=empresa).first()
    if usuario is None:
        return JsonResponse({"detail": "Usuario no encontrado en esta empresa"}, status=404)

    curso = CursoAcademia.objects.filter(id=curso_id, empresa=empresa).first()
    if curso is None:
        return JsonResponse({"detail": "Curso no encontrado"}, status=404)
    expiracion = timezone.now() + timedelta(days=dias_vigencia)

    acceso, _created = AccesoAcademia.objects.update_or_create(
        empresa=empresa,
        usuario=usuario,
        curso=curso,
        defaults={
            "fecha_inicio": timezone.now(),
            "fecha_expiracion": expiracion,
            "activo": True,
            "otorgado_por": request.user,
        },
    )
    return JsonResponse(
        {
            "ok": True,
            "id": acceso.id,
            "usuario_id": acceso.usuario_id,
            "curso_id": acceso.curso_id,
            "fecha_expiracion": acceso.fecha_expiracion.isoformat(),
        }
    )


@login_required
def reporte_colaborador(request, usuario_id: int):
    if not _es_admin_academia(request.user):
        return JsonResponse({"detail": "Sin permisos"}, status=403)

    empresa = _academia_habilitada_o_404(request)
    usuario = Usuario.objects.filter(id=usuario_id, empresa=empresa).first()
    if usuario is None:
        return JsonResponse({"detail": "Usuario no encontrado en esta empresa"}, status=404)
    sesiones = SesionVisualizacion.objects.filter(empresa=empresa, usuario_id=usuario_id).select_related("video", "video__curso")
    resumen = {}
    for sesion in sesiones:
        key = sesion.video_id
        item = resumen.setdefault(
            key,
            {
                "usuario_id": usuario_id,
                "curso_id": sesion.video.curso_id,
                "video_id": sesion.video_id,
                "titulo_video": sesion.video.titulo,
                "segundos_totales": 0,
            },
        )
        item["segundos_totales"] += sesion.segundos_acumulados
    return JsonResponse(list(resumen.values()), safe=False)
