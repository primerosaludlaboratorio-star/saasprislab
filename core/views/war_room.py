"""
War Room del Director — Dashboard de Excepciones en Tiempo Real
═══════════════════════════════════════════════════════════════
Solo muestra anomalías que requieren acción inmediata.
Los problemas buscan al Director, no al revés.

4 detectores activos:
  1. Discrepancias de caja > 2%
  2. Valores de pánico sin validar > 15 min
  3. Intentos de acceso fallido a módulos cifrados (Bienestar)
  4. Stock crítico de reactivos (predicción < 3 días)
"""
import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('core')


def _requiere_director(view_func):
    """Decorator: solo Director, Admin, Gerente o Superuser (Ángulo CISO / GUARDIÁN v5.3)."""
    from functools import wraps
    from django.http import HttpResponseForbidden

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('login')
        rol = (getattr(request.user, 'rol', '') or '').strip().upper()
        if not (request.user.is_superuser or rol in ('ADMIN', 'DIRECTOR', 'GERENTE')):
            logger.warning(
                'war_room acceso denegado (CISO): usuario=%s rol=%s ruta=%s ip=%s',
                getattr(request.user, 'username', ''),
                rol or '(vacío)',
                getattr(request, 'path', ''),
                request.META.get('REMOTE_ADDR', ''),
            )
            return HttpResponseForbidden('Acceso restringido al Director.')
        return view_func(request, *args, **kwargs)
    return wrapped


# ── Detectores de anomalías ────────────────────────────────────────────────────

def _model_has_field(model, field_name: str) -> bool:
    """Devuelve True si el modelo realmente expone el campo pedido."""
    try:
        return any(f.name == field_name for f in model._meta.get_fields())
    except Exception:
        return False

def _detectar_discrepancias_caja(empresa) -> list[dict]:
    """Detecta cortes de caja con discrepancia > 2% entre declarado y real."""
    anomalias = []
    try:
        from farmacia.models import CierreTurnoFarmacia
        desde = timezone.now() - timedelta(hours=48)
        cierres = CierreTurnoFarmacia.objects.filter(
            empresa=empresa,
            fecha_cierre__gte=desde,
        ).select_related('usuario_responsable')
        for c in cierres:
            # Comparar totales declarados vs teóricos (efectivo + tarjeta + vales)
            declarado = float((c.efectivo_declarado or 0) + (c.tarjeta_declarado or 0) + (c.vales_declarado or 0))
            sistema = float((c.efectivo_teorico or 0) + (c.tarjeta_teorico or 0) + (c.vales_teorico or 0))
            if sistema > 0:
                pct = abs(declarado - sistema) / sistema * 100
                if pct > 2.0:
                    anomalias.append({
                        'tipo': 'CAJA',
                        'nivel': 'CRITICO' if pct > 5 else 'ADVERTENCIA',
                        'icono': 'fas fa-cash-register',
                        'titulo': f'Discrepancia de caja: {pct:.1f}%',
                        'detalle': (
                            f'Declarado: ${declarado:,.2f} | '
                            f'Sistema: ${sistema:,.2f} | '
                            f'Diferencia: ${abs(declarado - sistema):,.2f}'
                        ),
                        'usuario': str(c.usuario_responsable) if c.usuario_responsable else 'Desconocido',
                        'fecha': timezone.localtime(c.fecha_cierre).strftime('%d/%m %H:%M'),
                        'accion_url': '/finanzas/farmacia/caja/',
                        'accion_texto': 'Revisar corte',
                    })
    except Exception as exc:
        logger.warning(f'War Room - discrepancias_caja: {exc}')
    return anomalias


