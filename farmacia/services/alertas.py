"""
PRISLAB V5 - SENTINEL V4 Integration: Alertas de Farmacia
Push Notifications para stock crítico y auditoría de precios staff
"""

import logging
from datetime import date, timedelta
from django.conf import settings
from django.db.models import F

logger = logging.getLogger(__name__)

# Umbrales de caducidad configurables (días)
_DIAS_CRITICO = getattr(settings, 'FARMACIA_DIAS_CADUCIDAD_CRITICO', 30)
_DIAS_ALERTA = getattr(settings, 'FARMACIA_DIAS_CADUCIDAD_ALERTA', 90)


def verificar_stock_critico_y_notificar():
    """
    Verifica productos con stock crítico y envía notificaciones push al Director.
    Se puede ejecutar como tarea programada (cron/celery) o manualmente.
    
    Returns:
        dict: Resumen de notificaciones enviadas
    """
    from core.models import Producto, Usuario, PushSubscription, Empresa
    from core.push_service import enviar_notificacion_push

    # Iterar por empresa activa para garantizar aislamiento multi-tenant
    empresas_activas = Empresa.objects.filter(activa=True)
    total_enviadas = 0

    for empresa in empresas_activas:
        _enviadas = _verificar_stock_empresa(empresa)
        total_enviadas += _enviadas

    return {'status': 'ok', 'enviadas': total_enviadas}


def _verificar_stock_empresa(empresa):
    """Verifica y notifica stock crítico para una empresa específica."""
    from core.models import Producto, Usuario
    from core.push_service import enviar_notificacion_push

    # 1. Buscar productos con stock por debajo del mínimo O en cero con mínimo definido
    productos_criticos = Producto.objects.filter(
        empresa=empresa,
        stock__lt=F('stock_minimo'),
        stock_minimo__gt=0
    ).select_related('empresa')

    if not productos_criticos.exists():
        return 0

    # 2. Obtener directores/admins de ESA empresa con push activo
    admins = Usuario.objects.filter(
        empresa=empresa,
        is_staff=True,
        push_subscriptions__activa=True
    ).distinct()
    
    if not admins.exists():
        logger.warning(f"[Alertas] No hay administradores suscritos a push en empresa {empresa}")
        return 0
    
    # 3. Agrupar por nivel de criticidad
    criticos_extremos = []  # Stock < 10% del mínimo
    criticos_normales = []  # Stock < mínimo pero > 10%
    
    for prod in productos_criticos:
        porcentaje = (prod.stock / prod.stock_minimo * 100) if prod.stock_minimo > 0 else 0
        
        if porcentaje < 10:
            criticos_extremos.append(prod)
        else:
            criticos_normales.append(prod)
    
    # 4. Enviar notificaciones agrupadas
    notificaciones_enviadas = 0
    
    # Notificación para críticos extremos (urgente)
    if criticos_extremos:
        titulo = "🔴 STOCK CRÍTICO EXTREMO"
        if len(criticos_extremos) == 1:
            prod = criticos_extremos[0]
            pct = int(prod.stock / prod.stock_minimo * 100) if prod.stock_minimo and prod.stock_minimo > 0 else 0
            cuerpo = f"{prod.nombre}: {prod.stock} unidades ({pct}% del mínimo)"
        else:
            cuerpo = f"{len(criticos_extremos)} productos en stock crítico extremo (<10% del mínimo)"
        
        url = '/farmacia/stock-critico/'
        
        for admin in admins:
            for sub in admin.push_subscriptions.filter(activa=True):
                if enviar_notificacion_push(
                    sub, 
                    titulo, 
                    cuerpo, 
                    url,
                    datos_extra={
                        'tipo': 'stock_critico',
                        'severidad': 'ALTA',
                        'isla': 'FARMACIA'
                    }
                ):
                    notificaciones_enviadas += 1
    
    # Notificación para críticos normales (informativa, solo si hay muchos)
    if len(criticos_normales) >= 5:
        titulo = "⚠️ Stock Bajo en Farmacia"
        cuerpo = f"{len(criticos_normales)} productos por debajo del stock mínimo"
        url = '/farmacia/stock-critico/'
        
        for admin in admins:
            for sub in admin.push_subscriptions.filter(activa=True):
                if enviar_notificacion_push(
                    sub, 
                    titulo, 
                    cuerpo, 
                    url,
                    datos_extra={
                        'tipo': 'stock_bajo',
                        'severidad': 'MEDIA',
                        'isla': 'FARMACIA'
                    }
                ):
                    notificaciones_enviadas += 1
    
    logger.info(f"[Alertas] Empresa {empresa}: notificaciones stock enviadas: {notificaciones_enviadas}")
    return notificaciones_enviadas


def verificar_caducidad_proxima_y_notificar():
    """
    Verifica lotes próximos a caducar y envía notificaciones push.
    Solo notifica lotes CRÍTICOS (< 30 días).
    
    Returns:
        dict: Resumen de notificaciones enviadas
    """
    from core.models import Lote, Usuario, Empresa
    from core.push_service import enviar_notificacion_push

    # Iterar por empresa activa para garantizar aislamiento multi-tenant
    empresas_activas = Empresa.objects.filter(activa=True)
    total_enviadas = 0
    for empresa in empresas_activas:
        total_enviadas += _verificar_caducidad_empresa(empresa)
    return {'status': 'ok', 'enviadas': total_enviadas}


