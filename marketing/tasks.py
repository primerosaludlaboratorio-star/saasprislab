"""
Tareas asíncronas — marketing (tracking 204).
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.db import close_old_connections

logger = logging.getLogger("marketing.tasks")


@shared_task(
    name="marketing.tasks.persist_marketing_tracking_hit",
    ignore_result=True,
)
def persist_marketing_tracking_hit(
    *,
    event_key: str,
    empresa_id: int | None,
    campana_id: int | None,
    paciente_id: int | None,
    prospecto_id: int | None,
    meta: dict,
    user_agent_hash: str,
    ip_hash: str,
) -> None:
    close_old_connections()
    try:
        if empresa_id is None:
            logger.critical(
                "persist_marketing_tracking_hit abortado: empresa_id obligatorio (multi-tenant Punto 17)"
            )
            return

        from marketing.models import MarketingTrackingHit

        MarketingTrackingHit.objects.create(
            event_key=event_key[:64],
            empresa_id=empresa_id,
            campana_id=campana_id,
            paciente_id=paciente_id,
            prospecto_id=prospecto_id,
            meta=meta or {},
            user_agent_hash=(user_agent_hash or "")[:64],
            ip_hash=(ip_hash or "")[:64],
        )
    finally:
        close_old_connections()
