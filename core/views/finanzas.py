"""
ARQUITECTURA FINANCIERA SEGREGADA - PRISLAB v5.0
Sistema de Silos de Información con Cúpula de Control (God Mode)
"""
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.db.models import Sum, Count, F, Q, DecimalField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from collections import Counter

from core.models import (
    Empresa,
    OrdenDeServicio,
    PagoOrden,
    DetalleOrden,
    DevolucionVenta,
    SalesReturn,
)
from core.lims_cart import detalle_orden_etiqueta

logger = logging.getLogger(__name__)


# ============================================================================
# SILO A: LABORATORIO (VISTA OPERATIVA)
# ============================================================================
class LabCajaView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Caja del Laboratorio - Solo KPIs operativos humanistas.
    Acceso: Personal de Lab + Admin.
    """
    template_name = 'core/finanzas/caja_laboratorio.html'
    
    def test_func(self):
        """Verificar que el usuario es personal de laboratorio o admin"""
        user = self.request.user
        return (
            user.rol in ['QUIMICO', 'RECEPCION', 'ADMIN'] or 
            user.is_superuser
        )
    
    def handle_no_permission(self):
        """Redirección amigable si no tiene permiso"""
        return redirect('dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        empresa = getattr(user, 'empresa', None)
        if not empresa:
            context['modulo_inactivo'] = True
            context['mensaje_error'] = "Usuario sin empresa asignada."
            return context
        hoy = timezone.now().date()
        inicio_dia = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
        
        # Filtrar por empresa y sucursal del usuario
        ordenes_hoy = OrdenDeServicio.objects.filter(
            empresa=empresa,
            fecha_creacion__gte=inicio_dia
        )
        
        if user.sucursal:
            ordenes_hoy = ordenes_hoy.filter(sucursal=user.sucursal)
        
        # KPI HUMANISTA 1: Pacientes Atendidos
        context['pacientes_atendidos'] = ordenes_hoy.values('paciente').distinct().count()
        
        # KPI HUMANISTA 2: Órdenes Completadas (OrdenDeServicio.estado, no estado_procesamiento)
        context['ordenes_completadas'] = ordenes_hoy.filter(estado='ENTREGADO').count()
        
        # KPI HUMANISTA 3: Órdenes Pendientes
        context['ordenes_pendientes'] = ordenes_hoy.exclude(estado='ENTREGADO').count()
        
        # JOIN por dimensiones de orden (evita materializar orden__in con miles de PKs)
        pago_join = {
            'orden__empresa': empresa,
            'orden__fecha_creacion__gte': inicio_dia,
        }
        if user.sucursal:
            pago_join['orden__sucursal'] = user.sucursal

        pagos_hoy = PagoOrden.objects.filter(**pago_join).aggregate(
            total_ingresos=Coalesce(
                Sum(F('monto_efectivo') + F('monto_tarjeta') + F('monto_transferencia')),
                Value(0),
                output_field=DecimalField()
            )
        )
        context['ingresos_dia'] = pagos_hoy['total_ingresos']
        
        # COMPARATIVA CON AYER (Solo ingresos)
        ayer = hoy - timedelta(days=1)
        inicio_ayer = timezone.make_aware(datetime.combine(ayer, datetime.min.time()))
        fin_ayer = timezone.make_aware(datetime.combine(ayer, datetime.max.time()))
        
        pago_join_ayer = {
            'orden__empresa': empresa,
            'orden__fecha_creacion__gte': inicio_ayer,
            'orden__fecha_creacion__lte': fin_ayer,
        }
        if user.sucursal:
            pago_join_ayer['orden__sucursal'] = user.sucursal

        pagos_ayer = PagoOrden.objects.filter(**pago_join_ayer).aggregate(
            total=Coalesce(
                Sum(F('monto_efectivo') + F('monto_tarjeta') + F('monto_transferencia')),
                Value(0),
                output_field=DecimalField()
            )
        )
        
        context['ingresos_ayer'] = pagos_ayer['total']
        context['variacion_ingreso'] = context['ingresos_dia'] - context['ingresos_ayer']
        
        # Líneas LIMS más solicitadas hoy (Top 5; clave legacy estudio__nombre para plantilla)
        detalle_join = {
            'orden__empresa': empresa,
            'orden__fecha_creacion__gte': inicio_dia,
        }
        if user.sucursal:
            detalle_join['orden__sucursal'] = user.sucursal

        _cnt = Counter()
        for d in DetalleOrden.objects.filter(**detalle_join).select_related(
            'analito', 'perfil_lims', 'paquete_lims'
        ).iterator(chunk_size=500):
            lab = detalle_orden_etiqueta(d).strip()
            if lab:
                _cnt[lab] += 1
        context['estudios_top'] = [
            {'estudio__nombre': nombre, 'cantidad': n}
            for nombre, n in _cnt.most_common(5)
        ]
        
        context['fecha_corte'] = timezone.now()
        context['usuario_corte'] = user.get_full_name() or user.username
        context['sucursal'] = user.sucursal.nombre if user.sucursal else "Todas las sucursales"
        
        return context


# ============================================================================
# SILO B: FARMACIA (VISTA OPERATIVA)
# ============================================================================
class FarmaciaCajaView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Caja de Farmacia - Solo KPIs operativos humanistas.
    Acceso: Personal de Farmacia + Admin.
    """
    template_name = 'core/finanzas/caja_farmacia.html'
    
    def test_func(self):
        """Verificar que el usuario es personal de farmacia o admin"""
        user = self.request.user
        return (
            user.rol in ['CAJERO', 'GERENTE', 'ADMIN'] or 
            user.is_superuser
        )
    
    def handle_no_permission(self):
        """Redirección amigable si no tiene permiso"""
        return redirect('dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # MANEJO DE ERROR: Si el módulo Farmacia no está activo
        try:
            from core.models import Venta, DetalleVenta, Producto
        except ImportError:
            context['modulo_inactivo'] = True
            context['mensaje_error'] = "Error de configuración: no se pueden importar los modelos de Farmacia. Contacte al administrador."
            return context
        
        user = self.request.user
        empresa = getattr(user, 'empresa', None)
        if not empresa:
            context['modulo_inactivo'] = True
            context['mensaje_error'] = "Usuario sin empresa asignada."
            return context
        hoy = timezone.now().date()
        inicio_dia = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
        
        # Filtrar ventas del día — excluir CANCELADAS para KPIs correctos
        ventas_hoy = Venta.objects.filter(
            empresa=empresa,
            fecha__gte=inicio_dia,
            estado='COMPLETADA',
        )

        if user.sucursal:
            ventas_hoy = ventas_hoy.filter(sucursal=user.sucursal)
        
        # KPI HUMANISTA 1: Clientes Atendidos
        context['clientes_atendidos'] = ventas_hoy.count()
        
        # KPI HUMANISTA 2: Recetas Surtidas
        context['recetas_surtidas'] = ventas_hoy.filter(
            receta__isnull=False
        ).count()
        
        dv_join = {
            'venta__empresa': empresa,
            'venta__fecha__gte': inicio_dia,
            'venta__estado': 'COMPLETADA',
        }
        if user.sucursal:
            dv_join['venta__sucursal'] = user.sucursal

        # KPI HUMANISTA 3: Productos Vendidos
        context['productos_vendidos'] = DetalleVenta.objects.filter(**dv_join).aggregate(
            total=Coalesce(Sum('cantidad'), Value(0))
        )['total'] or 0
        
        # INGRESO DEL DÍA (Sin mostrar costos ni utilidad)
        context['ingresos_dia'] = ventas_hoy.aggregate(
            total=Coalesce(Sum('total'), Value(0), output_field=DecimalField())
        )['total']
        
        # COMPARATIVA CON AYER
        ayer = hoy - timedelta(days=1)
        inicio_ayer = timezone.make_aware(datetime.combine(ayer, datetime.min.time()))
        fin_ayer = timezone.make_aware(datetime.combine(ayer, datetime.max.time()))
        
        ventas_ayer = Venta.objects.filter(
            empresa=empresa,
            fecha__gte=inicio_ayer,
            fecha__lte=fin_ayer,
            estado='COMPLETADA',
        )
        
        if user.sucursal:
            ventas_ayer = ventas_ayer.filter(sucursal=user.sucursal)
        
        ingresos_ayer = ventas_ayer.aggregate(
            total=Coalesce(Sum('total'), Value(0), output_field=DecimalField())
        )['total']
        
        context['ingresos_ayer'] = ingresos_ayer
        context['variacion_ingreso'] = context['ingresos_dia'] - ingresos_ayer
        
        # Productos más vendidos (Top 5)
        context['productos_top'] = DetalleVenta.objects.filter(**dv_join).values(
            'producto__nombre'
        ).annotate(
            cantidad=Sum('cantidad')
        ).order_by('-cantidad')[:5]
        
        context['fecha_corte'] = timezone.now()
        context['usuario_corte'] = user.get_full_name() or user.username
        context['sucursal'] = user.sucursal.nombre if user.sucursal else "Todas las sucursales"
        
        return context


# ============================================================================
# TORRE DE CONTROL: GOD MODE (SOLO SUPERUSER)
# ============================================================================
class MasterDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Dashboard Maestro del Dueño - LA VERDAD ABSOLUTA DEL NEGOCIO.
    Acceso: SOLO SUPERUSER.
    Auditoría: Cada acceso se registra en log.
    """
    template_name = 'core/finanzas/master_dashboard.html'
    
    def test_func(self):
        """ACCESO RESTRINGIDO: Solo el dueño (superuser)"""
        return self.request.user.is_superuser
    
    def handle_no_permission(self):
        """Bloqueo total si no es superuser"""
        logger.warning(
            f"INTENTO DE ACCESO NO AUTORIZADO A MASTER DASHBOARD - "
            f"Usuario: {self.request.user.username} - IP: {self.get_client_ip()}"
        )
        return redirect('dashboard')
    
    def get_client_ip(self):
        """Obtener IP del cliente para auditoría"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        empresa = getattr(user, 'empresa', None)
        if not empresa:
            return context

        # AUDITORÍA DE ACCESO
        logger.info(
            f"ACCESO A MASTER DASHBOARD - Usuario: {user.username} - "
            f"IP: {self.get_client_ip()} - Timestamp: {timezone.now()}"
        )
        
        hoy = timezone.now().date()
        inicio_dia = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
        
        # ========================================================================
        # CÁLCULO MAESTRO: RENTABILIDAD REAL
        # ========================================================================
        
        # --- LABORATORIO ---
        ordenes_hoy = OrdenDeServicio.objects.filter(
            empresa=empresa,
            fecha_creacion__gte=inicio_dia
        )
        
        # Ingresos Lab (JOIN por empresa + rango de fecha; sin lista masiva de PKs)
        ingresos_lab = PagoOrden.objects.filter(
            orden__empresa=empresa,
            orden__fecha_creacion__gte=inicio_dia,
        ).aggregate(
            total=Coalesce(
                Sum(F('monto_efectivo') + F('monto_tarjeta') + F('monto_transferencia')),
                Value(0),
                output_field=DecimalField()
            )
        )['total']
        
        # Costos Lab (mismo criterio temporal; agregado legacy estudio si existe en esquema)
        costos_lab = DetalleOrden.objects.filter(
            orden__empresa=empresa,
            orden__fecha_creacion__gte=inicio_dia,
        ).aggregate(
            total=Coalesce(
                Sum('estudio__costo_operativo'),
                Value(0),
                output_field=DecimalField()
            )
        )['total']
        
        # --- FARMACIA ---
        ventas_hoy = None  # set if farmacia module available
        try:
            from core.models import Venta, DetalleVenta, Producto

            ventas_hoy = Venta.objects.filter(
                empresa=empresa,
                fecha__gte=inicio_dia
            )
            
            # Ingresos Farmacia
            ingresos_farmacia = ventas_hoy.aggregate(
                total=Coalesce(Sum('total'), Value(0), output_field=DecimalField())
            )['total']
            
            # Costos Farmacia: JOIN por empresa + fecha (sin venta__in masivo)
            costos_farmacia = DetalleVenta.objects.filter(
                venta__empresa=empresa,
                venta__fecha__gte=inicio_dia,
            ).aggregate(
                total=Coalesce(
                    Sum(
                        F('cantidad') * Coalesce(F('costo_unitario_momento'), F('producto__precio_compra'), Value(0))
                    ),
                    Value(0),
                    output_field=DecimalField()
                )
            )['total']
            
        except (ImportError, Exception) as e:
            logger.warning(f"Módulo Farmacia no disponible para Master Dashboard: {e}")
            ingresos_farmacia = Decimal('0.00')
            costos_farmacia = Decimal('0.00')
            ventas_hoy = None
        
        # --- DEVOLUCIONES (Forense + PDV: ambos modelos) ---
        devoluciones_forense = DevolucionVenta.objects.filter(
            empresa=empresa,
            fecha_devolucion__gte=inicio_dia
        ).aggregate(
            total=Coalesce(Sum('monto_devuelto'), Value(0), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        devoluciones_pdv = SalesReturn.objects.filter(
            empresa=empresa,
            fecha_devolucion__gte=inicio_dia
        ).aggregate(
            total=Coalesce(Sum('monto_reembolsado'), Value(0), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        devoluciones_hoy = devoluciones_forense + devoluciones_pdv
        
        # --- CÁLCULO FINAL ---
        ingreso_total = (ingresos_lab or Decimal('0.00')) + (ingresos_farmacia or Decimal('0.00'))
        costo_total = (costos_lab or Decimal('0.00')) + (costos_farmacia or Decimal('0.00'))
        utilidad_neta = ingreso_total - costo_total - devoluciones_hoy
        margen_utilidad = (utilidad_neta / ingreso_total * 100) if ingreso_total > 0 else 0
        
        # PROYECCIÓN: Comparativa con Ayer
        ayer = hoy - timedelta(days=1)
        inicio_ayer = timezone.make_aware(datetime.combine(ayer, datetime.min.time()))
        fin_ayer = timezone.make_aware(datetime.combine(ayer, datetime.max.time()))
        
        ingresos_lab_ayer = PagoOrden.objects.filter(
            orden__empresa=empresa,
            orden__fecha_creacion__gte=inicio_ayer,
            orden__fecha_creacion__lte=fin_ayer,
        ).aggregate(
            total=Coalesce(
                Sum(F('monto_efectivo') + F('monto_tarjeta') + F('monto_transferencia')),
                Value(0),
                output_field=DecimalField()
            )
        )['total']

        costos_lab_ayer = DetalleOrden.objects.filter(
            orden__empresa=empresa,
            orden__fecha_creacion__gte=inicio_ayer,
            orden__fecha_creacion__lte=fin_ayer,
        ).aggregate(
            total=Coalesce(
                Sum('estudio__costo_operativo'),
                Value(0),
                output_field=DecimalField()
            )
        )['total']
        
        try:
            ventas_ayer = Venta.objects.filter(
                empresa=empresa,
                fecha__gte=inicio_ayer,
                fecha__lte=fin_ayer
            )
            
            ingresos_farmacia_ayer = ventas_ayer.aggregate(
                total=Coalesce(Sum('total'), Value(0), output_field=DecimalField())
            )['total']
            
            costos_farmacia_ayer = DetalleVenta.objects.filter(
                venta__empresa=empresa,
                venta__fecha__gte=inicio_ayer,
                venta__fecha__lte=fin_ayer,
            ).aggregate(
                total=Coalesce(
                    Sum(
                        F('cantidad') * Coalesce(F('costo_unitario_momento'), F('producto__precio_compra'), Value(0))
                    ),
                    Value(0),
                    output_field=DecimalField()
                )
            )['total']
        except (ImportError, Exception):
            ingresos_farmacia_ayer = Decimal('0.00')
            costos_farmacia_ayer = Decimal('0.00')
        
        utilidad_neta_ayer = (
            (ingresos_lab_ayer or Decimal('0.00')) + (ingresos_farmacia_ayer or Decimal('0.00'))
        ) - (costos_lab_ayer or Decimal('0.00')) - (costos_farmacia_ayer or Decimal('0.00'))
        variacion_utilidad = utilidad_neta - utilidad_neta_ayer
        
        # ========================================================================
        # CONTEXTO PARA EL TEMPLATE
        # ========================================================================
        
        # SECCIÓN PRIVADA (🔒 SOLO DUEÑO)
        context['ingreso_total'] = ingreso_total
        context['costo_total'] = costo_total
        context['utilidad_neta'] = utilidad_neta
        context['margen_utilidad'] = margen_utilidad
        context['devoluciones'] = devoluciones_hoy
        
        # PROYECCIÓN
        context['utilidad_ayer'] = utilidad_neta_ayer
        context['variacion_utilidad'] = variacion_utilidad
        context['variacion_porcentaje'] = (
            (variacion_utilidad / utilidad_neta_ayer * 100) 
            if utilidad_neta_ayer > 0 else 0
        )
        
        # SECCIÓN OPERATIVA (Comparativa) — proteger None de agregados vacíos
        _ing_lab = ingresos_lab or Decimal('0.00')
        _cost_lab = costos_lab or Decimal('0.00')
        _ing_farm = ingresos_farmacia or Decimal('0.00')
        _cost_farm = costos_farmacia or Decimal('0.00')
        context['lab_ingresos'] = ingresos_lab
        context['lab_costos'] = costos_lab
        context['lab_utilidad'] = _ing_lab - _cost_lab
        
        context['farmacia_ingresos'] = ingresos_farmacia
        context['farmacia_costos'] = costos_farmacia
        context['farmacia_utilidad'] = _ing_farm - _cost_farm
        
        # KPIs Operativos
        context['pacientes_lab'] = ordenes_hoy.values('paciente').distinct().count()
        context['ordenes_completadas'] = ordenes_hoy.filter(estado='ENTREGADO').count()
        
        context['clientes_farmacia'] = ventas_hoy.count() if ventas_hoy is not None else 0
        
        context['fecha_corte'] = timezone.now()
        context['usuario_corte'] = user.get_full_name() or user.username
        
        return context