def _verificar_caducidad_empresa(empresa):
    """Verifica y notifica lotes próximos a caducar para una empresa específica."""
    from core.models import Lote, Usuario
    from core.push_service import enviar_notificacion_push

    hoy = date.today()
    fecha_critico = hoy + timedelta(days=_DIAS_CRITICO)

    # 1. Buscar lotes críticos con stock disponible — FILTRADO POR EMPRESA
    lotes_criticos = Lote.objects.filter(
        producto__empresa=empresa,
        cantidad__gt=0,
        fecha_caducidad__lt=fecha_critico,
        fecha_caducidad__gte=hoy,
    ).select_related('producto').order_by('fecha_caducidad')

    if not lotes_criticos.exists():
        return 0

    # 2. Obtener directores/admins de ESA empresa con push activo
    admins = Usuario.objects.filter(
        empresa=empresa,
        is_staff=True,
        push_subscriptions__activa=True,
    ).prefetch_related('push_subscriptions').distinct()

    if not admins.exists():
        return 0
    
    # 3. Enviar notificación agrupada
    titulo = "⏰ Medicamentos Próximos a Caducar"
    
    if len(lotes_criticos) == 1:
        lote = lotes_criticos[0]
        dias = (lote.fecha_caducidad - hoy).days
        cuerpo = f"{lote.producto.nombre} (Lote {lote.numero_lote}): {dias} días hasta caducar"
    else:
        cuerpo = f"{len(lotes_criticos)} lotes caducan en menos de 30 días"
    
    url = '/farmacia/semaforo-caducidad/'
    
    notificaciones_enviadas = 0
    for admin in admins:
        for sub in admin.push_subscriptions.filter(activa=True):
            if enviar_notificacion_push(
                sub, 
                titulo, 
                cuerpo, 
                url,
                datos_extra={
                    'tipo': 'caducidad_proxima',
                    'severidad': 'ALTA',
                    'isla': 'FARMACIA'
                }
            ):
                notificaciones_enviadas += 1
    
    logger.info(f"[Alertas] Empresa {empresa}: notificaciones caducidad enviadas: {notificaciones_enviadas}")
    return notificaciones_enviadas


def registrar_uso_precio_staff(usuario, producto, precio_neto, precio_publico, venta_id=None):
    """
    Registra el uso del botón "Precio Staff" en el PDV y envía notificación silenciosa al Director.
    Auditoría de seguridad para prevenir abuso.
    
    Args:
        usuario: Usuario que aplicó el precio staff
        producto: Producto vendido
        precio_neto: Precio neto aplicado
        precio_publico: Precio público que debería haber sido
        venta_id: ID de la venta (opcional)
    
    Returns:
        bool: True si se registró exitosamente
    """
    from consultorio.models import IncidenciaSentinel
    from core.models import Usuario
    from core.push_service import enviar_notificacion_push
    
    try:
        # 1. Crear incidencia en Sentinel (tipo informativo, no error)
        descuento_aplicado = float(precio_publico) - float(precio_neto)
        porcentaje_descuento = (descuento_aplicado / float(precio_publico) * 100) if precio_publico > 0 else 0
        
        incidencia = IncidenciaSentinel.objects.create(
            empresa=usuario.empresa,
            tipo_excepcion='USO_PRECIO_STAFF',
            mensaje_error=f'Precio Staff aplicado por {usuario.get_full_name()}',
            path='/farmacia/pdv/',
            metodo='POST',
            usuario=usuario,
            severidad='MEDIA',
            namespace='farmacia',
            analisis_ia=(
                f"Se aplicó precio de costo (Precio Staff) en farmacia.\n\n"
                f"**Producto:** {producto.nombre}\n"
                f"**Usuario:** {usuario.get_full_name()} ({usuario.username})\n"
                f"**Precio Público:** ${precio_publico:.2f}\n"
                f"**Precio Neto:** ${precio_neto:.2f}\n"
                f"**Descuento:** ${descuento_aplicado:.2f} ({porcentaje_descuento:.1f}%)\n"
                f"**Venta ID:** {venta_id or 'N/A'}\n\n"
                f"**Auditoría QC:** Revisar si el beneficio fue aplicado correctamente (empleado/familia)."
            ),
            estado='PENDIENTE'
        )
        
        logger.info(f"Uso de Precio Staff registrado: Incidencia #{incidencia.id}")
        
        # 2. Enviar notificación push silenciosa al Director
        admins = Usuario.objects.filter(
            is_superuser=True,
            push_subscriptions__activa=True
        ).distinct()
        
        for admin in admins:
            for sub in admin.push_subscriptions.filter(activa=True):
                titulo = "🔍 Precio Staff Aplicado"
                cuerpo = f"{usuario.get_full_name()} aplicó precio de costo en {producto.nombre} (${descuento_aplicado:.2f} desc.)"
                url = f'/consultorio/sentinel/{incidencia.id}/'
                
                enviar_notificacion_push(
                    sub, 
                    titulo, 
                    cuerpo, 
                    url,
                    datos_extra={
                        'tipo': 'precio_staff',
                        'severidad': 'MEDIA',
                        'isla': 'FARMACIA',
                        'incidenciaId': incidencia.id
                    }
                )
        
        return True
        
    except Exception as e:
        # Justificación: Auditoría secundaria no bloqueante (registro de Sentinel y push).
        logger.error(f"Error al registrar uso de Precio Staff: {e}", exc_info=True)
        return False
