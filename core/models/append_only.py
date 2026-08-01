"""Shared guards for records that must never be mutated or deleted."""

from django.core.exceptions import ValidationError
from django.db import models

from core.tenant import TenantManager, TenantQuerySet


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError('Los registros append-only no se pueden modificar.')

    def delete(self):
        raise ValidationError('Los registros append-only no se pueden eliminar.')


class AppendOnlyManager(models.Manager.from_queryset(AppendOnlyQuerySet)):
    """Blocks bulk update/delete paths that bypass model methods."""


class TenantAppendOnlyQuerySet(TenantQuerySet):
    """Tenant-filtered queryset that also blocks bulk mutation."""

    def update(self, **kwargs):
        raise ValidationError('Los registros append-only no se pueden modificar.')

    def delete(self):
        raise ValidationError('Los registros append-only no se pueden eliminar.')


class TenantAppendOnlyManager(TenantManager.from_queryset(TenantAppendOnlyQuerySet)):
    """Default manager for immutable records owned by the current tenant."""


class UnfilteredAppendOnlyManager(models.Manager.from_queryset(TenantAppendOnlyQuerySet)):
    """Explicit unfiltered manager that retains append-only protections."""


def reject_append_only_mutation(instance, operation):
    if instance.pk is not None:
        raise ValidationError(
            f'{instance.__class__.__name__} es append-only; no se permite {operation}.'
        )
