#!/usr/bin/env python
"""
Rescate temporal PDV Farmacia (envoltorio).
Requiere: raíz del repo, variables de entorno de BD como manage.py.

  python fix_farmacia.py
  EMPRESA_RESCATE_ID=2 python fix_farmacia.py
"""
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django

    django.setup()
    from django.core.management import call_command

    eid = int(os.environ.get('EMPRESA_RESCATE_ID', '1'))
    call_command('rescate_farmacia_tenant', empresa_id=eid)
