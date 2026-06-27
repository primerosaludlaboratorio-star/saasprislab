"""
Vistas del módulo PRIS Sentinel: dashboard de incidencias, feedback,
exportación de contexto para Cursor, comandos SSH, resolución masiva.
"""
import json
import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from consultorio.models import IncidenciaSentinel
from core.utils.empresa_request import empresa_efectiva_request

logger = logging.getLogger('consultorio')


# ==============================================================================
# PRIS SENTINEL: TELEMETRÍA INTELIGENTE Y GESTIÓN DE INCIDENCIAS
# ==============================================================================

@login_required
def sentinel_dashboard(request):
    """
    Dashboard de incidencias para el Director.
    v3: Filtros por namespace, botón 'SOLUCIONAR CON CURSOR', SSH quick-fix,
    y panel de autocuración compatible con Remote SSH.
    Solo accesible por superusuarios, administradores y directores.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    is_director = (
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Administrador', 'Director', 'Gerente']).exists() or
        getattr(request.user, 'rol', '') in ['ADMIN', 'DIRECTOR', 'GERENTE']
    )
    if not is_director:
        messages.error(request, 'Acceso denegado. Solo directores y administradores.')
        return redirect('consultorio:dashboard_consultorio')

    if request.method == 'POST' and request.POST.get('accion') == 'limpiar_resueltas':
        urls_resueltas = ['/favicon.ico', '/consultorio/api/resultados-disponibles/']
        count_favicon = IncidenciaSentinel.objects.filter(
            empresa=empresa,
            estado='PENDIENTE',
            url_afectada__in=urls_resueltas,
        ).update(estado='SOLUCIONADO', resuelto_por=request.user, fecha_resolucion=timezone.now())

        count_feedback = IncidenciaSentinel.objects.filter(
            empresa=empresa,
            estado='PENDIENTE',
            origen='FEEDBACK',
        ).update(estado='SOLUCIONADO', resuelto_por=request.user, fecha_resolucion=timezone.now())

        total_limpiados = count_favicon + count_feedback
        messages.success(request, f'Sentinel: {total_limpiados} incidencias marcadas como solucionadas.')
        return redirect('consultorio:sentinel_dashboard')

    estado_filtro = request.GET.get('estado', '')
    severidad_filtro = request.GET.get('severidad', '')
    namespace_filtro = request.GET.get('namespace', '')

    incidencias = IncidenciaSentinel.objects.filter(empresa=empresa)

    if estado_filtro:
        incidencias = incidencias.filter(estado=estado_filtro)
    if severidad_filtro:
        incidencias = incidencias.filter(severidad=severidad_filtro)
    if namespace_filtro:
        incidencias = incidencias.filter(namespace=namespace_filtro)

    incidencias = incidencias.select_related('usuario_reporta', 'resuelto_por').order_by('-fecha_creacion')[:100]

    stats = IncidenciaSentinel.objects.filter(empresa=empresa).aggregate(
        total=Count('id'),
        pendientes=Count('id', filter=Q(estado='PENDIENTE')),
        en_reparacion=Count('id', filter=Q(estado='EN_REPARACION')),
        solucionados=Count('id', filter=Q(estado='SOLUCIONADO')),
        criticas=Count('id', filter=Q(severidad='CRITICA', estado='PENDIENTE')),
    )

    return render(request, 'consultorio/sentinel_dashboard.html', {
        'incidencias': incidencias,
        'stats': stats,
        'estado_filtro': estado_filtro,
        'severidad_filtro': severidad_filtro,
        'namespace_filtro': namespace_filtro,
    })


@login_required
def sentinel_ssh_guide(request):
    """Guía visual paso a paso para configurar Remote SSH con Cursor."""
    return render(request, 'consultorio/sentinel_ssh_guide.html')


@login_required
def sentinel_detalle(request, incidencia_id):
    """Detalle de una incidencia con traceback completo y análisis IA."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'message': 'Usuario sin empresa asignada'}, status=403)
    incidencia = get_object_or_404(IncidenciaSentinel, id=incidencia_id, empresa=empresa)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        if nuevo_estado in ['PENDIENTE', 'EN_REPARACION', 'SOLUCIONADO']:
            incidencia.estado = nuevo_estado
            if nuevo_estado == 'SOLUCIONADO':
                incidencia.resuelto_por = request.user
                incidencia.fecha_resolucion = timezone.now()
                incidencia.notas_resolucion = request.POST.get('notas_resolucion', '')
            incidencia.save()
            messages.success(request, f'Estado actualizado a: {incidencia.get_estado_display()}')
            return redirect('consultorio:sentinel_detalle', incidencia_id=incidencia.id)

    repair_ctx = incidencia.contexto_reparacion or {}

    return render(request, 'consultorio/sentinel_detalle.html', {
        'incidencia': incidencia,
        'repair_ctx': repair_ctx,
    })


