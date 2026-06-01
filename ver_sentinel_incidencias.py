#!/usr/bin/env python
"""
Buscar incidencias registradas por PRIS Sentinel
"""
import sys
import os
import django

sys.path.append(r'C:\Users\jonil\Desktop\PRISLAB_SaaS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from consultorio.models import SentinelIncidencia

print("=" * 100)
print("INCIDENCIAS REGISTRADAS POR PRIS SENTINEL")
print("=" * 100)

# Obtener las últimas 5 incidencias
incidencias = SentinelIncidencia.objects.all().order_by('-created_at')[:5]

if not incidencias.exists():
    print("\nNo se encontraron incidencias registradas por Sentinel")
else:
    for inc in incidencias:
        print(f"\n{'=' * 100}")
        print(f"ID: {inc.id}")
        print(f"Fecha: {inc.created_at}")
        print(f"Módulo: {inc.modulo}")
        print(f"Vista: {inc.vista}")
        print(f"Usuario: {inc.usuario}")
        print(f"Tipo: {inc.tipo_error}")
        print(f"Estado: {inc.estado}")
        print(f"\nMensaje de Error:")
        print(f"  {inc.mensaje_error}")
        
        if inc.traceback_completo:
            print(f"\nTraceback:")
            # Mostrar solo las últimas líneas del traceback
            tb_lines = inc.traceback_completo.split('\n')
            for line in tb_lines[-30:]:
                print(f"  {line}")
        
        if inc.solucion_ia:
            print(f"\nSolución sugerida por IA:")
            print(f"  {inc.solucion_ia[:500]}")
        
        print("=" * 100)
