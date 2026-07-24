"""OCR de facturas/notas para preparar recepciones del silo Laboratorio."""

import base64
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.services.ocr_documental import analizar_compra_laboratorio
from inventario.models import LecturaCompraLaboratorio, OrdenDeCompra, LineaOrdenCompra
from inventario.services.compra_ocr import conciliar_compra_laboratorio
from .helpers import _get_empresa


def _data_url(archivo):
    archivo.seek(0)
    contenido = archivo.read()
    archivo.seek(0)
    return f"data:{archivo.content_type};base64,{base64.b64encode(contenido).decode('ascii')}"


def _acceso(request):
    empresa = _get_empresa(request)
    permitido = bool(
        getattr(request.user, "is_superuser", False)
        or getattr(request.user, "rol", "") in {"ADMIN", "DIRECTOR", "QUIMICO", "GERENTE"}
    )
    return empresa, permitido


@login_required
@require_POST
def api_analizar_compra_laboratorio(request):
    empresa, permitido = _acceso(request)
    if not empresa or not permitido:
        return JsonResponse({"ok": False, "error": "Sin permisos para inventario de Laboratorio."}, status=403)
    archivo = request.FILES.get("documento_compra")
    if not archivo:
        return JsonResponse({"ok": False, "error": "Adjunte una foto de factura o nota de compra."}, status=400)
    lectura = LecturaCompraLaboratorio.objects_all.create(empresa=empresa, usuario=request.user, imagen=archivo)
    resultado = analizar_compra_laboratorio(_data_url(archivo), empresa, request.user)
    if resultado.get("error") or not resultado.get("activo", True):
        lectura.estado = "ERROR"
        lectura.error = resultado.get("error") or resultado.get("mensaje") or "No fue posible procesar el documento."
        lectura.save(update_fields=["estado", "error"])
        return JsonResponse({"ok": False, "lectura_id": lectura.id, "error": lectura.error}, status=422)
    datos = resultado.get("datos_extraidos") or {}
    lectura.texto_extraido = resultado.get("texto_extraido", "")
    lectura.datos_extraidos = datos
    lectura.sugerencias = conciliar_compra_laboratorio(empresa, datos)
    lectura.confianza = Decimal(str(resultado.get("confianza") or 0))
    lectura.save(update_fields=["texto_extraido", "datos_extraidos", "sugerencias", "confianza"])
    return JsonResponse({"ok": True, "lectura_id": lectura.id, "datos": datos,
                         "sugerencias": lectura.sugerencias, "requiere_revision_humana": True})


@login_required
@require_POST
def api_confirmar_compra_laboratorio(request):
    empresa, permitido = _acceso(request)
    if not empresa or not permitido:
        return JsonResponse({"ok": False, "error": "Sin permisos para inventario de Laboratorio."}, status=403)
    try:
        payload = json.loads(request.body or "{}")
        lectura = LecturaCompraLaboratorio.objects_all.get(pk=payload.get("lectura_id"), empresa=empresa)
        oc = OrdenDeCompra.objects.get(pk=payload.get("orden_id"), empresa=empresa)
    except (ValueError, TypeError, LecturaCompraLaboratorio.DoesNotExist, OrdenDeCompra.DoesNotExist):
        return JsonResponse({"ok": False, "error": "Lectura u orden de compra inválida."}, status=400)
    items = payload.get("items") or []
    lineas = {linea.id: linea for linea in oc.lineas.filter(silo="LAB")}
    confirmados = []
    for item in items:
        try:
            linea = lineas[int(item.get("linea_id"))]
            cantidad = Decimal(str(item.get("cantidad")))
            costo = Decimal(str(item.get("costo_unitario")))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "Línea, cantidad o costo inválido."}, status=400)
        if str(item.get("reactivo_id")) != str(linea.object_id):
            return JsonResponse({"ok": False, "error": f"Seleccione el reactivo del catálogo para {linea.descripcion_snapshot}."}, status=400)
        lote = str(item.get("numero_lote") or "").strip().upper()
        caducidad = str(item.get("fecha_caducidad") or "").strip()
        if cantidad <= 0 or costo < 0 or not lote or not caducidad:
            return JsonResponse({"ok": False, "error": f"Complete cantidad, costo, lote y caducidad para {linea.descripcion_snapshot}."}, status=400)
        try:
            datetime.strptime(caducidad, "%Y-%m-%d")
        except ValueError:
            return JsonResponse({"ok": False, "error": f"Caducidad inválida para {linea.descripcion_snapshot}."}, status=400)
        confirmados.append({
            "linea_id": linea.id, "cantidad": str(cantidad), "costo_unitario": str(costo),
            "numero_lote": lote, "fecha_caducidad": caducidad,
            "marca": str(item.get("marca") or "").strip(),
            "fecha_compra": str(item.get("fecha_compra") or ""),
            "fecha_apertura": str(item.get("fecha_apertura") or ""),
            "factura_numero": str(item.get("factura_numero") or "").strip(),
            "factura_fecha": str(item.get("factura_fecha") or ""),
            "inserto_version": str(item.get("inserto_version") or "").strip(),
        })
    request.session[f"inventario_lab_ocr_{oc.id}"] = {
        "lectura_id": lectura.id, "items": confirmados,
        "proveedor_texto": str((payload.get("proveedor") or "")).strip(),
        "folio": str(payload.get("folio") or "").strip(),
        "fecha_compra": str(payload.get("fecha_compra") or "").strip(),
    }
    request.session.modified = True
    lectura.items_confirmados = confirmados
    lectura.estado = "CONFIRMADA"
    lectura.confirmado_en = timezone.now()
    lectura.confirmado_por = request.user
    lectura.save(update_fields=["items_confirmados", "estado", "confirmado_en", "confirmado_por"])
    return JsonResponse({"ok": True, "redirect": reverse("inventario:detalle_oc", kwargs={"pk": oc.id}),
                         "mensaje": "Recepción preparada para revisión final. Todavía no se modificó el inventario."})