def _detectar_panico_sin_validar(empresa) -> list[dict]:
    """Detecta valores de pánico ISO 15189 sin validar por más de 15 minutos."""
    anomalias = []
    try:
        from laboratorio.models import Resultado
        limite = timezone.now() - timedelta(minutes=15)
        criticos = Resultado.objects.filter(
            orden__empresa=empresa,
            es_critico=True,
            alerta_critica_enviada=False,
            orden__fecha_creacion__lte=limite,
        ).select_related('orden__paciente', 'parametro_ref').order_by('orden__fecha_creacion')[:20]

        for r in criticos:
            fecha_ref = r.orden.fecha_creacion
            minutos = int((timezone.now() - fecha_ref).total_seconds() / 60) if fecha_ref else 0
            param_nombre = r.parametro_ref.nombre if r.parametro_ref else 'Parametro'
            anomalias.append({
                'tipo': 'PANICO',
                'nivel': 'CRITICO',
                'icono': 'fas fa-exclamation-triangle',
                'titulo': f'Valor critico sin validar — {param_nombre}',
                'detalle': (
                    f'Valor: {r.valor_obtenido or r.valor} | '
                    f'Folio: {getattr(r.orden, "folio_orden", r.orden_id)} | '
                    f'Sin validar: {minutos} min'
                ),
                'usuario': 'Quimico de turno',
                'fecha': timezone.localtime(fecha_ref).strftime('%d/%m %H:%M') if fecha_ref else 'N/A',
                'accion_url': f'/laboratorio/captura/{r.orden_id}/',
                'accion_texto': 'Validar resultado',
            })
    except Exception as exc:
        logger.warning(f'War Room - panico_sin_validar: {exc}')
    return anomalias


def _detectar_accesos_fallidos_bienestar(empresa) -> list[dict]:
    """Detecta intentos de acceso no autorizado a módulos cifrados en las últimas 4h."""
    anomalias = []
    try:
        from seguridad.models import LogAccionSensible
        desde = timezone.now() - timedelta(hours=4)
        logs = LogAccionSensible.objects.filter(
            usuario__empresa=empresa,
            accion__icontains='bienestar',
            fecha_hora__gte=desde,
            exitosa=False,
        ).select_related('usuario').order_by('-fecha_hora')[:10]

        if logs.exists():
            usuarios_set = set()
            for log in logs:
                usuarios_set.add(str(log.usuario))
            anomalias.append({
                'tipo': 'SEGURIDAD',
                'nivel': 'ADVERTENCIA',
                'icono': 'fas fa-shield-alt',
                'titulo': f'{logs.count()} intentos de acceso fallido al modulo Bienestar',
                'detalle': (
                    f'Ultimas 4 horas | '
                    f'Usuarios involucrados: {", ".join(list(usuarios_set)[:3])}'
                ),
                'usuario': 'Sistema de Seguridad',
                'fecha': timezone.localtime(timezone.now()).strftime('%d/%m %H:%M'),
                'accion_url': '/seguridad/auditoria/logs/',
                'accion_texto': 'Ver logs',
            })

        # Detectar multiples intentos fallidos de login general
        from core.models import AuditLog
        logins_fallidos = AuditLog.objects.filter(
            empresa=empresa,
            accion__icontains='login_fallido',
            fecha_cierta__gte=timezone.now() - timedelta(hours=1),
        ).count()
        if logins_fallidos > 10:
            anomalias.append({
                'tipo': 'SEGURIDAD',
                'nivel': 'CRITICO',
                'icono': 'fas fa-user-slash',
                'titulo': f'{logins_fallidos} intentos de login fallido en la ultima hora',
                'detalle': 'Posible ataque de fuerza bruta. Revisar IPs de origen.',
                'usuario': 'CISO Automatico',
                'fecha': timezone.localtime(timezone.now()).strftime('%d/%m %H:%M'),
                'accion_url': '/seguridad/sesiones/',
                'accion_texto': 'Ver sesiones',
            })
    except Exception as exc:
        logger.warning(f'War Room - accesos_fallidos: {exc}')
    return anomalias


