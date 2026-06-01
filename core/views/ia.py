"""
Vistas para el sistema de IA Jerárquico.
Maneja las consultas a la IA con filtros de permisos.
"""
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.utils.ia_permissions import preparar_datos_para_ia, filtrar_datos_para_ia
from core.models import Empresa, Venta, DetalleVenta, Producto, OrdenDeServicio


@login_required
@require_http_methods(["POST"])
def consultar_ia_negocios(request):
    """
    API para consultar la IA de Negocios.
    Filtra los datos según el nivel de acceso del usuario.
    """
    try:
        usuario = request.user
        empresa = usuario.empresa
        
        # Verificar que el usuario tenga permiso para usar IA de Negocios
        if not usuario.puede_ver_ia_negocios():
            return JsonResponse({
                'status': 'error',
                'mensaje': 'No tienes permisos para acceder a la IA de Negocios'
            }, status=403)
        
        # Obtener datos del request
        data = json.loads(request.body)
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        # Preparar contexto con datos financieros
        contexto = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'empresa': empresa
        }
        
        # Obtener datos financieros (solo para IA_MASTER)
        if usuario.tiene_permiso_ia_master():
            # Ventas con detalles de costos
            ventas = Venta.objects.filter(
                empresa=empresa,
                fecha__date__range=[fecha_inicio, fecha_fin],
                estado='COMPLETADA'
            ).prefetch_related('detalles__producto')
            
            ventas_data = []
            for venta in ventas:
                detalles_data = []
                for detalle in venta.detalles.all():
                    detalles_data.append({
                        'producto': detalle.producto.nombre,
                        'cantidad': detalle.cantidad,
                        'precio_unitario': float(detalle.precio_unitario),
                        'precio_compra': float(detalle.producto.precio_compra),
                        'margen': float(detalle.precio_unitario - detalle.producto.precio_compra),
                        'subtotal': float(detalle.subtotal)
                    })
                
                ventas_data.append({
                    'id': venta.id,
                    'folio': venta.folio_operacion,
                    'fecha': venta.fecha.strftime('%Y-%m-%d'),
                    'total': float(venta.total),
                    'subtotal': float(venta.subtotal),
                    'descuento': float(venta.descuento_aplicado),
                    'detalles': detalles_data
                })
            
            contexto['ventas'] = ventas_data
            
            # Productos con costos y márgenes
            productos = Producto.objects.filter(empresa=empresa)
            productos_data = []
            for producto in productos:
                productos_data.append({
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'precio_compra': float(producto.precio_compra),
                    'precio_publico': float(producto.precio_publico),
                    'margen': float(producto.precio_publico - producto.precio_compra),
                    'margen_porcentaje': float((producto.precio_publico - producto.precio_compra) / producto.precio_publico * 100) if producto.precio_publico > 0 else 0,
                    'stock': producto.stock,
                    'categoria': producto.categoria
                })
            
            contexto['productos'] = productos_data
        
        # Preparar datos para IA con filtros aplicados
        datos_para_ia = preparar_datos_para_ia(usuario, contexto)
        
        # Aquí se conectaría con la API real de IA
        # Por ahora, retornamos un análisis simulado
        analisis = generar_analisis_simulado(datos_para_ia, usuario)
        
        return JsonResponse({
            'status': 'success',
            'titulo': 'Análisis Financiero y Operativo',
            'analisis': analisis['analisis'],
            'recomendaciones': analisis['recomendaciones'],
            'datos_filtrados': datos_para_ia  # Para debugging
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Error al procesar los datos'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error: {str(e)}'
        }, status=500)


def generar_analisis_simulado(datos, usuario):
    """
    Genera un análisis simulado basado en los datos filtrados.
    En producción, esto se reemplazaría por una llamada a la API real de IA.
    """
    nivel = datos.get('usuario', {}).get('nivel_ia', 'IA_BASICA')
    
    if nivel == 'IA_MASTER':
        # Análisis completo con costos y márgenes
        productos = datos.get('productos', [])
        ventas = datos.get('ventas', [])
        
        total_ventas = sum(v.get('total', 0) for v in ventas)
        total_costos = sum(
            sum(d.get('precio_compra', 0) * d.get('cantidad', 0) for d in v.get('detalles', []))
            for v in ventas
        )
        utilidad_neta = total_ventas - total_costos
        margen_promedio = (utilidad_neta / total_ventas * 100) if total_ventas > 0 else 0
        
        analisis = f"""
        <h6>📊 Resumen Financiero</h6>
        <ul>
            <li><strong>Total de Ventas:</strong> ${total_ventas:,.2f}</li>
            <li><strong>Total de Costos:</strong> ${total_costos:,.2f}</li>
            <li><strong>Utilidad Neta:</strong> ${utilidad_neta:,.2f}</li>
            <li><strong>Margen Promedio:</strong> {margen_promedio:.2f}%</li>
        </ul>
        """
        
        recomendaciones = """
        <ul>
            <li>Revisar productos con bajo margen de ganancia</li>
            <li>Optimizar inventario de productos de alta rotación</li>
            <li>Considerar estrategias de precios dinámicos</li>
        </ul>
        """
        
    elif nivel == 'IA_TECNICA':
        # Análisis técnico sin información financiera sensible
        analisis = """
        <h6>🔬 Análisis Técnico de Laboratorio</h6>
        <p>Análisis de resultados y valores de referencia disponibles.</p>
        """
        recomendaciones = """
        <ul>
            <li>Revisar valores de referencia actualizados</li>
            <li>Verificar tiempos de entrega de resultados</li>
        </ul>
        """
        
    else:  # IA_BASICA
        # Análisis básico solo con nombres y precios
        analisis = """
        <h6>📋 Información Básica</h6>
        <p>Consulta de estudios y precios disponibles.</p>
        """
        recomendaciones = """
        <ul>
            <li>Revisar catálogo de estudios</li>
            <li>Verificar precios actualizados</li>
        </ul>
        """
    
    return {
        'analisis': analisis,
        'recomendaciones': recomendaciones
    }
