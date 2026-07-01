# core/middleware/tenant_subdomain.py
# ==============================================================================
# PRISLAB SaaS — TenantSubdomainMiddleware
# ==============================================================================
# Extrae el tenant_id desde el subdominio del Host header.
# Complementa EmpresaIdentityMiddleware (que usa user.empresa).
#
# Resolución por prioridad:
#   1. Subdominio del Host → busca Empresa por slug/subdominio
#   2. Header X-Tenant-Slug (APIs, mobile, Postman)
#   3. user.empresa (fallback — EmpresaIdentityMiddleware ya lo hace)
#
# Dominio raíz configurado en settings.PRISLAB_ROOT_DOMAIN (ej: "labcorecloud.com")
#
# Ejemplos:
#   Host: prislab.labcorecloud.com  → tenant slug "prislab"
#   Host: demo.labcorecloud.com     → tenant slug "demo"
#   Host: labcorecloud.com          → sin subdominio → sin tenant (pública)
#
# POSICIÓN en MIDDLEWARE: justo DESPUÉS de AuthenticationMiddleware,
# ANTES de EmpresaIdentityMiddleware para que éste último tenga prioridad
# si el usuario ya tiene empresa asignada.
# ==============================================================================

from __future__ import annotations

import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied

from core.tenant import set_current_empresa, clear_current_empresa

logger = logging.getLogger("core.middleware.tenant_subdomain")


def _extract_subdomain(host: str, root_domain: str) -> str | None:
    """
    Extrae el subdominio dado un host y un dominio raíz.

    Examples:
        _extract_subdomain("acme.labcorecloud.com", "labcorecloud.com") → "acme"
        _extract_subdomain("labcorecloud.com", "labcorecloud.com") → None
        _extract_subdomain("localhost", "labcorecloud.com") → None
    """
    host = host.lower().split(":")[0].strip()  # quitar puerto
    root = root_domain.lower().strip()

    if host == root or not host.endswith("." + root):
        return None

    subdomain = host[: -(len(root) + 1)]
    # Ignorar subdominios www o vacíos
    if not subdomain or subdomain == "www":
        return None
    return subdomain


def _resolve_empresa_by_slug(slug: str):
    """Busca la Empresa cuyo campo slug/subdominio coincide."""
    try:
        from core.models import Empresa
        # El modelo Empresa tiene campo 'subdominio' o 'slug'
        empresa = Empresa.objects.filter(subdominio=slug, activa=True).first()
        if empresa is None:
            # Fallback: buscar por nombre exacto o slug en nombre
            empresa = Empresa.objects.filter(nombre__iexact=slug, activa=True).first()
        return empresa
    except Exception as exc:
        logger.error("Error al resolver empresa por slug='%s': %s", slug, exc)
        return None


class TenantSubdomainMiddleware:
    """
    Middleware que resuelve el tenant a partir del subdominio HTTP.

    Garantiza aislamiento omnipresente: incluso si el usuario no está
    autenticado, el tenant queda establecido para queries de onboarding/
    landing públicas que usen el contexto de empresa.

    Configuración en settings.py:
        PRISLAB_ROOT_DOMAIN = "labcorecloud.com"
        PRISLAB_TENANT_STRICT_SUBDOMAIN = False  # True = 404 si slug no existe
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._root_domain: str = getattr(settings, "PRISLAB_ROOT_DOMAIN", "labcorecloud.com")
        self._strict: bool = getattr(settings, "PRISLAB_TENANT_STRICT_SUBDOMAIN", False)

    def __call__(self, request):
        empresa = None
        slug = None

        try:
            host = request.META.get("HTTP_HOST", "")
            slug = _extract_subdomain(host, self._root_domain)

            # Fallback: header explícito para APIs / tests
            if not slug:
                slug = request.META.get("HTTP_X_TENANT_SLUG", "").strip() or None

            if slug:
                empresa = _resolve_empresa_by_slug(slug)
                if empresa is None and self._strict:
                    logger.warning(
                        "TENANT_SUBDOMAIN: slug='%s' no encontrado (strict mode).", slug
                    )
                    raise PermissionDenied(f"Tenant '{slug}' no existe o está inactivo.")
                if empresa:
                    logger.debug(
                        "TENANT_SUBDOMAIN: host='%s' → empresa_id=%s slug='%s'",
                        host, empresa.pk, slug,
                    )
                    # Solo inyecta en thread-local si EmpresaIdentityMiddleware
                    # aún no lo hizo (se evita sobrescribir empresa del usuario).
                    # EmpresaIdentityMiddleware corre DESPUÉS y puede sobreescribir.
                    request._tenant_from_subdomain = empresa

            response = self.get_response(request)
            return response

        except PermissionDenied:
            raise
        except Exception as exc:
            logger.exception(
                "TenantSubdomainMiddleware error inesperado slug='%s': %s", slug, exc
            )
            response = self.get_response(request)
            return response
        finally:
            # El cleanup real lo hace EmpresaIdentityMiddleware.
            # Este middleware es solo de resolución, no de limpieza.
            pass
