#!/usr/bin/env python
"""
Script para generar llaves VAPID (Voluntary Application Server Identification)
para Web Push Notifications en PRISLAB V5.

SOLO EJECUTAR UNA VEZ durante el setup inicial.
Las llaves deben guardarse como variables de entorno o en Secret Manager.

Uso:
    python generar_vapid_keys.py
"""

import os
import sys
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.push_service import generar_vapid_keys


def main():
    print("=" * 70)
    print("  GENERADOR DE LLAVES VAPID - PRIS SENTINEL V4")
    print("=" * 70)
    print()
    print("Generando par de llaves VAPID para Web Push Notifications...")
    print()
    
    try:
        keys = generar_vapid_keys()
        
        print("LLAVES GENERADAS EXITOSAMENTE:")
        print("-" * 70)
        print()
        print("VAPID_PRIVATE_KEY (CONFIDENCIAL - Guardar en Secret Manager):")
        print(keys['private_key'])
        print()
        print("VAPID_PUBLIC_KEY (Para el frontend - puede ser pública):")
        print(keys['public_key'])
        print()
        print("-" * 70)
        print()
        print("INSTRUCCIONES:")
        print("1. Copia la PRIVATE_KEY y guárdala en Google Secret Manager como 'vapid-private-key'")
        print("2. Copia la PUBLIC_KEY y guárdala como 'vapid-public-key'")
        print()
        print("3. Agrega a config/settings.py:")
        print()
        print("   # Web Push Notifications (VAPID)")
        print("   VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')")
        print("   VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')")
        print("   VAPID_CLAIMS = {")
        print("       'sub': 'mailto:admin@prislab.com'")
        print("   }")
        print()
        print("4. Para desarrollo local, crea un archivo .env con:")
        print()
        print(f"   VAPID_PRIVATE_KEY={keys['private_key']}")
        print(f"   VAPID_PUBLIC_KEY={keys['public_key']}")
        print()
        print("=" * 70)
        print("ADVERTENCIA: NO COMPARTAS LA PRIVATE_KEY. ES COMO UNA PASSWORD.")
        print("=" * 70)
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en main (generar_vapid_keys.py)")
        print(f"ERROR al generar llaves: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()