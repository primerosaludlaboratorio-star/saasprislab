"""
API HTTP v3 — Django Ninja + contrato ApiErrorEnvelope (Fase 3).
PDV: búsqueda + cobro → VentaFarmaciaService.
LIMS: captura → ResultadosLimsService.guardar_captura_desde_datos.
"""
import json
import logging
import uuid
from typing import Any

from django.conf import settings
from django.http import JsonResponse
from ninja import Body, NinjaAPI, Query, Router
from ninja.errors import HttpError, ValidationError
from ninja.security import SessionAuth

from core.api_contracts.errors import BusinessApiError
from core.api_contracts.schemas import (
    ApiErrorEnvelope,
    BuscarProductosPdvResponse,
    LimsCapturaV3Response,
    PdvCobroV3Response,
    PdvProductoItem,
)
from core.services.lims.resultados_lims_service import ResultadosLimsService
from core.services.ventas.venta_farmacia_service import VentaFarmaciaService
from core.views.farmacia import _empresa_desde_request, _verificar_acceso

logger = logging.getLogger("core.api_v3")

router = Router(tags=["farmacia-pdv"])

api = NinjaAPI(
    version="3.0.0",
    title="PRISLAB Contratos API",
    auth=[SessionAuth()],
)


def _error_json(
    request,
    *,
    code: str,
    message: str,
    detail: dict | None = None,
    status: int = 400,
):
    rid = getattr(request, "api_request_id", None) or str(uuid.uuid4())
    body = ApiErrorEnvelope(
        code=code,
        message=message,
        detail=detail or {},
        request_id=rid,
    )
    return JsonResponse(body.model_dump(mode="json"), status=status)