def _detectar_stock_critico(empresa) -> list[dict]:
    """Detecta reactivos/productos con stock para menos de 3 días según predicción."""
    anomalias = []
    try:
        from core.services.prediccion_stock import predecir_agotamiento_critico
        criticos = predecir_agotamiento_critico(empresa, dias_umbral=3)
        for item in criticos[:10]:
            dias = item.get('dias_restantes', 0)
            nivel = 'CRITICO' if dias <= 1 else 'ADVERTENCIA'
            anomalias.append({
                'tipo': 'STOCK',
                'nivel': nivel,
                'icono': 'fas fa-flask',
                'titulo': f'Stock critico: {item["producto_nombre"]}',
                'detalle': (
                    f'Stock actual: {item["stock_actual"]} unidades | '
                    f'Consumo diario: {item["consumo_diario"]:.1f} | '
                    f'Se agota en: {"HOY" if dias <= 0 else f"{dias} dias"}'
                ),
                'usuario': 'IA de Inventario',
                'fecha': timezone.localtime(timezone.now()).strftime('%d/%m %H:%M'),
                'accion_url': '/inventario/',
                'accion_texto': 'Ver inventario',
            })
    except Exception as exc:
        logger.warning(f'War Room - stock_critico: {exc}')
    return anomalias


def _detectar_anomalias_silos(empresa) -> list[dict]:
    """Detecta lotes próximos a vencer (≤7 días) y quiebres de stock en los 3 silos."""
    anomalias = []
    hoy = timezone.now().date()
    limite = hoy + timedelta(days=7)
    try:
        from inventario.models import (
            LoteReactivoLab, LoteInsumoConsultorio, LoteInsumoGeneral
        )
        # has_caducidad indica si el modelo maneja fecha_caducidad (General no la tiene)
        silos = [
            (LoteReactivoLab,      'reactivo__nombre', 'LAB',         '/inventario/lab/lotes/'),
            (LoteInsumoConsultorio,'insumo__nombre',   'CONSULTORIO', '/inventario/consultorio/lotes/'),
            (LoteInsumoGeneral,    'insumo__nombre',   'GENERAL',     '/inventario/generales/lotes/'),
        ]
        for Model, nombre_field, silo_label, url in silos:
            if not _model_has_field(Model, 'fecha_caducidad'):
                continue

            # Lotes próximos a vencer
            por_vencer = Model.objects.filter(
                empresa=empresa,
                cantidad_actual__gt=0,
                fecha_caducidad__lte=limite,
                fecha_caducidad__gte=hoy,
            ).count()
            if por_vencer:
                anomalias.append({
                    'tipo': 'SILO',
                    'nivel': 'ADVERTENCIA',
                    'icono': 'fas fa-hourglass-half',
                    'titulo': f'Silo {silo_label}: {por_vencer} lote(s) vencen en ≤7 días',
                    'detalle': 'Revisar FEFO y tomar decisión de uso o descarte.',
                    'usuario': 'Monitor Silos',
                    'fecha': timezone.localtime(timezone.now()).strftime('%d/%m %H:%M'),
                    'accion_url': url,
                    'accion_texto': 'Ver lotes',
                })
            # Lotes ya vencidos con stock
            vencidos = Model.objects.filter(
                empresa=empresa,
                cantidad_actual__gt=0,
                fecha_caducidad__lt=hoy,
            ).count()
            if vencidos:
                anomalias.append({
                    'tipo': 'SILO',
                    'nivel': 'CRITICO',
                    'icono': 'fas fa-skull-crossbones',
                    'titulo': f'Silo {silo_label}: {vencidos} lote(s) VENCIDOS con stock activo',
                    'detalle': 'Lotes caducados no deben utilizarse. Dar de baja inmediatamente.',
                    'usuario': 'Monitor Silos',
                    'fecha': timezone.localtime(timezone.now()).strftime('%d/%m %H:%M'),
                    'accion_url': url,
                    'accion_texto': 'Atender ahora',
                })
    except Exception as exc:
        logger.warning(f'War Room - anomalias_silos: {exc}')
    return anomalias


