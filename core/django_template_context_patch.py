"""
Django 5.0.x + Python 3.13+: BaseContext.__copy__ usa copy(super()), que falla
(AttributeError en dicts). Misma corrección que django/django en main.
"""
import sys


def apply_if_needed() -> None:
    if sys.version_info < (3, 13):
        return
    from copy import copy as copy_fn
    from django.template import context as ctx

    def __copy__(self):
        duplicate = ctx.BaseContext()
        duplicate.__class__ = self.__class__
        duplicate.__dict__ = copy_fn(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    ctx.BaseContext.__copy__ = __copy__
