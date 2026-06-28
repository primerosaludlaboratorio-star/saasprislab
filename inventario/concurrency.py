"""
Inventario federado — utilidades de concurrencia (Fase 1 v7.5).

Reintentos ante bloqueos de BD o carreras en get_or_create.
Aislado de farmacia/caja; solo para silos inventario.
"""
from __future__ import annotations

import time
import logging
from typing import Callable, TypeVar

from django.db import OperationalError, IntegrityError

logger = logging.getLogger(__name__)

T = TypeVar('T')

DEFAULT_MAX_RETRIES = 3


def retry_on_db_contention(
    fn: Callable[[], T],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    label: str = 'inventario',
) -> T:
    """
    Ejecuta ``fn`` reintentando ante OperationalError o IntegrityError
    (deadlock, lock timeout, carrera en clave única).
    """
    last_exc: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except (OperationalError, IntegrityError) as exc:
            last_exc = exc
            if attempt >= max_retries - 1:
                raise
            wait = 2**attempt
            logger.warning(
                '%s: reintento %s/%s tras %s; espera %ss',
                label,
                attempt + 1,
                max_retries,
                type(exc).__name__,
                wait,
            )
            time.sleep(wait)
    assert last_exc is not None
    raise last_exc