def _detectar_cmms_criticos(empresa) -> list[dict]:
    """Detecta equipos con tickets críticos y certificados vencidos."""
    anomalias = []
    try:
        from mantenimiento.models import TicketMantenimientoCMMS, CertificadoMetrologia
        hoy = timezone.now().date()

        # Equipos con tickets en niveles de escalamiento que requieren intervención
        niveles_criticos = ('DIRECTOR', 'PROVEEDOR')
        tickets_criticos = TicketMantenimientoCMMS.objects.filter(
            empresa=empresa,
            nivel_escalamiento_actual__in=niveles_criticos,
            estado__in=('ABIERTO', 'EN_PROCESO'),
        ).count()

        if tickets_criticos:
            anomalias.append({
                'tipo': 'CMMS',
                'nivel': 'CRITICO',
                'icono': 'fas fa-tools',
                'titulo': f'CMMS: {tickets_criticos} ticket(s) CRÍTICO(S) sin resolver',
                'detalle': 'Equipos con falla crítica pueden comprometer la operación.',
                'usuario': 'Monitor CMMS',
                'fecha': timezone.localtime(timezone.now()).strftime('%d/%m %H:%M'),
                'accion_url': '/mantenimiento/tickets/',
                'accion_texto': 'Ver tickets',
            })

        # Certificados vencidos
        certs_vencidos = CertificadoMetrologia.objects.filter(
            empresa=empresa,
            estado='VENCIDO',
        ).count()
        if certs_vencidos:
            anomalias.append({
                'tipo': 'CMMS',
                'nivel': 'CRITICO',
                'icono': 'fas fa-certificate',
                'titulo': f'Metrología: {certs_vencidos} certificado(s) VENCIDO(S)',
                'detalle': 'Equipos sin certificado vigente no cumplen ISO 15189 §6.4.3.',
                'usuario': 'Monitor Metrología',
                'fecha': timezone.localtime(timezone.now()).strftime('%d/%m %H:%M'),
                'accion_url': '/mantenimiento/metrologia/',
                'accion_texto': 'Ver certificados',
            })

        # Sensores IoT fuera de rango en las últimas 4h
        desde = timezone.now() - timedelta(hours=4)
        from mantenimiento.models import LecturaSensorIoT
        alertas_iot = LecturaSensorIoT.objects.filter(
            empresa=empresa,
            fuera_de_rango=True,
            timestamp__gte=desde,
        ).count()
        if alertas_iot:
            anomalias.append({
                'tipo': 'CMMS',
                'nivel': 'CRITICO',
                'icono': 'fas fa-thermometer-full',
                'titulo': f'IoT: {alertas_iot} alerta(s) de temperatura/humedad (4h)',
                'detalle': 'Revisar condiciones de almacenamiento. Posible pérdida de reactivos.',
                'usuario': 'Monitor IoT',
                'fecha': timezone.localtime(timezone.now()).strftime('%d/%m %H:%M'),
                'accion_url': '/mantenimiento/sensores/dashboard/',
                'accion_texto': 'Ver sensores',
            })
    except Exception as exc:
        logger.warning(f'War Room - cmms_criticos: {exc}')
    return anomalias


def _detectar_burnout_nom035(empresa) -> list[dict]:
    """Detecta señales de riesgo de burnout del staff (NOM-035)."""
    anomalias = []
    try:
        from bienestar.models import EvaluacionNOM035, DiarioEmocionalStaff
        desde = timezone.now() - timedelta(days=7)

        evaluaciones_criticas = EvaluacionNOM035.objects.filter(
            usuario__empresa=empresa,
            riesgo_factor__in=('ALTO', 'MUY_ALTO'),
            fecha__gte=desde,
        ).count()
        if evaluaciones_criticas:
            anomalias.append({
                'tipo': 'BIENESTAR',
                'nivel': 'ADVERTENCIA',
                'icono': 'fas fa-heart-broken',
                'titulo': f'NOM-035: {evaluaciones_criticas} colaborador(es) en riesgo ALTO',
                'detalle': 'Factores de riesgo psicosocial detectados en la última semana.',
                'usuario': 'Monitor NOM-035',
                'fecha': timezone.localtime(timezone.now()).strftime('%d/%m %H:%M'),
                'accion_url': '/bienestar/',
                'accion_texto': 'Ver bienestar',
            })
    except Exception as exc:
        logger.debug(f'War Room - burnout (no crítico): {exc}')
    return anomalias