@login_required
@require_http_methods(["POST"])
def api_sentinel_feedback(request):
    """
    API: Recibe el reporte en lenguaje natural de la doctora.
    Cruza con el ultimo error tecnico para crear un Ticket de Reparacion Maestro.
    """
    _logger = logging.getLogger('sentinel')

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'message': 'Usuario sin empresa asignada'}, status=403)

    try:
        data = json.loads(request.body)
        descripcion = data.get('descripcion', '').strip()

        if not descripcion:
            return JsonResponse({'status': 'error', 'message': 'Escribe una descripcion del problema.'}, status=400)

        ultima_incidencia = None
        try:
            hace_2h = timezone.now() - timedelta(hours=2)
            ultima_incidencia = IncidenciaSentinel.objects.filter(
                empresa=empresa,
                origen='MIDDLEWARE',
                fecha_creacion__gte=hace_2h,
            ).order_by('-fecha_creacion').first()
        except (DatabaseError, ValidationError) as e:
            _logger.warning("SENTINEL FEEDBACK: Error buscando incidencias previas: %s", e)

        url_reportada = str(data.get('url_actual', request.META.get('HTTP_REFERER', '')))[:500]

        contexto_basico = f"Reporte del usuario: {descripcion}"
        incidencia = IncidenciaSentinel.objects.create(
            empresa=empresa,
            origen='FEEDBACK',
            usuario_reporta=request.user,
            url_afectada=url_reportada,
            metodo_http='POST',
            namespace='consultorio',
            codigo_http=0,
            tipo_excepcion='UserFeedback',
            traceback_completo=ultima_incidencia.traceback_completo if ultima_incidencia else '',
            datos_request={'feedback': True},
            tag='#FEEDBACK_CONSULTA',
            descripcion_usuario=descripcion,
            analisis_ia=contexto_basico,
            contexto_cursor=contexto_basico,
            estado='PENDIENTE',
            severidad=data.get('severidad', 'MEDIA'),
        )

        _logger.info("SENTINEL FEEDBACK OK: Incidencia #%s creada por %s", incidencia.id, request.user.username)

        try:
            from consultorio.sentinel_service import cruzar_feedback_con_error
            import threading

            def _enriquecer_con_ia(inc_id, desc, ult_inc):
                try:
                    contexto_maestro = cruzar_feedback_con_error(desc, ult_inc)
                    IncidenciaSentinel.objects.filter(id=inc_id).update(
                        analisis_ia=contexto_maestro,
                        contexto_cursor=contexto_maestro,
                    )
                except (DatabaseError, ValidationError, ImportError, AttributeError, ValueError, RuntimeError) as ex:
                    logging.getLogger('sentinel').warning("SENTINEL IA background: %s", ex)

            threading.Thread(
                target=_enriquecer_con_ia,
                args=(incidencia.id, descripcion, ultima_incidencia),
                daemon=True
            ).start()
        except (RuntimeError, ImportError) as e:
            _logger.warning("SENTINEL FEEDBACK: No se pudo iniciar enriquecimiento IA: %s", e)

        return JsonResponse({
            'status': 'success',
            'message': 'Tu reporte fue registrado. El equipo tecnico lo revisara.',
            'incidencia_id': incidencia.id,
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Formato de datos invalido.'}, status=400)
    except (DatabaseError, ValidationError, ValueError, TypeError) as e:
        _logger.error("SENTINEL FEEDBACK ERROR: %s: %s", type(e).__name__, e, exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'Error del servidor: {type(e).__name__}'}, status=500)


@login_required
def api_sentinel_exportar_cursor(request, incidencia_id):
    """
    API: Exporta el contexto técnico de una incidencia en formato
    listo para copiar y pegar en Cursor (Remote SSH compatible).
    """
    from consultorio.sentinel_service import (
        generar_prompt_cursor_reparacion,
        generar_resumen_ssh_rapido,
    )

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'message': 'Usuario sin empresa asignada'}, status=403)
    incidencia = get_object_or_404(IncidenciaSentinel, id=incidencia_id, empresa=empresa)

    if incidencia.contexto_reparacion:
        bloque_cursor = generar_prompt_cursor_reparacion(incidencia)
    else:
        bloque_cursor = (
            f"@Codebase PRIS SENTINEL - Ticket #{incidencia.id} (REPARACIÓN REMOTA)\n"
            f"{'=' * 60}\n"
            f"MODO: Remote SSH -> Servidor Ubuntu\n"
            f"Severidad: {incidencia.get_severidad_display()}\n"
            f"Modulo: {incidencia.namespace.upper()}\n"
            f"URL: {incidencia.metodo_http} {incidencia.url_afectada}\n"
            f"Excepcion: {incidencia.tipo_excepcion}\n"
            f"Fecha: {incidencia.fecha_creacion.strftime('%Y-%m-%d %H:%M')}\n\n"
        )

        if incidencia.descripcion_usuario:
            bloque_cursor += f"REPORTE DEL USUARIO:\n{incidencia.descripcion_usuario}\n\n"

        if incidencia.contexto_cursor:
            bloque_cursor += f"ANALISIS IA:\n{incidencia.contexto_cursor}\n\n"

        bloque_cursor += (
            f"TRACEBACK COMPLETO:\n"
            f"{incidencia.traceback_completo}\n\n"
            f"INSTRUCCION: Corrige este error. El servidor está conectado via "
            f"Remote SSH. Ruta del proyecto: /app/. Los cambios se aplican en vivo.\n"
        )

    ssh_rapido = ''
    if incidencia.contexto_reparacion:
        ssh_rapido = generar_resumen_ssh_rapido(incidencia)

    if incidencia.estado == 'PENDIENTE':
        incidencia.estado = 'EN_REPARACION'
        incidencia.resuelto_por = request.user
        incidencia.save(update_fields=['estado', 'resuelto_por', 'fecha_modificacion'])

    ctx_rep = incidencia.contexto_reparacion or {}

    return JsonResponse({
        'status': 'success',
        'bloque_cursor': bloque_cursor,
        'ssh_rapido': ssh_rapido,
        'incidencia_id': incidencia.id,
        'tiene_reparacion': bool(ctx_rep),
        'reparacion': {
            'archivo': ctx_rep.get('archivo_principal', ''),
            'linea': ctx_rep.get('linea_error', 0),
            'funcion': ctx_rep.get('funcion_afectada', ''),
            'causa': ctx_rep.get('causa_raiz', ''),
            'codigo_original': ctx_rep.get('codigo_original', ''),
            'codigo_propuesto': ctx_rep.get('codigo_propuesto', ''),
            'instrucciones_ssh': ctx_rep.get('instrucciones_ssh', ''),
            'riesgo': ctx_rep.get('riesgo_regresion', ''),
            'tiempo': ctx_rep.get('tiempo_estimado', ''),
            'archivos_relacionados': ctx_rep.get('archivos_relacionados', []),
        } if ctx_rep else {},
    })


