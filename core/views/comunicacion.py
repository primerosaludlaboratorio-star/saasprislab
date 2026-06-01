"""
PRIS-Chat: APIs de Mensajeria Interna (Estandar WhatsApp).
Envio de texto, notas de voz, lista de conversaciones, polling.
"""
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Max, Subquery, OuterRef, Count
from django.utils import timezone
from django.shortcuts import render

from core.models import MensajeInterno, Usuario


@login_required
def chat_page(request):
    """Pagina dedicada del chat PRIS-Chat (fullscreen WhatsApp-style)."""
    return render(request, 'core/pris_chat.html')


@login_required
def api_enviar_mensaje(request):
    """API para enviar mensaje de texto."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Metodo no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        destinatario_id = data.get('destinatario_id')
        mensaje = data.get('mensaje', '').strip()
        
        if not destinatario_id:
            return JsonResponse({'status': 'error', 'mensaje': 'Destinatario requerido'}, status=400)
        if not mensaje:
            return JsonResponse({'status': 'error', 'mensaje': 'Mensaje vacio'}, status=400)
        
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=400)
        try:
            destinatario = Usuario.objects.get(id=destinatario_id, empresa=empresa)
        except Usuario.DoesNotExist:
            return JsonResponse({'status': 'error', 'mensaje': 'Destinatario no encontrado'}, status=404)
        
        msg = MensajeInterno.objects.create(
            remitente=request.user,
            destinatario=destinatario,
            mensaje=mensaje,
            tipo='texto'
        )
        
        return JsonResponse({
            'status': 'success',
            'mensaje_id': msg.id,
            'fecha': timezone.localtime(msg.fecha).strftime('%H:%M'),
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'JSON invalido'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_enviar_audio(request):
    """API para enviar nota de voz (FormData con archivo)."""
    try:
        destinatario_id = request.POST.get('destinatario_id')
        audio_file = request.FILES.get('audio')
        
        if not destinatario_id:
            return JsonResponse({'status': 'error', 'mensaje': 'Destinatario requerido'}, status=400)
        if not audio_file:
            return JsonResponse({'status': 'error', 'mensaje': 'Archivo de audio requerido'}, status=400)
        
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=400)
        try:
            destinatario = Usuario.objects.get(id=destinatario_id, empresa=empresa)
        except Usuario.DoesNotExist:
            return JsonResponse({'status': 'error', 'mensaje': 'Destinatario no encontrado'}, status=404)
        
        msg = MensajeInterno.objects.create(
            remitente=request.user,
            destinatario=destinatario,
            mensaje='',
            tipo='audio',
            audio=audio_file,
        )
        
        return JsonResponse({
            'status': 'success',
            'mensaje_id': msg.id,
            'audio_url': msg.audio.url if msg.audio else '',
            'fecha': timezone.localtime(msg.fecha).strftime('%H:%M'),
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
def api_obtener_mensajes(request):
    """API para obtener mensajes de una conversacion (polling)."""
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'mensaje': 'Metodo no permitido'}, status=405)
    
    destinatario_id = request.GET.get('destinatario_id')
    after_id = request.GET.get('after_id')  # Para polling incremental
    
    if not destinatario_id:
        return JsonResponse({'status': 'error', 'mensaje': 'Destinatario requerido'}, status=400)
    
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=400)
    try:
        destinatario = Usuario.objects.get(id=destinatario_id, empresa=empresa)
    except Usuario.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Destinatario no encontrado'}, status=404)
    
    # Obtener mensajes bidireccionales
    queryset = MensajeInterno.objects.filter(
        Q(remitente=request.user, destinatario=destinatario) |
        Q(remitente=destinatario, destinatario=request.user)
    )
    
    # Polling incremental: solo mensajes nuevos
    if after_id:
        try:
            queryset = queryset.filter(id__gt=int(after_id)).order_by('fecha')
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'mensaje': 'after_id inválido'}, status=400)
    else:
        queryset = queryset.order_by('-fecha')[:50]
        queryset = sorted(queryset, key=lambda m: m.fecha)
    
    # Marcar como leidos los mensajes recibidos
    MensajeInterno.objects.filter(
        remitente=destinatario,
        destinatario=request.user,
        leido=False
    ).update(leido=True)
    
    resultados = []
    for msg in queryset:
        item = {
            'id': msg.id,
            'remitente_id': msg.remitente.id,
            'remitente_nombre': msg.remitente.get_full_name() or msg.remitente.username,
            'mensaje': msg.mensaje,
            'tipo': msg.tipo,
            'fecha': timezone.localtime(msg.fecha).strftime('%H:%M'),
            'fecha_completa': timezone.localtime(msg.fecha).strftime('%d/%m/%Y %H:%M'),
            'leido': msg.leido,
            'es_mio': msg.remitente.id == request.user.id,
        }
        if msg.tipo == 'audio' and msg.audio:
            item['audio_url'] = msg.audio.url
        resultados.append(item)
    
    return JsonResponse({'status': 'success', 'mensajes': resultados})


@login_required
def api_listar_conversaciones(request):
    """
    API para listar conversaciones activas con badge de no leidos.
    Optimizada: usa 3 queries totales en lugar de 3N (N+1 fix).
    Filtra por empresa: solo usuarios de la misma empresa.
    """
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'mensaje': 'Metodo no permitido'}, status=405)

    user = request.user
    empresa = getattr(user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=400)

    # 1) IDs de usuarios con conversacion (2 queries → 1 con union)
    enviados = MensajeInterno.objects.filter(
        remitente=user
    ).values_list('destinatario_id', flat=True).distinct()
    recibidos = MensajeInterno.objects.filter(
        destinatario=user
    ).values_list('remitente_id', flat=True).distinct()
    user_ids = set(enviados) | set(recibidos)

    if not user_ids:
        return JsonResponse({
            'status': 'success',
            'conversaciones': [],
            'total_no_leidos': 0,
        })

    # 2) Cargar TODOS los usuarios de la misma empresa (1 query, filtro multitenant)
    usuarios_map = {
        u.id: u
        for u in Usuario.objects.filter(id__in=user_ids, empresa=empresa).only(
            'id', 'username', 'first_name', 'last_name', 'rol'
        )
    }

    # 3) Contar no leidos por remitente de una sola vez (1 query)
    no_leidos_qs = (
        MensajeInterno.objects
        .filter(destinatario=user, leido=False, remitente_id__in=user_ids)
        .values('remitente_id')
        .annotate(cnt=Count('id'))
    )
    no_leidos_map = {row['remitente_id']: row['cnt'] for row in no_leidos_qs}

    # 4) Ultimo mensaje por conversacion (1 query con subquery)
    ultimo_fecha_sub = (
        MensajeInterno.objects
        .filter(
            Q(remitente=user, destinatario_id=OuterRef('pk')) |
            Q(destinatario=user, remitente_id=OuterRef('pk'))
        )
        .order_by('-fecha')
        .values('fecha')[:1]
    )

    resultados = []
    total_no_leidos = 0

    # Obtener todos los ultimos mensajes de UNA SOLA VEZ (1 query, no N)
    ultimos_mensajes = {}
    all_msgs = MensajeInterno.objects.filter(
        Q(remitente=user, destinatario_id__in=user_ids) |
        Q(remitente_id__in=user_ids, destinatario=user)
    ).order_by('-fecha').values(
        'remitente_id', 'destinatario_id', 'mensaje', 'tipo', 'fecha'
    )
    for msg in all_msgs:
        uid = msg['destinatario_id'] if msg['remitente_id'] == user.id else msg['remitente_id']
        if uid not in ultimos_mensajes:
            ultimos_mensajes[uid] = msg
        if len(ultimos_mensajes) >= len(user_ids):
            break  # Ya encontro el ultimo de todos los partners

    for uid in user_ids:
        otro = usuarios_map.get(uid)
        if not otro:
            continue

        ultimo = ultimos_mensajes.get(uid)
        if not ultimo:
            continue

        no_leidos = no_leidos_map.get(uid, 0)
        total_no_leidos += no_leidos

        preview = (ultimo['mensaje'] or '')[:40] if ultimo['tipo'] == 'texto' else 'Nota de voz'
        resultados.append({
            'usuario_id': otro.id,
            'nombre': otro.get_full_name() or otro.username,
            'username': otro.username,
            'rol': getattr(otro, 'rol', '') or '',
            'ultimo_mensaje': preview,
            'ultima_fecha': timezone.localtime(ultimo['fecha']).strftime('%H:%M'),
            'ultima_fecha_sort': ultimo['fecha'].isoformat(),
            'no_leidos': no_leidos,
            'es_audio': ultimo['tipo'] == 'audio',
        })

    # Ordenar por fecha mas reciente
    resultados.sort(key=lambda x: x['ultima_fecha_sort'], reverse=True)

    return JsonResponse({
        'status': 'success',
        'conversaciones': resultados,
        'total_no_leidos': total_no_leidos,
    })


@login_required
def api_listar_usuarios(request):
    """API para listar usuarios disponibles para chatear."""
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'mensaje': 'Metodo no permitido'}, status=405)
    
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=400)
    usuarios = Usuario.objects.filter(
        empresa=empresa,
        is_active=True
    ).exclude(id=request.user.id).order_by('first_name', 'last_name')
    
    resultados = [{
        'id': u.id,
        'nombre': u.get_full_name() or u.username,
        'username': u.username,
        'rol': getattr(u, 'rol', '') or '',
    } for u in usuarios]
    
    return JsonResponse({'status': 'success', 'usuarios': resultados})
