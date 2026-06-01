"""
Utilidades para el sistema de permisos jerárquico de IA.
Filtra datos según el nivel de acceso del usuario.
"""
from decimal import Decimal
from typing import Dict, List, Any, Optional


def filtrar_datos_para_ia(usuario, datos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filtra los datos según el nivel de acceso a IA del usuario.
    
    Args:
        usuario: Instancia de Usuario
        datos: Diccionario con los datos a filtrar
    
    Returns:
        Diccionario con los datos filtrados según el nivel de acceso
    """
    nivel = usuario.nivel_ia if hasattr(usuario, 'nivel_ia') else 'IA_BASICA'
    
    if nivel == 'IA_MASTER' or usuario.is_superuser:
        # Acceso completo: no se filtra nada
        return datos
    
    elif nivel == 'IA_TECNICA':
        # Puede ver resultados de laboratorio y valores de referencia
        return filtrar_ia_tecnica(datos)
    
    else:  # IA_BASICA
        # Solo nombres de estudios y precios
        return filtrar_ia_basica(datos)


def filtrar_ia_basica(datos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filtro para nivel IA_BASICA: Solo nombres de estudios y precios.
    """
    datos_filtrados = {}
    
    # Estudios de laboratorio
    if 'estudios' in datos:
        estudios_filtrados = []
        for estudio in datos['estudios']:
            estudios_filtrados.append({
                'id': estudio.get('id'),
                'nombre': estudio.get('nombre'),
                'codigo': estudio.get('codigo'),
                'precio': estudio.get('precio'),
                'categoria': estudio.get('categoria', {}).get('nombre') if isinstance(estudio.get('categoria'), dict) else estudio.get('categoria')
            })
        datos_filtrados['estudios'] = estudios_filtrados
    
    # Productos de farmacia
    if 'productos' in datos:
        productos_filtrados = []
        for producto in datos['productos']:
            productos_filtrados.append({
                'id': producto.get('id'),
                'nombre': producto.get('nombre'),
                'precio_publico': producto.get('precio_publico'),
                'categoria': producto.get('categoria')
            })
        datos_filtrados['productos'] = productos_filtrados
    
    # Ventas (solo totales, sin costos)
    if 'ventas' in datos:
        ventas_filtradas = []
        for venta in datos['ventas']:
            ventas_filtradas.append({
                'id': venta.get('id'),
                'fecha': venta.get('fecha'),
                'total': venta.get('total'),
                'cliente': venta.get('cliente')
            })
        datos_filtrados['ventas'] = ventas_filtradas
    
    # Mantener otros campos que no sean sensibles
    campos_permitidos = ['fecha_inicio', 'fecha_fin', 'empresa', 'usuario']
    for campo in campos_permitidos:
        if campo in datos:
            datos_filtrados[campo] = datos[campo]
    
    return datos_filtrados


def filtrar_ia_tecnica(datos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filtro para nivel IA_TECNICA: Resultados de laboratorio y valores de referencia.
    """
    datos_filtrados = {}
    
    # Estudios con resultados
    if 'estudios' in datos:
        estudios_filtrados = []
        for estudio in datos['estudios']:
            estudio_filtrado = {
                'id': estudio.get('id'),
                'nombre': estudio.get('nombre'),
                'codigo': estudio.get('codigo'),
                'precio': estudio.get('precio'),
                'categoria': estudio.get('categoria', {}).get('nombre') if isinstance(estudio.get('categoria'), dict) else estudio.get('categoria'),
                'valores_referencia': estudio.get('valores_referencia_texto'),
                'muestra_requerida': estudio.get('muestra_requerida'),
                'indicaciones': estudio.get('indicaciones')
            }
            estudios_filtrados.append(estudio_filtrado)
        datos_filtrados['estudios'] = estudios_filtrados
    
    # Resultados de laboratorio
    if 'resultados' in datos:
        datos_filtrados['resultados'] = datos['resultados']
    
    # Órdenes de servicio (sin información financiera sensible)
    if 'ordenes' in datos:
        ordenes_filtradas = []
        for orden in datos['ordenes']:
            orden_filtrada = {
                'id': orden.get('id'),
                'folio': orden.get('folio_orden'),
                'paciente': orden.get('paciente', {}).get('nombre_completo') if isinstance(orden.get('paciente'), dict) else orden.get('paciente'),
                'fecha': orden.get('fecha_creacion'),
                'estado': orden.get('estado'),
                'estudios': orden.get('estudios', [])
            }
            ordenes_filtradas.append(orden_filtrada)
        datos_filtrados['ordenes'] = ordenes_filtradas
    
    # Productos (sin costos)
    if 'productos' in datos:
        productos_filtrados = []
        for producto in datos['productos']:
            productos_filtrados.append({
                'id': producto.get('id'),
                'nombre': producto.get('nombre'),
                'precio_publico': producto.get('precio_publico'),
                'categoria': producto.get('categoria'),
                'stock': producto.get('stock')
            })
        datos_filtrados['productos'] = productos_filtrados
    
    # Mantener otros campos
    campos_permitidos = ['fecha_inicio', 'fecha_fin', 'empresa', 'usuario']
    for campo in campos_permitidos:
        if campo in datos:
            datos_filtrados[campo] = datos[campo]
    
    return datos_filtrados


def preparar_datos_para_ia(usuario, contexto: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepara los datos del contexto para enviarlos a la API de IA,
    aplicando los filtros según el nivel de acceso.
    
    Args:
        usuario: Instancia de Usuario
        contexto: Diccionario con el contexto de la vista
    
    Returns:
        Diccionario con los datos preparados y filtrados
    """
    datos_para_ia = {
        'usuario': {
            'id': usuario.id,
            'username': usuario.username,
            'nivel_ia': usuario.nivel_ia if hasattr(usuario, 'nivel_ia') else 'IA_BASICA',
            'rol': usuario.rol
        },
        'empresa': {
            'id': usuario.empresa.id if usuario.empresa else None,
            'nombre': usuario.empresa.nombre if usuario.empresa else None
        }
    }
    
    # Agregar datos del contexto
    if 'estudios' in contexto:
        datos_para_ia['estudios'] = contexto['estudios']
    
    if 'productos' in contexto:
        datos_para_ia['productos'] = contexto['productos']
    
    if 'ventas' in contexto:
        datos_para_ia['ventas'] = contexto['ventas']
    
    if 'resultados' in contexto:
        datos_para_ia['resultados'] = contexto['resultados']
    
    if 'ordenes' in contexto:
        datos_para_ia['ordenes'] = contexto['ordenes']
    
    # Aplicar filtros según el nivel de acceso
    datos_filtrados = filtrar_datos_para_ia(usuario, datos_para_ia)
    
    return datos_filtrados