@login_required
def api_sentinel_ssh(request, incidencia_id):
    """
    API: Genera comandos SSH rápidos para reparación directa en terminal.
    Compatible con conexiones Remote SSH al servidor Ubuntu de producción.
    """
    from consultorio.sentinel_service import generar_resumen_ssh_rapido

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'message': 'Usuario sin empresa asignada'}, status=403)
    incidencia = get_object_or_404(IncidenciaSentinel, id=incidencia_id, empresa=empresa)
    comandos_ssh = generar_resumen_ssh_rapido(incidencia)

    ctx = incidencia.contexto_reparacion or {}

    return JsonResponse({
        'status': 'success',
        'comandos_ssh': comandos_ssh,
        'incidencia_id': incidencia.id,
        'archivo': ctx.get('archivo_principal', ''),
        'linea': ctx.get('linea_error', 0),
        'ruta_contenedor': f"/app/{ctx.get('archivo_principal', '')}",
    })


@login_required
def api_test_github_sentinel(request):
    """
    API de prueba: Verifica la conexion con GitHub y opcionalmente crea un issue de test.
    Solo accesible por superusuarios.
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'mensaje': 'Solo superusuarios'}, status=403)

    from core.services.github_reporter import test_github_connection, crear_github_issue, GITHUB_TOKEN, GITHUB_REPO

    if request.method == 'GET':
        ok, msg = test_github_connection()
        return JsonResponse({
            'status': 'success' if ok else 'error',
            'conexion': ok,
            'mensaje': msg,
            'config': {
                'token_configurado': bool(GITHUB_TOKEN),
                'repo': GITHUB_REPO or 'NO CONFIGURADO',
            }
        })

    elif request.method == 'POST':
        ok, msg = test_github_connection()
        if not ok:
            return JsonResponse({'status': 'error', 'mensaje': f'Conexion fallida: {msg}'}, status=500)

        resultado = crear_github_issue({
            'tipo_excepcion': 'TestSentinel',
            'traceback_texto': (
                'Traceback (most recent call last):\\n'
                '  File "consultorio/views.py", line 999, in test_view\\n'
                '    raise TestSentinel("Prueba de notificacion")\\n'
                'TestSentinel: Prueba de notificacion de PRIS Sentinel\\n'
                '\\n'
                'NOTA: Este es un issue de PRUEBA generado automaticamente\\n'
                'para verificar que las notificaciones de GitHub funcionan.\\n'
                'Puede cerrar este issue de forma segura.'
            ),
            'path': '/api/sentinel/test-github/',
            'url': '/api/sentinel/test-github/',
            'metodo': 'POST',
            'severidad': 'BAJA',
            'namespace': 'sentinel',
            'codigo_http': 200,
            'user_id': request.user.id,
        })

        if resultado:
            return JsonResponse({
                'status': 'success',
                'mensaje': 'Issue de prueba creado exitosamente en GitHub',
                'issue_url': resultado.get('issue_url'),
                'issue_number': resultado.get('issue_number'),
            })
        else:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'No se pudo crear el issue. Puede ser rate limit o deduplicacion.'
            }, status=500)

    return JsonResponse({'status': 'error', 'mensaje': 'Metodo no permitido'}, status=405)


@login_required
@require_http_methods(['POST'])
def api_resolver_incidencias_sentinel(request):
    """
    API: Marca como SOLUCIONADO todas las incidencias Sentinel
    que correspondan a errores ya corregidos.
    Solo accesible por superusuarios.
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'mensaje': 'Solo superusuarios'}, status=403)

    ahora = timezone.now()

    patrones = [
        {'filtro': {'tipo_excepcion__icontains': 'NameError'}, 'nota': 'Fix: timezone import en sentinel.py'},
        {'filtro': {'tipo_excepcion__icontains': 'FieldError', 'url_afectada__icontains': 'entrega-resultados'}, 'nota': 'Fix: bitacora_entrega removido de select_related'},
        {'filtro': {'tipo_excepcion__icontains': 'FieldError', 'url_afectada__icontains': 'medicos'}, 'nota': 'Fix: empresa filter removido de Medico'},
        {'filtro': {'tipo_excepcion__icontains': 'FieldError', 'url_afectada__icontains': 'compras'}, 'nota': 'Fix: activo filter removido de Producto'},
        {'filtro': {'tipo_excepcion__icontains': 'TypeError', 'url_afectada__icontains': 'paciente'}, 'nota': 'Fix: registrar_trazabilidad args corregidos'},
        {'filtro': {'tipo_excepcion__icontains': 'ReferenceError'}, 'nota': 'Fix: funciones JS expuestas a scope global'},
        {'filtro': {'tipo_excepcion': 'UserFeedback'}, 'nota': 'Resuelto: errores reportados ya corregidos'},
        {'filtro': {'tag': '#BUG_FARMACIA', 'url_afectada__icontains': 'pdv'}, 'nota': 'Fix: PDV farmacia corregido'},
    ]

    total = 0
    detalles = []
    for p in patrones:
        qs = IncidenciaSentinel.objects.filter(
            estado__in=['PENDIENTE', 'EN_REPARACION'],
            **p['filtro'],
        )
        count = qs.count()
        if count > 0:
            qs.update(
                estado='SOLUCIONADO',
                notas_resolucion=p['nota'],
                fecha_resolucion=ahora,
            )
            total += count
            detalles.append(f"{count}x {p['nota']}")

    for patron_tb in ['timezone', 'bitacora_entrega', 'activo', 'empresa',
                       'abrirModalReceta', 'validarCamposConsultorio',
                       'enviarErrorAlServidor', 'contenedor-productos']:
        qs_tb = IncidenciaSentinel.objects.filter(
            estado__in=['PENDIENTE', 'EN_REPARACION'],
            traceback_completo__icontains=patron_tb,
        )
        count_tb = qs_tb.count()
        if count_tb > 0:
            qs_tb.update(
                estado='SOLUCIONADO',
                notas_resolucion=f'Fix automatico: error de {patron_tb} resuelto',
                fecha_resolucion=ahora,
            )
            total += count_tb

    pendientes = IncidenciaSentinel.objects.filter(
        estado__in=['PENDIENTE', 'EN_REPARACION']
    ).count()

    logger.info('SENTINEL: %s incidencias marcadas como SOLUCIONADO, %s pendientes', total, pendientes)

    return JsonResponse({
        'status': 'success',
        'resueltas': total,
        'pendientes_restantes': pendientes,
        'detalles': detalles,
    })


