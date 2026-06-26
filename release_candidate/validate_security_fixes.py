#!/usr/bin/env python3
"""Validación de correcciones de seguridad post-auditoría"""

import os
import sys
import django
import logging

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, str(os.path.dirname(os.path.abspath(__file__))))

try:
    django.setup()
    from django.conf import settings
    
    print('╔══════════════════════════════════════════════════════════════╗')
    print('║   VALIDACIÓN POST-CORRECCIONES - BLOQUE 1 COMPLETADO        ║')
    print('╚══════════════════════════════════════════════════════════════╝')
    print()
    
    # Verificar DEBUG
    debug_ok = not settings.DEBUG
    print(f'[{"✅" if debug_ok else "❌"}] DEBUG = {settings.DEBUG} {"(CORRECTO)" if debug_ok else "(DEBE SER False)"}')
    
    # Verificar SECRET_KEY
    sk_len = len(settings.SECRET_KEY)
    sk_secure = not settings.SECRET_KEY.startswith('django-insecure')
    sk_ok = sk_len >= 50 and sk_secure
    print(f'[{"✅" if sk_ok else "❌"}] SECRET_KEY length: {sk_len} chars {"(>= 50)" if sk_len >= 50 else "(MUY CORTA)"}')
    print(f'[{"✅" if sk_secure else "❌"}] SECRET_KEY secure: {sk_secure} {"(no usa django-insecure)" if sk_secure else "(USA PREFIJO INSEGURO)"}')
    
    # Verificar SSL/HSTS (solo si DEBUG=False)
    if not settings.DEBUG:
        ssl_ok = getattr(settings, 'SECURE_SSL_REDIRECT', False)
        session_ok = getattr(settings, 'SESSION_COOKIE_SECURE', False)
        csrf_ok = getattr(settings, 'CSRF_COOKIE_SECURE', False)
        hsts_ok = getattr(settings, 'SECURE_HSTS_SECONDS', 0) >= 31536000
        
        print(f'[{"✅" if ssl_ok else "❌"}] SECURE_SSL_REDIRECT = {ssl_ok}')
        print(f'[{"✅" if session_ok else "❌"}] SESSION_COOKIE_SECURE = {session_ok}')
        print(f'[{"✅" if csrf_ok else "❌"}] CSRF_COOKIE_SECURE = {csrf_ok}')
        print(f'[{"✅" if hsts_ok else "❌"}] SECURE_HSTS_SECONDS = {getattr(settings, "SECURE_HSTS_SECONDS", 0)} {"(>= 31536000)" if hsts_ok else ""}')
    
    # Verificar ALLOWED_HOSTS
    ah = getattr(settings, 'ALLOWED_HOSTS', [])
    ah_ok = len(ah) > 0 and ah != ['*']
    print(f'[{"✅" if ah_ok else "⚠️ "}] ALLOWED_HOSTS = {ah}')
    
    print()
    print('╔══════════════════════════════════════════════════════════════╗')
    
    # Resultado final
    all_ok = debug_ok and sk_ok and ssl_ok and session_ok and csrf_ok and hsts_ok
    if all_ok:
        print('║   ✅ BLOQUE 1: TODAS LAS CORRECCIONES APLICADAS CORRECTAMENTE ║')
    else:
        print('║   ⚠️  BLOQUE 1: ALGUNAS CORRECCIONES REQUIEREN ATENCIÓN        ║')
    
    print('╚══════════════════════════════════════════════════════════════╝')
    
    sys.exit(0 if all_ok else 1)
    
except Exception as e:
    logging.getLogger(__name__).exception("Error inesperado en funcion_desconocida (validate_security_fixes.py)")
    print(f'❌ Error durante validación: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)