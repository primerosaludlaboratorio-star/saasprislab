"""
Utilidad para detectar y corregir errores comunes encontrados durante pruebas E2E.
"""

import re
import os
from pathlib import Path


def corregir_strip_en_vistas():
    """Corrige problemas de .strip() en campos None."""
    archivos_vistas = [
        'core/views/farmacia.py',
        'core/views/laboratorio.py',
        'laboratorio/views.py',
    ]
    
    correcciones = []
    
    for archivo in archivos_vistas:
        if not os.path.exists(archivo):
            continue
        
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        contenido_original = contenido
        
        # Patrón: request.POST.get('campo').strip() o data.get('campo').strip()
        patrones = [
            (r"(\w+)\.get\(['\"](\w+)['\"]\)\.strip\(\)", r"\1.get('\2', '').strip()"),
            (r"(\w+)\['(\w+)'\]\.strip\(\)", r"(\1.get('\2', '') if isinstance(\1, dict) else \1['\2']).strip()"),
        ]
        
        for patron, reemplazo in patrones:
            contenido = re.sub(patron, reemplazo, contenido)
        
        if contenido != contenido_original:
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write(contenido)
            correcciones.append(f"Corregido: {archivo}")
    
    return correcciones


def corregir_fecha_strftime():
    """Corrige errores de strftime en fechas."""
    archivos = [
        'laboratorio/views.py',
        'core/views/laboratorio.py',
    ]
    
    correcciones = []
    
    for archivo in archivos:
        if not os.path.exists(archivo):
            continue
        
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        contenido_original = contenido
        
        # Buscar patrones problemáticos: fecha_str.strftime() donde fecha_str es string
        # Reemplazar con conversión a date primero
        
        # Patrón común: fecha_nacimiento_str.strftime()
        if 'fecha_nacimiento_str.strftime' in contenido:
            contenido = contenido.replace(
                'fecha_nacimiento_str.strftime',
                'datetime.strptime(fecha_nacimiento_str, "%Y-%m-%d").date().strftime'
            )
            correcciones.append(f"Corregido strftime en: {archivo}")
        
        if contenido != contenido_original:
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write(contenido)
    
    return correcciones


def corregir_calculos_javascript():
    """Verifica y corrige problemas en cálculos JavaScript."""
    archivos_js = [
        'core/templates/core/pdv_farmacia.html',
        'laboratorio/templates/laboratorio/crear_orden.html',
    ]
    
    correcciones = []
    
    for archivo in archivos_js:
        if not os.path.exists(archivo):
            continue
        
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        contenido_original = contenido
        
        # Buscar sumas de strings sin parseFloat
        # Patrón: precio + cantidad (debería ser parseFloat(precio) + parseFloat(cantidad))
        patron = r'(\w+)\s*\+\s*(\w+)'
        # Solo reemplazar si está en contexto de cálculo numérico
        # (esto es más complejo, mejor hacerlo manualmente)
        
        # Verificar que los cálculos usen parseFloat
        if 'subtotal' in contenido.lower() and 'parseFloat' not in contenido:
            # Agregar función helper si no existe
            if 'function calcularTotal' in contenido or 'function actualizarTotal' in contenido:
                # Ya tiene función, verificar que use parseFloat
                pass
            else:
                # Agregar función helper
                helper_js = """
<script>
function safeParseFloat(value) {
    const num = parseFloat(value) || 0;
    return isNaN(num) ? 0 : num;
}
</script>
"""
                # Insertar antes del cierre de </body> o </head>
                if '</body>' in contenido:
                    contenido = contenido.replace('</body>', helper_js + '</body>')
                    correcciones.append(f"Agregada función helper en: {archivo}")
        
        if contenido != contenido_original:
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write(contenido)
    
    return correcciones


def ejecutar_correcciones():
    """Ejecuta todas las correcciones automáticas."""
    print("Ejecutando correcciones automáticas...")
    
    todas_correcciones = []
    todas_correcciones.extend(corregir_strip_en_vistas())
    todas_correcciones.extend(corregir_fecha_strftime())
    todas_correcciones.extend(corregir_calculos_javascript())
    
    if todas_correcciones:
        print("\nCorrecciones aplicadas:")
        for corr in todas_correcciones:
            print(f"  - {corr}")
    else:
        print("\nNo se encontraron correcciones necesarias.")
    
    return todas_correcciones
