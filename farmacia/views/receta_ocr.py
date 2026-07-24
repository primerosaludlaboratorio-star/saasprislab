"""Endpoints del lector de recetas del PDV."""

import base64
import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.services.ocr_documental import analizar_receta_farmacia
from core.models import Producto
from farmacia.models import LecturaRecetaFarmacia
from farmacia.services.receta_ocr import conciliar_medicamentos
from farmacia.views.pdv import _empresa_desde_request, _verificar_acceso


def _archivo_data_url(archivo):
    archivo.seek(0)
    contenido = archivo.read()
    archivo.seek(0)
    return f"data:{archivo.content_type};base64,{base64.b64encode(contenido).decode('ascii')}"


@login_required
@require_POST
def api_analizar_receta(request):
    empresa = _empresa_desde_request(request)
    if not empresa or not _verificar_acceso(request.user, ["CAJERO", "FARMACIA", "ADMIN", "ADMINISTRADOR", "GERENTE"]):
        return JsonResponse({"ok": False, "error": "Sin permisos para Farmacia"}, status=403)
    archivo = request.FILES.get("imagen_receta")
    if not archivo:
        return JsonResponse({"ok": False, "error": "Adjunte una foto de receta."}, status=400)
    lectura = LecturaRecetaFarmacia.objects_all.create(
        empresa=empresa, usuario=request.user, imagen=archivo,
    )
    resultado = analizar_receta_farmacia(_archivo_data_url(archivo), empresa, request.user)
    if resultado.get("error") or not resultado.get("activo", True):
        lectura.estado = "ERROR"
        lectura.error = resultado.get("error") or resultado.get("mensaje") or "No fue posible procesar la receta."
        lectura.save(update_fields=["estado", "error"])
        return JsonResponse({"ok": False, "lectura_id": lectura.id, "error": lectura.error}, status=422)
    datos = resultado.get("datos_extraidos") or {}
    lectura.texto_extraido = resultado.get("texto_extraido", "")
    lectura.datos_extraidos = datos
    lectura.sugerencias = conciliar_medicamentos(empresa, datos)
    lectura.confianza = Decimal(str(resultado.get("confianza") or 0))
    lectura.save(update_fields=["texto_extraido", "datos_extraidos", "sugerencias", "confianza"])
    return JsonResponse({
        "ok": True,
        "lectura_id": lectura.id,
        "tipo_documento": resultado.get("tipo_documento"),
        "confianza": resultado.get("confianza"),
        "datos": datos,
        "sugerencias": lectura.sugerencias,
        "requiere_revision_humana": True,
    })


@login_required
@require_POST
def api_confirmar_receta(request):
    empresa = _empresa_desde_request(request)
    if not empresa or not _verificar_acceso(request.user, ["CAJERO", "FARMACIA", "ADMIN", "ADMINISTRADOR", "GERENTE"]):
        return JsonResponse({"ok": False, "error": "Sin permisos para Farmacia"}, status=403)
    try:
        payload = json.loads(request.body or "{}")
        lectura = LecturaRecetaFarmacia.objects_all.get(pk=payload.get("lectura_id"), empresa=empresa)
        items = payload.get("items") or []
    except (ValueError, TypeError, LecturaRecetaFarmacia.DoesNotExist):
        return JsonResponse({"ok": False, "error": "Lectura o selección inválida."}, status=400)
    if not items:
        return JsonResponse({"ok": False, "error": "Confirme al menos un medicamento."}, status=400)
    ids = {int(item.get("producto_id")) for item in items if str(item.get("producto_id", "")).isdigit()}
    productos = {p.id: p for p in Producto.objects_all.filter(empresa=empresa, id__in=ids)}
    confirmados = []
    for item in items:
        producto = productos.get(int(item.get("producto_id"))) if str(item.get("producto_id", "")).isdigit() else None
        if not producto:
            return JsonResponse({"ok": False, "error": "Producto fuera del catálogo de la empresa."}, status=400)
        try:
            cantidad = int(item.get("cantidad") or 1)
        except (TypeError, ValueError):
            cantidad = 1
        cantidad = max(1, min(cantidad, 99))
        confirmados.append({"producto_id": producto.id, "cantidad": cantidad})
    lectura.productos_confirmados = confirmados
    lectura.estado = "CONFIRMADA"
    lectura.confirmada_en = timezone.now()
    lectura.confirmada_por = request.user
    lectura.save(update_fields=["productos_confirmados", "estado", "confirmada_en", "confirmada_por"])
    return JsonResponse({"ok": True, "items": confirmados, "mensaje": "Medicamentos confirmados. Revise lotes y receta antes de cobrar."})