def _obtener_flujo_caja(empresa) -> dict:
    """Calcula ingresos vs gastos de hoy para el War Room."""
    from django.db.models import Sum
    hoy = timezone.now().date()
    resultado = {'ingresos': 0.0, 'gastos_compras': 0.0, 'saldo_neto': 0.0}
    try:
        from core.models import Venta
        ventas = Venta.objects.filter(
            empresa=empresa, fecha__date=hoy, estado='COMPLETADA'
        ).aggregate(total=Sum('total'))
        resultado['ingresos'] = float(ventas['total'] or 0)
    except Exception:
        pass
    try:
        from inventario.models import OrdenDeCompra
        gastos = OrdenDeCompra.objects.filter(
            empresa=empresa,
            estado__in=('COMPLETADA', 'PARCIALMENTE_RECIBIDA'),
            fecha_aprobacion__date=hoy,
        ).aggregate(total=Sum('total_estimado'))
        resultado['gastos_compras'] = float(gastos['total'] or 0)
    except Exception:
        pass
    resultado['saldo_neto'] = resultado['ingresos'] - resultado['gastos_compras']
    return resultado


def _obtener_metricas_rapidas(empresa) -> dict:
    """KPIs del día para el header del War Room."""
    from django.db.models import Sum, Count
    hoy = timezone.now().date()
    metricas = {}
    try:
        from core.models import OrdenDeServicio
        qs = OrdenDeServicio.objects.filter(empresa=empresa, fecha_creacion__date=hoy)
        metricas['ordenes_hoy'] = qs.count()
        metricas['ordenes_pendientes'] = qs.filter(estado__in=['PENDIENTE_PAGO', 'EN_PROCESO']).count()
        metricas['ordenes_completadas'] = qs.filter(estado__in=['RESULTADOS_LISTOS', 'ENTREGADO']).count()
    except Exception:
        logger.error('[WarRoom] Error obteniendo métricas de órdenes', exc_info=True)
        metricas['ordenes_hoy'] = 0
        metricas['ordenes_pendientes'] = 0
        metricas['ordenes_completadas'] = 0

    try:
        from core.models import Venta
        ventas = Venta.objects.filter(empresa=empresa, fecha__date=hoy, estado='COMPLETADA')
        metricas['ingresos_hoy'] = float(ventas.aggregate(t=Sum('total'))['t'] or 0)
        metricas['ventas_hoy'] = ventas.count()
    except Exception:
        logger.error('[WarRoom] Error obteniendo métricas de ventas', exc_info=True)
        metricas['ingresos_hoy'] = 0
        metricas['ventas_hoy'] = 0

    try:
        from laboratorio.models import Resultado
        metricas['criticos_activos'] = Resultado.objects.filter(
            orden__empresa=empresa, es_critico=True, alerta_critica_enviada=False
        ).count()
    except Exception:
        logger.error('[WarRoom] Error obteniendo críticos activos', exc_info=True)
        metricas['criticos_activos'] = 0

    try:
        from core.services.prediccion_stock import predecir_agotamiento_critico
        metricas['stocks_criticos'] = len(predecir_agotamiento_critico(empresa, dias_umbral=3))
    except Exception:
        logger.error('[WarRoom] Error predicción stock', exc_info=True)
        metricas['stocks_criticos'] = 0

    return metricas


