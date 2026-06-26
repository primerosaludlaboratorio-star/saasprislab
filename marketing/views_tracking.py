"""
Endpoint de tracking HTTP 204 — sin cuerpo, mínima latencia percibida.

- GET/HEAD: válido para pixel de correo o prefetch de cliente.
- Persistencia: Celery si está disponible; si no, hilo daemon con conexión BD propia.
- Consentimiento: si el token identifica paciente/prospecto, no se guarda nada sin opt-in.

Claves `ev` canónicas (v1.20 — ver DOCS_AUDIT_MAESTRO §6.11 / §9):
  wa_resultado_clic, email_resultado_abierto, email_promo_abierto, push_notif_tap.
Otros valores ``[a-z0-9_]{1,64}`` siguen siendo válidos; las canónicas alinean métricas entre canales.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading

from django.conf import settings
from django.core import signing
from django.db import close_old_connections
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

from core.models import Paciente

from .models import CampanaMarketing, ProspectoCRM
from .tracking_signing import unsign_track_token

logger = logging.getLogger("marketing.tracking")

# Referencia cruzada con bitácora §6.11 — no se rechazan otros `ev` por compatibilidad.
CANONICAL_TRACKING_EVENTS_V120 = frozenset(
    (
        "wa_resultado_clic",
        "email_resultado_abierto",
        "email_promo_abierto",
        "push_notif_tap",
    )
)

_EVENT_RE = re.compile(r"^[a-z0-9_]{1,64}$")
_MAX_META_JSON = 800


def _hash_ip(request) -> str:
    raw = (request.META.get("HTTP_X_FORWARDED_FOR") or "") or (
        request.META.get("REMOTE_ADDR") or ""
    )
    first = raw.split(",")[0].strip()
    if not first:
        return ""
    pepper = (getattr(settings, "SECRET_KEY", "") or "")[:32]
    return hashlib.sha256(f"{pepper}|{first}".encode()).hexdigest()[:64]


def _hash_ua(request) -> str:
    ua = (request.META.get("HTTP_USER_AGENT") or "")[:512]
    if not ua:
        return ""
    return hashlib.sha256(ua.encode("utf-8", errors="ignore")).hexdigest()[:64]


def _compact_meta(request) -> dict:
    """Solo querystring acotado; excluye token y claves reservadas."""
    skip = {"tok", "token", "sig", "ev", "camp"}
    out = {}
    for k in request.GET:
        if k.lower() in skip:
            continue
        if len(out) >= 12:
            break
        if not re.match(r"^[a-zA-Z0-9_]{1,32}$", k):
            continue
        vals = request.GET.getlist(k)[:2]
        cleaned = [(item or "")[:120] for item in vals if item]
        if cleaned:
            out[k] = cleaned if len(cleaned) > 1 else cleaned[0]
    try:
        raw = json.dumps(out, ensure_ascii=False)
        if len(raw) > _MAX_META_JSON:
            raw = raw[:_MAX_META_JSON]
        return json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def _schedule_persist(**kwargs) -> None:
    try:
        from .tasks import persist_marketing_tracking_hit

        persist_marketing_tracking_hit.delay(**kwargs)
        return
    except Exception as exc:
        logging.getLogger(__name__).exception("Error inesperado en _schedule_persist (views_tracking.py)")
        logger.debug("Celery no disponible o fallo al encolar: %s", exc)

    def _run():
        close_old_connections()
        try:
            from .models import MarketingTrackingHit

            MarketingTrackingHit.objects.create(
                event_key=kwargs["event_key"][:64],
                empresa_id=kwargs.get("empresa_id"),
                campana_id=kwargs.get("campana_id"),
                paciente_id=kwargs.get("paciente_id"),
                prospecto_id=kwargs.get("prospecto_id"),
                meta=kwargs.get("meta") or {},
                user_agent_hash=(kwargs.get("user_agent_hash") or "")[:64],
                ip_hash=(kwargs.get("ip_hash") or "")[:64],
            )
        except Exception:
            logger.exception("persist tracking (fallback thread)")
        finally:
            close_old_connections()

    threading.Thread(target=_run, daemon=True).start()


@require_http_methods(["GET", "HEAD"])
def track_pixel_204(request):
    ev = (request.GET.get("ev") or "").strip().lower()
    if not ev or not _EVENT_RE.match(ev):
        return HttpResponse(status=204)

    tok = (request.GET.get("tok") or "").strip()
    payload = unsign_track_token(tok) if tok else None

    empresa_id = None
    paciente_id = None
    prospecto_id = None

    if payload:
        empresa_id = payload.get("e")
        if isinstance(empresa_id, int) or (isinstance(empresa_id, str) and str(empresa_id).isdigit()):
            empresa_id = int(empresa_id)
        else:
            empresa_id = None

        pid = payload.get("p")
        if pid is not None and str(pid).isdigit():
            paciente_id = int(pid)
        prid = payload.get("pr")
        if prid is not None and str(prid).isdigit():
            prospecto_id = int(prid)

    campana_id = None
    raw_camp = (request.GET.get("camp") or "").strip()
    if raw_camp.isdigit():
        cid = int(raw_camp)
        camp = CampanaMarketing.objects.filter(pk=cid).select_related("empresa").first()
        if camp:
            if empresa_id is None:
                empresa_id = camp.empresa_id
            elif camp.empresa_id != empresa_id:
                camp = None
        if camp:
            campana_id = camp.pk

    if paciente_id is not None and empresa_id is not None:
        p = Paciente.objects.filter(pk=paciente_id, empresa_id=empresa_id).first()
        if p is None:
            return HttpResponse(status=204)
        if not getattr(p, "consentimiento_marketing", False):
            return HttpResponse(status=204)

    if prospecto_id is not None and empresa_id is not None:
        pr = ProspectoCRM.objects.filter(pk=prospecto_id, empresa_id=empresa_id).first()
        if pr is None:
            return HttpResponse(status=204)
        if not getattr(pr, "consentimiento_comunicaciones", False):
            return HttpResponse(status=204)

    if empresa_id is None:
        raw_eid = (request.META.get("HTTP_X_EMPRESA_ID") or "").strip()
        if raw_eid.isdigit():
            empresa_id = int(raw_eid)

    meta = _compact_meta(request)
    ua_h = _hash_ua(request)
    ip_h = _hash_ip(request)

    _schedule_persist(
        event_key=ev,
        empresa_id=empresa_id,
        campana_id=campana_id,
        paciente_id=paciente_id,
        prospecto_id=prospecto_id,
        meta=meta,
        user_agent_hash=ua_h,
        ip_hash=ip_h,
    )
    return HttpResponse(status=204)