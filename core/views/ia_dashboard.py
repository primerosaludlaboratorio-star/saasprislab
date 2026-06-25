"""
PRISLAB V5 - Dashboard de Actividad (Panel del Director)
Muestra actividad reciente, contadores del dia y acceso a IA.
"""
import json
import logging
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import localdate
from django.views.decorators.http import require_http_methods

from core.ai_brain import responder

logger = logging.getLogger(__name__)


@login_required
def ia_dashboard(request):
    """
    Panel del Director: Actividad reciente + Contadores + IA Chat.
    URL: /ia/panel/
    """
    empresa = getattr(request.user, 'empresa', None)
    empresa_nombre = empresa.nombre if empresa and hasattr(empresa, 'nombre') else ""
    
    hoy = localdate()
    hoy_inicio = timezone.make_aware(
        datetime.combine(hoy, datetime.min.time())
    )
    
    # ============ CONTADORES RAPIDOS ============
    contadores = {
        'muestras_hoy': 0,
        'consultas_hoy': 0,
        'ventas_hoy': 0,
        'pacientes_total': 0,
    }
    
    try:
        from core.models import OrdenDeServicio, Paciente, Venta, ConsultaMedica
        
        if empresa:
            contadores['muestras_hoy'] = OrdenDeServicio.objects.filter(
                empresa=empresa,
                fecha_creacion__date=hoy
            ).count()
            
            contadores['pacientes_total'] = Paciente.objects.filter(
                empresa=empresa
            ).count()
            
            try:
                contadores['ventas_hoy'] = Venta.objects.filter(
                    empresa=empresa,
                    fecha__date=hoy
                ).count()
            except Exception:
                pass
            
            try:
                contadores['consultas_hoy'] = ConsultaMedica.objects.filter(
                    empresa=empresa,
                    fecha_consulta__date=hoy
                ).count()
            except Exception:
                pass
                
    except Exception as e:
        logger.warning(f"Error obteniendo contadores: {e}")
    
    # ============ ACTIVIDAD RECIENTE ============
    ultimos_pacientes = []
    ultimos_estudios = []
    
    try:
        from core.models import Paciente, OrdenDeServicio, DetalleOrden
        
        if empresa:
            # Ultimos 5 pacientes registrados
            for p in Paciente.objects.filter(empresa=empresa).order_by('-id')[:5]:
                ultimos_pacientes.append({
                    'nombre': p.nombre_completo,
                    'telefono': p.telefono or '',
                    'sexo': p.sexo or '',
                    'id': p.id,
                    'uuid': str(p.uuid) if p.uuid else '',
                })
            
            # Ultimas 5 ordenes completadas
            for o in OrdenDeServicio.objects.filter(
                empresa=empresa,
                estado_clinico__in=['COMPLETO', 'ENTREGADO', 'RESULTADOS_LISTOS']
            ).select_related('paciente').order_by('-fecha_creacion')[:5]:
                ultimos_estudios.append({
                    'folio': o.folio_orden or f'ORD-{o.id}',
                    'paciente': o.paciente.nombre_completo,
                    'estado': o.get_estado_clinico_display() if hasattr(o, 'get_estado_clinico_display') else o.estado_clinico,
                    'fecha': o.fecha_creacion.strftime('%d/%m %H:%M') if o.fecha_creacion else '',
                    'id': o.id,
                })
    except Exception as e:
        logger.warning(f"Error obteniendo actividad reciente: {e}")

    # ============ ALERTAS DE INVENTARIO CRITICO ============
    alertas_stock = []
    STOCK_CRITICO_UMBRAL = 5  # Productos con stock <= 5 son criticos

    try:
        from core.models import Producto
        if empresa:
            productos_criticos = Producto.objects.filter(
                empresa=empresa,
                stock__lte=STOCK_CRITICO_UMBRAL,
                stock__gte=0,
            ).order_by('stock')[:15]

            for prod in productos_criticos:
                alertas_stock.append({
                    'nombre': prod.nombre,
                    'sustancia': prod.sustancia_activa or '',
                    'stock': prod.stock,
                    'precio': float(prod.precio_publico),
                    'codigo': prod.codigo_barras or '',
                    'es_cero': prod.stock <= 0,
                })
    except Exception as e:
        logger.warning(f"Error obteniendo alertas de stock: {e}")

    # ============ SENTINEL 2.0: AUDITORIA IA ============
    sentinel_data = {
        'incidencias_pendientes': 0,
        'incidencias_criticas': 0,
        'ultimas_incidencias': [],
        'audit_logs_hoy': 0,
        'sugerencias_proceso': [],
        'salud_sistema': 'OK',
    }

    try:
        from consultorio.models import IncidenciaSentinel

        if empresa:
            # Incidencias pendientes
            inc_pendientes = IncidenciaSentinel.objects.filter(
                empresa=empresa,
                estado='PENDIENTE',
            )
            sentinel_data['incidencias_pendientes'] = inc_pendientes.count()
            sentinel_data['incidencias_criticas'] = inc_pendientes.filter(
                severidad='CRITICA'
            ).count()

            # Ultimas 5 incidencias
            for inc in IncidenciaSentinel.objects.filter(
                empresa=empresa
            ).order_by('-fecha_creacion')[:5]:
                sentinel_data['ultimas_incidencias'].append({
                    'id': inc.id,
                    'tipo': inc.tipo_excepcion or 'N/A',
                    'url': inc.url_afectada or '',
                    'severidad': inc.severidad,
                    'estado': inc.estado,
                    'fecha': inc.fecha_creacion.strftime('%d/%m %H:%M') if inc.fecha_creacion else '',
                    'analisis': (inc.analisis_ia or '')[:200],
                })

        # AuditLogs de hoy
        from core.models import AuditLog
        if empresa:
            sentinel_data['audit_logs_hoy'] = AuditLog.objects.filter(
                empresa=empresa,
                fecha_cierta__date=hoy,
            ).count()

        # Sugerencias de proceso IA
        from core.services.validador_ia import generar_sugerencias_proceso
        if empresa:
            sentinel_data['sugerencias_proceso'] = generar_sugerencias_proceso(empresa)

        # Determinar salud del sistema
        if sentinel_data['incidencias_criticas'] > 0:
            sentinel_data['salud_sistema'] = 'CRITICA'
        elif sentinel_data['incidencias_pendientes'] > 3:
            sentinel_data['salud_sistema'] = 'ALERTA'
        else:
            sentinel_data['salud_sistema'] = 'OK'

    except Exception as e:
        logger.warning(f"Error obteniendo datos Sentinel: {e}")

    return render(
        request,
        "core/ia_dashboard.html",
        {
            "empresa_nombre": empresa_nombre,
            "contadores": contadores,
            "ultimos_pacientes": ultimos_pacientes,
            "ultimos_estudios": ultimos_estudios,
            "alertas_stock": alertas_stock,
            "fecha_hoy": hoy.strftime('%d/%m/%Y'),
            "sentinel": sentinel_data,
        },
    )


