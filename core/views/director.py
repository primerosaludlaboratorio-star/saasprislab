"""
Vista del Dashboard de Director - Control de Mando Ejecutivo.
Muestra métricas en tiempo real: ventas, reactivos, pacientes, alertas críticas.
"""
from decimal import Decimal
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from django.db.models import DecimalField
from django.utils import timezone

from core.models import (
    Empresa, Sucursal, Venta, Pago, Producto, Lote, 
    OrdenDeServicio, Paciente, BackupRegistro, BuzonQuejas, Usuario,
    SolicitudAutorizacion, IncidenciaOperativa
)
from core.models import EvaluacionDesempeno


@login_required
def dashboard_director(request):
    """Dashboard ejecutivo para la dirección con métricas en tiempo real."""
    try:
        # Control de acceso: solo directivos, admin o gerencia
        user = request.user
        if not (user.is_superuser or user.is_staff
                or (getattr(user, 'rol', '') or '').upper().strip() in ('ADMIN', 'ADMINISTRADOR', 'GERENTE', 'DIRECTOR')
                or user.groups.filter(name__in=['GERENCIA', 'GERENCIA_OPERATIVA', 'DIRECTOR']).exists()):
            from django.contrib import messages
            messages.warning(request, 'No tienes permisos para acceder al Dashboard de Dirección.')
            return redirect('home')

        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            from django.contrib import messages
            messages.error(request, 'Usuario no tiene empresa asignada.')
            return redirect('login')
        # Fecha actual
        hoy = timezone.now().date()
        inicio_dia = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
        fin_dia = timezone.make_aware(datetime.combine(hoy, datetime.max.time()))

        # 1. VENTAS DEL DÍA (Sin redondeos)
        ventas_hoy = Venta.objects.filter(
            empresa=empresa,
            fecha__range=(inicio_dia, fin_dia),
            estado='COMPLETADA'
        )
        total_ventas_hoy = ventas_hoy.aggregate(
            total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')

        ventas_efectivo = Pago.objects.filter(
            venta__empresa=empresa,
            venta__fecha__range=(inicio_dia, fin_dia),
            venta__estado='COMPLETADA',
            metodo='EFECTIVO'
        ).aggregate(
            total=Coalesce(Sum('monto'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')

        # 2. PORCENTAJE DE OCUPACIÓN DE SUCURSALES (optimizado: batch queries)
        sucursales = Sucursal.objects.filter(empresa=empresa, activa=True)
        total_usuarios_empresa = empresa.usuarios.filter(is_active=True).count()

        # Batch: contar usuarios por sucursal
        from django.db.models import Count as DjCount
        sucursales_con_usuarios = sucursales.annotate(
            usuarios_activos_count=DjCount('usuarios', filter=Q(usuarios__is_active=True))
        )
        # Batch: ventas por sucursal hoy
        ventas_por_sucursal = dict(
            Venta.objects.filter(
                empresa=empresa,
                fecha__range=(inicio_dia, fin_dia),
                estado='COMPLETADA'
            ).values('sucursal_id').annotate(
                total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField())
            ).values_list('sucursal_id', 'total')
        )

        ocupacion_sucursales = []
        for sucursal in sucursales_con_usuarios:
            usuarios_sucursal = sucursal.usuarios_activos_count
            porcentaje_ocupacion = (usuarios_sucursal / total_usuarios_empresa * 100) if total_usuarios_empresa > 0 else 0
            ventas_sucursal = ventas_por_sucursal.get(sucursal.id, Decimal('0.00'))

            ocupacion_sucursales.append({
                'sucursal': sucursal,
                'usuarios_activos': usuarios_sucursal,
                'porcentaje_ocupacion': round(porcentaje_ocupacion, 2),
                'ventas_hoy': ventas_sucursal,
                'estado': 'ocupada' if porcentaje_ocupacion > 50 else 'disponible'
            })

        # 3. ALERTAS DE VALORES CRÍTICOS (Laboratorio)
        try:
            from core.models import ResultadoParametro
            alertas_criticas_count = ResultadoParametro.objects.filter(
                orden__empresa=empresa,
                es_critico=True,
            ).count()
        except Exception:
            alertas_criticas_count = 0

        # 4. ESTATUS DE REACTIVOS PRÓXIMOS A VENCER (una query en lugar de N+1)
        fecha_limite = hoy + timedelta(days=30)
        reactivos_vencer = []
        lotes_proximos_qs = Lote.objects.filter(
            producto__empresa=empresa,
            cantidad__gt=0,
            fecha_caducidad__lte=fecha_limite,
            fecha_caducidad__gte=hoy
        ).select_related('producto').order_by('fecha_caducidad')[:200]

        productos_vistos = set()
        for lote in lotes_proximos_qs:
            if lote.producto_id in productos_vistos:
                continue
            productos_vistos.add(lote.producto_id)
            dias_restantes = (lote.fecha_caducidad - hoy).days
            reactivos_vencer.append({
                    'producto': lote.producto.nombre,
                    'lote': lote.numero_lote,
                    'fecha_caducidad': lote.fecha_caducidad,
                    'dias_restantes': dias_restantes,
                    'cantidad': lote.cantidad,
                    'es_critico': dias_restantes <= 7,
                    'es_atencion': dias_restantes <= 14 and dias_restantes > 7
                })

        # Ordenar por días restantes (más críticos primero)
        reactivos_vencer.sort(key=lambda x: x['dias_restantes'])

        # 5. VOLUMEN DE PACIENTES POR SUCURSAL (optimizado: batch queries)
        pac_por_sucursal = dict(
            Paciente.objects.filter(empresa=empresa)
            .values('sucursal_id')
            .annotate(total=Count('id'))
            .values_list('sucursal_id', 'total')
        )
        ord_por_sucursal = dict(
            OrdenDeServicio.objects.filter(empresa=empresa, fecha_creacion__date=hoy)
            .values('sucursal_id')
            .annotate(total=Count('id'))
            .values_list('sucursal_id', 'total')
        )
        volumen_pacientes = []
        for sucursal in sucursales:
            volumen_pacientes.append({
                'sucursal': sucursal,
                'total_pacientes': pac_por_sucursal.get(sucursal.id, 0),
                'ordenes_hoy': ord_por_sucursal.get(sucursal.id, 0),
            })

        # 6. ESTADÍSTICAS GENERALES
        total_pacientes = Paciente.objects.filter(empresa=empresa).count()
        total_ordenes_hoy = OrdenDeServicio.objects.filter(
            empresa=empresa,
            fecha_creacion__date=hoy
        ).count()

        # 7. NOTIFICACIONES DE BACKUP NOCTURNO
        backups_recientes = BackupRegistro.objects.filter(
            empresa=empresa,
            fecha_backup__date__gte=hoy - timedelta(days=7)  # Últimos 7 días
        ).order_by('-fecha_backup')[:10]

        ultimo_backup = BackupRegistro.objects.filter(
            empresa=empresa,
            estado='COMPLETADO',
            fecha_backup__date__gte=hoy - timedelta(days=30)
        ).order_by('-fecha_backup').first()

        backup_ultima_noche = BackupRegistro.objects.filter(
            empresa=empresa,
            fecha_backup__date=hoy - timedelta(days=1),
            estado='COMPLETADO'
        ).first()

        # ==============================================================================
        # NUEVAS SECCIONES: CRECIMIENTO Y CONTROL GERENCIAL
        # ==============================================================================

        # RADAR DE PROBLEMAS
        quejas_hoy = BuzonQuejas.objects.filter(
            empresa=empresa,
            fecha_creacion__date=hoy
        ).count()

        # Órdenes retrasadas (ordenes con fecha de entrega pasada y no entregadas)
        ordenes_retrasadas = OrdenDeServicio.objects.filter(
            empresa=empresa,
            estado__in=['PAGADO', 'EN_PROCESO', 'RESULTADOS_LISTOS'],
            hora_entrega_prometida__lt=timezone.now()
        ).count()

        # Empleado con peor calificación esta semana
        inicio_semana = hoy - timedelta(days=7)
        evaluaciones_semana = EvaluacionDesempeno.objects.filter(
            empleado__empresa=empresa,
            fecha__gte=inicio_semana
        ).select_related('empleado')

        peor_empleado = None
        if evaluaciones_semana.exists():
            peor_eval = evaluaciones_semana.order_by('promedio_competencias').first()
            if peor_eval:
                empleado = peor_eval.empleado
                nombre = getattr(empleado, 'nombre_completo', None) or (
                    (empleado.usuario.get_full_name() or empleado.usuario.username) if empleado.usuario else 'N/A'
                )
                peor_empleado = {
                    'nombre': nombre or 'N/A',
                    'calificacion': peor_eval.promedio_competencias,
                    'periodo': peor_eval.periodo
                }

        # Buzón de la Verdad - Estadísticas
        quejas_pendientes = BuzonQuejas.objects.filter(
            empresa=empresa,
            estado='PENDIENTE'
        ).count()

        quejas_por_tipo = {
            'QUEJA': BuzonQuejas.objects.filter(empresa=empresa, tipo='QUEJA').count(),
            'SUGERENCIA': BuzonQuejas.objects.filter(empresa=empresa, tipo='SUGERENCIA').count(),
            'FELICITACION': BuzonQuejas.objects.filter(empresa=empresa, tipo='FELICITACION').count(),
        }

        # Autorizaciones pendientes (select_related para evitar N+1 en template)
        autorizaciones_pendientes = SolicitudAutorizacion.objects.filter(
            usuario_solicita__empresa=empresa,
            estado='PENDIENTE'
        ).select_related('usuario_solicita').order_by('-fecha_solicitud')[:50]

        # Incidencias de hoy (IncidenciaOperativa tiene campo empresa y fecha_hora)
        incidencias_hoy_count = IncidenciaOperativa.objects.filter(
            empresa=empresa,
            fecha_hora__date=hoy
        ).count()

        return render(request, 'core/dashboard_director.html', {
            'empresa': empresa,
            'fecha_hoy': hoy.strftime('%d/%m/%Y'),

            # Ventas
            'total_ventas_hoy': total_ventas_hoy,
            'ventas_efectivo': ventas_efectivo,
            'cantidad_ventas': ventas_hoy.count(),

            # Sucursales
            'ocupacion_sucursales': ocupacion_sucursales,
            'total_sucursales': sucursales.count(),

            # Alertas
            'alertas_criticas_count': alertas_criticas_count,
            'reactivos_vencer': reactivos_vencer,
            'cantidad_reactivos_vencer': len(reactivos_vencer),
            'reactivos_criticos': [r for r in reactivos_vencer if r['es_critico']],

            # Pacientes
            'volumen_pacientes': volumen_pacientes,
            'total_pacientes': total_pacientes,
            'total_ordenes_hoy': total_ordenes_hoy,

            # Backups
            'backups_recientes': backups_recientes,
            'ultimo_backup': ultimo_backup,
            'backup_ultima_noche': backup_ultima_noche,

            # Radar de Problemas
            'quejas_hoy': quejas_hoy,
            'ordenes_retrasadas': ordenes_retrasadas,
            'peor_empleado': peor_empleado,

            # Buzón de la Verdad
            'quejas_pendientes': quejas_pendientes,
            'quejas_por_tipo': quejas_por_tipo,

            # Autorizaciones
            'autorizaciones_pendientes': autorizaciones_pendientes,
            'autorizaciones_pendientes_count': autorizaciones_pendientes.count(),

            # Incidencias
            'incidencias_hoy_count': incidencias_hoy_count,
        })
    except Exception as exc:
        from django.contrib import messages
        import logging
        logging.getLogger('core.director').error(
            'dashboard_director: error inesperado, degradando a login: %s',
            exc,
            exc_info=True,
        )
        messages.error(
            request,
            'El panel de dirección tuvo un problema temporal. Vuelve a iniciar sesión.'
        )
        return redirect('login')


# ─── MÓDULO GESTIÓN DE ANALIZADORES ─────────────────────────────────────────

def _require_director(request):
    """Devuelve True si el usuario tiene acceso de dirección."""
    user = request.user
    return (user.is_superuser or user.is_staff
            or (getattr(user, 'rol', '') or '').upper().strip() in ('ADMIN', 'ADMINISTRADOR', 'GERENTE', 'DIRECTOR', 'QUIMICO', 'LABORATORIO')
            or user.groups.filter(name__in=['GERENCIA', 'GERENCIA_OPERATIVA', 'LABORATORIO']).exists())


@login_required
def director_analizadores(request):
    """Vista de gestión de analizadores de laboratorio."""
    from django.http import HttpResponseForbidden
    if not _require_director(request):
        return HttpResponseForbidden('Sin acceso.')

    from laboratorio.models import Equipo, CodigoParametroEquipo

    # Equipo pertenece al catálogo técnico global de la instalación.
    # El modelo laboratorio.Equipo no tiene FK empresa; el aislamiento aquí es RBAC.
    equipo_qs = Equipo.objects.all()
    equipos = equipo_qs.prefetch_related('mapeos_codigos__parametro')
    mapeos_qs = CodigoParametroEquipo.objects.select_related('equipo', 'parametro').order_by('equipo__nombre')
    mapeos = mapeos_qs[:200]

    equipos_activos = equipos.filter(activo=True).count()
    equipos_interfazados = equipos.exclude(protocolo='MANUAL').filter(activo=True).count()
    total_mapeos = mapeos_qs.count()

    return render(request, 'core/director_analizadores.html', {
        'equipos': equipos,
        'mapeos': mapeos,
        'equipos_activos': equipos_activos,
        'equipos_interfazados': equipos_interfazados,
        'total_mapeos': total_mapeos,
    })


@login_required
def director_analizadores_crear(request):
    """Crear un nuevo equipo de laboratorio."""
    from django.http import HttpResponseForbidden
    from django.contrib import messages
    if not _require_director(request):
        return HttpResponseForbidden('Sin acceso.')
    if request.method != 'POST':
        return redirect('director_analizadores')

    from laboratorio.models import Equipo
    nombre = request.POST.get('nombre', '').strip()
    if not nombre:
        messages.error(request, 'El nombre del equipo es obligatorio.')
        return redirect('director_analizadores')

    Equipo.objects.create(
        nombre=nombre,
        marca=request.POST.get('marca', '').strip() or None,
        ip_address=request.POST.get('ip_address', '').strip() or None,
        puerto=request.POST.get('puerto') or None,
        protocolo=request.POST.get('protocolo', 'MANUAL').strip(),
        notas=request.POST.get('notas', '').strip() or None,
        activo=True,
    )
    messages.success(request, f'Equipo "{nombre}" registrado correctamente.')
    return redirect('director_analizadores')


@login_required
def director_analizadores_toggle(request, equipo_id):
    """Activar/desactivar un equipo."""
    from django.http import JsonResponse, HttpResponseForbidden
    if not _require_director(request):
        return HttpResponseForbidden('Sin acceso.')
    from laboratorio.models import Equipo
    from django.shortcuts import get_object_or_404
    equipo = get_object_or_404(Equipo, id=equipo_id)
    equipo.activo = not equipo.activo
    equipo.save(update_fields=['activo'])
    return JsonResponse({'ok': True, 'activo': equipo.activo})


@login_required
def director_analizadores_mapeos(request, equipo_id):
    """Vista parcial (HTMX/AJAX) con los mapeos de un equipo."""
    from django.http import HttpResponseForbidden
    from django.shortcuts import get_object_or_404
    if not _require_director(request):
        return HttpResponseForbidden('Sin acceso.')

    from laboratorio.models import Equipo, CodigoParametroEquipo, Parametro
    equipo = get_object_or_404(Equipo, id=equipo_id)
    mapeos = CodigoParametroEquipo.objects.filter(equipo=equipo).select_related('parametro')
    parametros = Parametro.objects.order_by('estudio__nombre', 'orden_impresion', 'nombre')[:300]

    return render(request, 'core/director_analizadores_mapeos.html', {
        'equipo': equipo,
        'mapeos': mapeos,
        'parametros': parametros,
    })


@login_required
def director_analizadores_probar_conexion(request):
    """Prueba conexión TCP/IP con un equipo."""
    from django.http import JsonResponse, HttpResponseForbidden
    import socket
    import json
    if not _require_director(request):
        return HttpResponseForbidden('Sin acceso.')
    try:
        data = json.loads(request.body)
        ip = data.get('ip', '')
        puerto = int(data.get('puerto', 9100))
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((ip, puerto))
        sock.close()
        return JsonResponse({'ok': result == 0, 'mensaje': 'Conectado' if result == 0 else 'Sin respuesta'})
    except Exception as e:
        return JsonResponse({'ok': False, 'mensaje': str(e)})


@login_required
def director_analizadores_eliminar_mapeo(request, mapeo_id):
    """Eliminar un mapeo de código."""
    from django.http import JsonResponse, HttpResponseForbidden
    from django.shortcuts import get_object_or_404
    if not _require_director(request):
        return HttpResponseForbidden('Sin acceso.')
    from laboratorio.models import CodigoParametroEquipo
    mapeo = get_object_or_404(CodigoParametroEquipo, id=mapeo_id)
    mapeo.delete()
    return JsonResponse({'ok': True})