def _obtener_tendencia_bienestar(empresa) -> dict:
    """
    Retorna datos para la gráfica NOM-035 burnout del staff.
    Agrupa DiarioEmocional por semana (últimas 8 semanas) y cuenta niveles de riesgo.
    Los datos son anonimizados: solo conteos, nunca nombres.
    """
    resultado = {
        'labels': [],
        'verde': [],
        'amarillo': [],
        'rojo': [],
        'total_alto_riesgo': 0,
        'disponible': False,
    }
    try:
        from bienestar.models import DiarioEmocional
        from django.db.models import Count
        from django.db.models.functions import TruncWeek
        import json as _json

        desde = timezone.now() - timedelta(weeks=8)
        entradas = (
            DiarioEmocional.objects
            .filter(fecha_creacion__gte=desde)
            .annotate(semana=TruncWeek('fecha_creacion'))
            .values('semana', 'nivel_riesgo')
            .annotate(total=Count('id'))
            .order_by('semana')
        )

        semanas_dict = {}
        for e in entradas:
            semana_key = e['semana'].strftime('%d/%m') if e['semana'] else '??'
            if semana_key not in semanas_dict:
                semanas_dict[semana_key] = {'VERDE': 0, 'AMARILLO': 0, 'ROJO': 0}
            nivel = e['nivel_riesgo'] or 'VERDE'
            if nivel.startswith('ROJO'):
                semanas_dict[semana_key]['ROJO'] += e['total']
            elif nivel == 'AMARILLO':
                semanas_dict[semana_key]['AMARILLO'] += e['total']
            else:
                semanas_dict[semana_key]['VERDE'] += e['total']

        for semana, counts in sorted(semanas_dict.items()):
            resultado['labels'].append(semana)
            resultado['verde'].append(counts['VERDE'])
            resultado['amarillo'].append(counts['AMARILLO'])
            resultado['rojo'].append(counts['ROJO'])
            resultado['total_alto_riesgo'] += counts['ROJO']

        if resultado['labels']:
            resultado['disponible'] = True

    except Exception as e:
        logger.warning('war_room: _obtener_tendencia_bienestar error: %s', e)

    return resultado


def _obtener_metricas_marketing(empresa) -> dict:
    """
    Métricas de Marketing para el War Room:
    - Campañas activas
    - Solicitudes CFDI pendientes
    - Pacientes potencialmente inactivos (cálculo rápido sin API externa)
    """
    resultado = {
        'disponible': False,
        'campanas_activas': 0,
        'cfdi_pendientes': 0,
        'pacientes_inactivos_estimado': 0,
    }
    try:
        from marketing.models import CampanaMarketing
        resultado['campanas_activas'] = CampanaMarketing.objects.filter(
            empresa=empresa, activa=True
        ).count()
        resultado['disponible'] = True
    except Exception as e:
        logger.debug('war_room _metricas_marketing CampanaMarketing: %s', e)

    try:
        from core.models import FacturaSAT
        resultado['cfdi_pendientes'] = FacturaSAT.objects.filter(
            empresa=empresa, estatus=FacturaSAT.ESTATUS_BORRADOR
        ).count()
    except Exception as e:
        logger.debug('war_room _metricas_marketing FacturaSAT: %s', e)

    try:
        # Estimado rápido: pacientes sin órdenes en últimos 6 meses
        from core.models import Paciente, OrdenDeServicio
        hace_6m = timezone.now() - timedelta(days=180)
        total_pac = Paciente.objects.filter(empresa=empresa, activo=True).count()
        con_actividad = OrdenDeServicio.objects.filter(
            empresa=empresa, fecha_creacion__gte=hace_6m
        ).values('paciente_id').distinct().count()
        resultado['pacientes_inactivos_estimado'] = max(0, total_pac - con_actividad)
    except Exception as e:
        logger.debug('war_room _metricas_marketing pacientes inactivos: %s', e)

    return resultado


# ── Vistas ─────────────────────────────────────────────────────────────────────