def _requiere_lims_captura(user) -> bool:
    """Misma regla que @role_required('QUIMICO', 'ADMIN', 'LABORATORIO') en api_guardar_resultados."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    allowed_upper = {"QUIMICO", "ADMIN", "LABORATORIO"}
    user_rol = (getattr(user, "rol", "") or "").upper().strip()
    if user_rol in allowed_upper:
        return True
    return user.groups.filter(name__in=list(allowed_upper)).exists()


def _raise_from_farmacia_venta_json(resp: JsonResponse) -> dict:
    """Convierte JsonResponse del servicio PDV en BusinessApiError o dict de éxito."""
    status = resp.status_code
    try:
        body = json.loads(resp.content.decode("utf-8"))
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _raise_from_farmacia_venta_json (ninja_api.py)")
        raise BusinessApiError(
            "FARMACIA_INVALID_RESPONSE",
            "Respuesta inválida del servicio de venta.",
            status_code=502,
        ) from None
    if status < 400:
        return body
    msg = body.get("mensaje") or body.get("message") or "Error al procesar el cobro"
    detail = {k: v for k, v in body.items() if k not in ("status", "mensaje", "message")}
    lower = msg.lower()
    if status >= 500:
        raise BusinessApiError(
            "VENTA_PROCESSING_FAILED",
            msg,
            detail=detail,
            status_code=500,
        )
    if "stock insuficiente" in lower or (
        "insuficiente" in lower and ("unidad" in lower or "stock" in lower)
    ):
        raise BusinessApiError(
            "STOCK_INSUFFICIENT",
            msg,
            detail=detail,
            status_code=409,
        )
    if "no coincide" in lower or "suma de pagos" in lower:
        raise BusinessApiError(
            "PAYMENT_TOTAL_MISMATCH",
            msg,
            detail=detail,
            status_code=409,
        )
    raise BusinessApiError(
        "FARMACIA_BUSINESS_RULE",
        msg,
        detail=detail,
        status_code=status if status in (400, 403, 404, 409) else 400,
    )


def _raise_from_lims_out(out: dict) -> dict:
    """Traduce salida {http_status, body} del servicio LIMS a BusinessApiError o body OK."""
    status = int(out.get("http_status", 500))
    body = out.get("body") or {}
    if status < 400:
        return body
    msg = body.get("mensaje") or body.get("message") or "Error en captura de resultados"
    detail = {k: v for k, v in body.items() if k not in ("status", "mensaje", "message")}
    codigo = (body.get("codigo") or "").strip()
    http = status
    biz_code = codigo or "LIMS_BUSINESS_ERROR"
    if codigo in ("FORMULA_INCOMPLETA", "LIMS_PLACEHOLDER_0058"):
        http = 422
        biz_code = codigo
    elif status == 403:
        biz_code = "LIMS_FORBIDDEN"
    elif status == 404:
        biz_code = "ORDER_NOT_FOUND"
    elif status == 422:
        biz_code = "VALIDATION_ERROR"
    raise BusinessApiError(biz_code, msg, detail=detail, status_code=http)


@api.exception_handler(BusinessApiError)
def _handle_business(request, exc: BusinessApiError):
    return _error_json(
        request,
        code=exc.code,
        message=exc.message,
        detail=exc.detail,
        status=exc.status_code,
    )


@api.exception_handler(ValidationError)
def _handle_validation(request, exc: ValidationError):
    return _error_json(
        request,
        code="VALIDATION_ERROR",
        message="Los parámetros de la solicitud no son válidos.",
        detail={"errors": exc.errors},
        status=422,
    )


@api.exception_handler(HttpError)
def _handle_http_error(request, exc: HttpError):
    code_map = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        429: "RATE_LIMITED",
    }
    code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    return _error_json(
        request,
        code=code,
        message=str(exc.message),
        detail={},
        status=exc.status_code,
    )


@api.exception_handler(Exception)
def _handle_unexpected(request, exc: Exception):
    logger.exception("API v3: error no manejado")
    if settings.DEBUG:
        return _error_json(
            request,
            code="INTERNAL_ERROR",
            message=str(exc),
            detail={"exception_type": type(exc).__name__},
            status=500,
        )
    return _error_json(
        request,
        code="INTERNAL_ERROR",
        message="Error interno del servidor",
        detail={},
        status=500,
    )


@router.get(
    "/farmacia/pdv/productos",
    response=BuscarProductosPdvResponse,
    summary="Búsqueda de productos PDV (catálogo en vivo)",
)
def buscar_productos_pdv_v3(request, termino: str = Query(..., min_length=2, max_length=200)):
    if not _verificar_acceso(
        request.user,
        ["CAJERO", "FARMACIA", "ADMIN", "ADMINISTRADOR", "GERENTE"],
        ["FARMACIA", "GERENCIA_OPERATIVA", "GERENCIA"],
    ):
        raise BusinessApiError(
            "FORBIDDEN_FARMACIA",
            "Sin permisos para Punto de Venta Farmacia.",
            status_code=403,
        )
    empresa = _empresa_desde_request(request)
    if not empresa:
        raise BusinessApiError(
            "TENANT_REQUIRED",
            "Usuario sin empresa asignada; no se puede consultar el catálogo.",
            status_code=403,
        )
    raw = VentaFarmaciaService.buscar_productos_pdv(empresa, termino)
    productos = [PdvProductoItem.model_validate(x) for x in raw]
    rid = getattr(request, "api_request_id", None) or str(uuid.uuid4())
    return BuscarProductosPdvResponse(productos=productos, request_id=rid)


@router.post(
    "/farmacia/pdv/cobrar",
    response=PdvCobroV3Response,
    summary="Cobro PDV (transaccional, PEPS/Kardex)",
)
def farmacia_pdv_cobrar_v3(request, body: dict[str, Any] = Body(...)):
    if not _verificar_acceso(
        request.user,
        ["CAJERO", "FARMACIA", "ADMIN", "ADMINISTRADOR", "GERENTE"],
        ["FARMACIA", "GERENCIA_OPERATIVA", "GERENCIA"],
    ):
        raise BusinessApiError(
            "FORBIDDEN_FARMACIA",
            "Sin permisos para cobrar en Punto de Venta Farmacia.",
            status_code=403,
        )
    empresa = _empresa_desde_request(request)
    if not empresa:
        raise BusinessApiError(
            "TENANT_REQUIRED",
            "Usuario sin empresa asignada; no se puede cobrar.",
            status_code=403,
        )
    resp = VentaFarmaciaService.ejecutar_venta_pdv(request, body, empresa)
    if not isinstance(resp, JsonResponse):
        raise BusinessApiError(
            "FARMACIA_INVALID_RESPONSE",
            "El servicio de venta no devolvió una respuesta JSON esperada.",
            status_code=502,
        )
    ok = _raise_from_farmacia_venta_json(resp)
    rid = getattr(request, "api_request_id", None) or str(uuid.uuid4())
    return PdvCobroV3Response.model_validate({**ok, "request_id": rid})


@router.post(
    "/lims/resultados/captura",
    response=LimsCapturaV3Response,
    summary="Captura / validación de resultados LIMS (misma lógica que api_guardar_resultados)",
)
def lims_resultados_captura_v3(request, body: dict[str, Any] = Body(...)):
    if not _requiere_lims_captura(request.user):
        raise BusinessApiError(
            "LIMS_FORBIDDEN",
            "Solo personal autorizado (Químico/Laboratorio/Admin) puede capturar resultados.",
            status_code=403,
        )
    empresa = _empresa_desde_request(request)
    if not empresa:
        raise BusinessApiError(
            "TENANT_REQUIRED",
            "Usuario sin empresa asignada.",
            status_code=403,
        )
    data = dict(body)
    orden_id = data.pop("orden_id", None)
    if orden_id is None:
        raise BusinessApiError(
            "ORDEN_ID_REQUIRED",
            "El cuerpo JSON debe incluir orden_id (clave primaria de la orden).",
            status_code=400,
        )
    try:
        oid = int(orden_id)
    except (TypeError, ValueError):
        raise BusinessApiError(
            "ORDEN_ID_INVALID",
            "orden_id debe ser un entero válido.",
            status_code=400,
        ) from None
    out = ResultadosLimsService.guardar_captura_desde_datos(
        request,
        empresa,
        oid,
        data,
        usuario_efectivo=None,
    )
    ok = _raise_from_lims_out(out)
    rid = getattr(request, "api_request_id", None) or str(uuid.uuid4())
    return LimsCapturaV3Response.model_validate({**ok, "request_id": rid})


api.add_router("", router)