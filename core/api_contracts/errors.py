"""Errores de negocio tipados para la API con contrato uniforme (Fase 3).

Guía de códigos HTTP típicos (status_code en BusinessApiError):
  400 — solicitud inválida / regla de negocio simple
  403 — permiso denegado o tenant ausente
  404 — recurso no encontrado
  409 — conflicto transaccional (stock, saldo, estado incompatible)
  422 — validación de esquema (también cubierto por Ninja ValidationError)
"""


class BusinessApiError(Exception):
    """
    Error de negocio (saldo, lote, tenant, permiso, conflicto transaccional).
    El manejador Ninja lo serializa al esquema ApiErrorEnvelope.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        detail: dict | None = None,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.detail = dict(detail or {})
        self.status_code = int(status_code)
        super().__init__(message)