@login_required
@_requiere_director
def war_room(request):
    """Dashboard de excepciones del Director."""
    from core.services.feature_flags import flag_activo
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.shortcuts import redirect
        return redirect('dashboard')

    if not flag_activo('WAR_ROOM_ACTIVO', empresa):
        from django.shortcuts import redirect
        return redirect('dashboard')

    anomalias = []
    anomalias += _detectar_panico_sin_validar(empresa)
    anomalias += _detectar_discrepancias_caja(empresa)
    anomalias += _detectar_accesos_fallidos_bienestar(empresa)
    anomalias += _detectar_stock_critico(empresa)
    anomalias += _detectar_anomalias_silos(empresa)
    anomalias += _detectar_cmms_criticos(empresa)
    anomalias += _detectar_burnout_nom035(empresa)

    # Ordenar: CRITICO primero
    orden_nivel = {'CRITICO': 0, 'ADVERTENCIA': 1, 'INFO': 2}
    anomalias.sort(key=lambda x: orden_nivel.get(x.get('nivel', 'INFO'), 2))

    metricas = _obtener_metricas_rapidas(empresa)
    flujo_caja = _obtener_flujo_caja(empresa)

    # Discrepancias no resueltas
    discrepancias_pendientes = 0
    try:
        from inventario.models import NotificacionDiscrepancia
        discrepancias_pendientes = NotificacionDiscrepancia.objects.filter(
            empresa=empresa, resuelta=False
        ).count()
    except Exception:
        pass

    tendencia_bienestar = _obtener_tendencia_bienestar(empresa)
    metricas_marketing = _obtener_metricas_marketing(empresa)

    return render(request, 'core/director/war_room.html', {
        'anomalias': anomalias,
        'total_criticos': sum(1 for a in anomalias if a['nivel'] == 'CRITICO'),
        'total_advertencias': sum(1 for a in anomalias if a['nivel'] == 'ADVERTENCIA'),
        'metricas': metricas,
        'flujo_caja': flujo_caja,
        'tendencia_bienestar': tendencia_bienestar,
        'discrepancias_pendientes': discrepancias_pendientes,
        'metricas_marketing': metricas_marketing,
        'ultima_actualizacion': timezone.localtime(timezone.now()).strftime('%H:%M:%S'),
    })


@login_required
@_requiere_director
@require_http_methods(['GET'])
def api_war_room_anomalias(request):
    """API JSON para actualización automática del War Room cada 60 segundos."""
    from core.services.feature_flags import flag_activo
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
    if not flag_activo('WAR_ROOM_ACTIVO', empresa):
        return JsonResponse({'error': 'War Room desactivado'}, status=403)

    anomalias = []
    anomalias += _detectar_panico_sin_validar(empresa)
    anomalias += _detectar_discrepancias_caja(empresa)
    anomalias += _detectar_accesos_fallidos_bienestar(empresa)
    anomalias += _detectar_stock_critico(empresa)
    anomalias += _detectar_anomalias_silos(empresa)
    anomalias += _detectar_cmms_criticos(empresa)
    anomalias += _detectar_burnout_nom035(empresa)

    orden_nivel = {'CRITICO': 0, 'ADVERTENCIA': 1, 'INFO': 2}
    anomalias.sort(key=lambda x: orden_nivel.get(x.get('nivel', 'INFO'), 2))
    metricas = _obtener_metricas_rapidas(empresa)
    flujo_caja = _obtener_flujo_caja(empresa)
    metricas_marketing = _obtener_metricas_marketing(empresa)

    return JsonResponse({
        'anomalias': anomalias,
        'total_criticos': sum(1 for a in anomalias if a['nivel'] == 'CRITICO'),
        'total_advertencias': sum(1 for a in anomalias if a['nivel'] == 'ADVERTENCIA'),
        'metricas': metricas,
        'flujo_caja': flujo_caja,
        'metricas_marketing': metricas_marketing,
        'timestamp': timezone.localtime(timezone.now()).strftime('%H:%M:%S'),
    })
