"""Compat: el middleware vive en ``admin_access`` (SOP / auditoría)."""
from core.middleware.admin_access import AdminAccessMiddleware

__all__ = ['AdminAccessMiddleware']