@login_required
@require_http_methods(["POST"])
def api_ia_chat(request):
    """
    POST /api/ia/chat/
    Body JSON: { mensaje: str }
    Responde usando el Cerebro Dual (PRIS/LIA).
    """
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}

    mensaje = (data.get("mensaje") or "").strip()
    if not mensaje:
        return JsonResponse({"status": "error", "mensaje": "Mensaje vacio."}, status=400)

    try:
        out = responder(request.user, mensaje)
    except Exception as e:
        logger.error(f"Error CRITICO en responder() desde api_ia_chat: {str(e)}", exc_info=True)
        return JsonResponse({"status": "error", "mensaje": f"Error interno en cerebro IA: {str(e)}"}, status=500)

    if out.get("ok") is False:
        return JsonResponse({"status": "error", "mensaje": out.get("mensaje", "No se pudo responder.")}, status=400)

    texto = out.get("respuesta") or out.get("mensaje") or ""
    return JsonResponse({"status": "success", "respuesta": texto, "meta": out})


@login_required
@require_http_methods(["POST"])
def api_ia_diagnostico(request):
    """
    POST /api/ia/diagnostico/
    SENTINEL 2.0: Genera un diagnostico completo del sistema en tiempo real.
    Responde a "Que esta fallando?" con datos tecnicos y operativos.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa'}, status=400)

    diagnostico = {
        'salud': 'OK',
        'problemas': [],
        'sugerencias': [],
        'metricas': {},
    }

    try:
        # 1. Incidencias activas
        from consultorio.models import IncidenciaSentinel
        pendientes = IncidenciaSentinel.objects.filter(
            empresa=empresa, estado='PENDIENTE'
        )
        criticas = pendientes.filter(severidad='CRITICA').count()
        altas = pendientes.filter(severidad='ALTA').count()

        if criticas > 0:
            diagnostico['salud'] = 'CRITICA'
            diagnostico['problemas'].append(
                f'{criticas} incidencia(s) CRITICA(s) sin resolver. '
                f'Revisar panel de incidencias.'
            )
        if altas > 0:
            diagnostico['problemas'].append(
                f'{altas} incidencia(s) de severidad ALTA pendientes.'
            )

        # 2. Ordenes estancadas
        from core.models import OrdenDeServicio
        estancadas = OrdenDeServicio.objects.filter(
            empresa=empresa,
            estado_clinico='PENDIENTE_TOMA',
            fecha_creacion__lt=timezone.now() - timedelta(hours=24),
            deleted_at__isnull=True,
        ).count()
        if estancadas > 0:
            diagnostico['problemas'].append(
                f'{estancadas} ordenes estancadas (>24h sin toma de muestra).'
            )

        # 3. Stock critico
        from core.models import Producto
        stock_critico = Producto.objects.filter(
            empresa=empresa, stock__lte=3, stock__gte=0
        ).count()
        if stock_critico > 0:
            diagnostico['problemas'].append(
                f'{stock_critico} productos con stock critico (<=3 unidades).'
            )

        # 4. Sugerencias de proceso
        from core.services.validador_ia import generar_sugerencias_proceso
        diagnostico['sugerencias'] = [
            s['mensaje'] for s in generar_sugerencias_proceso(empresa)
        ]

        # 5. Metricas del dia
        hoy = localdate()
        diagnostico['metricas'] = {
            'ordenes_hoy': OrdenDeServicio.objects.filter(
                empresa=empresa, fecha_creacion__date=hoy
            ).count(),
            'completadas_hoy': OrdenDeServicio.objects.filter(
                empresa=empresa, estado_clinico='COMPLETO',
                fecha_creacion__date=hoy
            ).count(),
            'incidencias_hoy': IncidenciaSentinel.objects.filter(
                empresa=empresa, fecha_creacion__date=hoy
            ).count(),
        }

        # 6. Si todo bien
        if not diagnostico['problemas']:
            diagnostico['salud'] = 'OK'
            diagnostico['problemas'].append(
                'Sistema operando con normalidad. Sin problemas detectados.'
            )

    except Exception as e:
        diagnostico['problemas'].append(f'Error ejecutando diagnostico: {str(e)}')
        diagnostico['salud'] = 'ERROR'
        logger.error(f'Error en diagnostico IA: {e}')

    return JsonResponse({'status': 'success', 'diagnostico': diagnostico})


@login_required
@require_http_methods(["POST"])
def api_ia_consultar_negocios(request):
    """
    POST /api/ia/consultar-negocios/
    Analiza datos financieros y operativos usando IA.
    """
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}

    empresa = getattr(request.user, 'empresa', None)
    empresa_nombre = data.get("empresa", {}).get("nombre", "")
    if not empresa_nombre and empresa:
        empresa_nombre = empresa.nombre or ""
    fecha_inicio = data.get("fecha_inicio", "")
    fecha_fin = data.get("fecha_fin", "")

    mensaje = f"Analiza los datos financieros y operativos de {empresa_nombre}"
    if fecha_inicio and fecha_fin:
        mensaje += f" del periodo {fecha_inicio} al {fecha_fin}"
    mensaje += ". Proporciona un analisis completo con recomendaciones estrategicas."

    out = responder(request.user, mensaje)
    
    if out.get("ok") is False:
        return JsonResponse({
            "status": "error",
            "mensaje": out.get("mensaje", "No se pudo generar el analisis.")
        }, status=400)

    respuesta = out.get("respuesta") or out.get("mensaje") or ""
    
    return JsonResponse({
        "status": "success",
        "titulo": "Analisis de Negocios",
        "analisis": respuesta,
        "recomendaciones": "Revisa el analisis completo arriba para obtener recomendaciones especificas."
    })