@login_required
@require_http_methods(['GET'])
def api_sentinel_listar_feedback(request):
    """
    API: Lista las incidencias con feedback del usuario (descripcion_usuario).
    Solo accesible por superusuarios.
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'mensaje': 'Solo superusuarios'}, status=403)

    incidencias = IncidenciaSentinel.objects.filter(
        origen='FEEDBACK',
    ).order_by('-fecha_creacion').values(
        'id', 'descripcion_usuario', 'url_afectada', 'estado',
        'severidad', 'fecha_creacion', 'notas_resolucion',
        'usuario_reporta__username', 'usuario_reporta__first_name',
    )[:50]

    items = []
    for inc in incidencias:
        items.append({
            'id': inc['id'],
            'usuario': inc['usuario_reporta__first_name'] or inc['usuario_reporta__username'] or 'Anon',
            'descripcion': inc['descripcion_usuario'],
            'url': inc['url_afectada'],
            'estado': inc['estado'],
            'severidad': inc['severidad'],
            'fecha': inc['fecha_creacion'].strftime('%Y-%m-%d %H:%M') if inc['fecha_creacion'] else '',
            'notas_resolucion': inc['notas_resolucion'] or '',
        })

    return JsonResponse({'status': 'success', 'feedback': items, 'total': len(items)})
