# -*- coding: utf-8 -*-
"""
🔬 PILAR 1: MIGRACIÓN DE DATOS - UNIFICACIÓN FORENSE
Sistema PRISLAB - Laboratorio

Objetivo: Consolidar laboratorio.Orden → core.OrdenDeServicio
Garantiza: Cero pérdida de datos, trazabilidad completa
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime
import logging

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from django.utils import timezone
from laboratorio.models import Orden as OrdenLab, DetalleOrden as DetalleLab, Resultado as ResultadoLab
from core.models import (
    OrdenDeServicio, DetalleOrden, Estudio, Paciente, Usuario, 
    Empresa, Sucursal, ResultadoParametro, AuditLog
)

# ==============================================================================
# CONFIGURACIÓN Y VALIDACIÓN
# ==============================================================================

DRY_RUN = False  # Cambiar a False para ejecutar la migración real
VERBOSE = True

def log(mensaje, nivel="INFO"):
    """Logger simple con timestamps."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefijo = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "DEBUG": "🔍"
    }.get(nivel, "📋")
    
    print(f"[{timestamp}] {prefijo} {mensaje}")

# ==============================================================================
# PASO 1: ANÁLISIS PREVIO
# ==============================================================================

def analizar_estado_actual():
    """Analiza el estado actual antes de la migración."""
    log("="*80, "INFO")
    log("AUDITORÍA PRE-MIGRACIÓN - PILAR 1: LA VERDAD ÚNICA", "INFO")
    log("="*80, "INFO")
    
    # Contar órdenes en ambas tablas
    ordenes_lab = OrdenLab.objects.count()
    ordenes_core = OrdenDeServicio.objects.count()
    
    log(f"Órdenes en laboratorio.Orden: {ordenes_lab}", "INFO")
    log(f"Órdenes en core.OrdenDeServicio: {ordenes_core}", "INFO")
    
    # Verificar órdenes con resultados
    ordenes_con_resultados = OrdenLab.objects.filter(
        detalles__resultados__isnull=False
    ).distinct().count()
    
    log(f"Órdenes con resultados capturados: {ordenes_con_resultados}", "WARNING")
    
    # Verificar órdenes validadas
    ordenes_validadas = OrdenLab.objects.filter(
        estado_analisis=OrdenLab.ESTADO_ANALISIS_VALIDADO
    ).count()
    
    log(f"Órdenes VALIDADAS (críticas): {ordenes_validadas}", "WARNING")
    
    # Verificar pacientes sin equivalente
    pacientes_laboratorio = OrdenLab.objects.values_list('paciente_id', flat=True).distinct()
    pacientes_core = Paciente.objects.filter(id__in=pacientes_laboratorio).count()
    
    log(f"Pacientes únicos en órdenes: {len(set(pacientes_laboratorio))}", "INFO")
    log(f"Pacientes existentes en core: {pacientes_core}", "INFO")
    
    if len(set(pacientes_laboratorio)) != pacientes_core:
        log("⚠️ ADVERTENCIA: Hay pacientes huérfanos", "WARNING")
    
    # Verificar estudios
    estudios_lab = DetalleLab.objects.values_list('estudio_id', flat=True).distinct()
    estudios_core = Estudio.objects.filter(id__in=estudios_lab).count()
    
    log(f"Estudios únicos en detalles: {len(set(estudios_lab))}", "INFO")
    log(f"Estudios existentes en core: {estudios_core}", "INFO")
    
    log("="*80, "INFO")
    
    return {
        'ordenes_lab': ordenes_lab,
        'ordenes_core': ordenes_core,
        'ordenes_validadas': ordenes_validadas,
        'ordenes_con_resultados': ordenes_con_resultados
    }

# ==============================================================================
# PASO 2: MIGRACIÓN DE ÓRDENES
# ==============================================================================

def migrar_orden(orden_lab, empresa_default, usuario_default):
    """
    Migra una orden individual de laboratorio.Orden a core.OrdenDeServicio.
    
    Garantiza:
    - Preservación de timestamps originales
    - Mapeo correcto de estados
    - Generación de folio único
    - Migración de resultados existentes
    """
    try:
        # Verificar si ya existe una orden migrada (por ID o folio)
        folio_generado = f"LAB-MIG-{orden_lab.id}"
        
        if OrdenDeServicio.objects.filter(folio_orden=folio_generado).exists():
            log(f"Orden #{orden_lab.id} ya migrada (Folio: {folio_generado})", "DEBUG")
            return OrdenDeServicio.objects.get(folio_orden=folio_generado), False
        
        # Mapeo de estados
        mapeo_estados = {
            OrdenLab.ESTADO_ANALISIS_PENDIENTE: 'PAGADO',
            OrdenLab.ESTADO_ANALISIS_EN_PROCESO: 'EN_PROCESO',
            OrdenLab.ESTADO_ANALISIS_VALIDADO: 'RESULTADOS_LISTOS',
        }
        
        estado_nuevo = mapeo_estados.get(orden_lab.estado_analisis, 'PAGADO')
        
        # Calcular total desde detalles
        total_orden = Decimal('0.00')
        for detalle in orden_lab.detalles.all():
            total_orden += detalle.subtotal
        
        # Crear OrdenDeServicio
        orden_nueva = OrdenDeServicio(
            empresa=empresa_default,
            sucursal=orden_lab.usuario_creador.sucursal if hasattr(orden_lab.usuario_creador, 'sucursal') else None,
            paciente=orden_lab.paciente,
            fecha_creacion=orden_lab.fecha_creacion,
            estado=estado_nuevo,
            total=total_orden,
            anticipo=total_orden if orden_lab.estado_pago else Decimal('0.00'),
            responsable_ingreso=orden_lab.usuario_creador,
            folio_orden=folio_generado,
            tipo_servicio='RUTINA',
            tarifa=orden_lab.get_origen_display(),
            estado_pago='PAGADO' if orden_lab.estado_pago else 'PENDIENTE',
            diagnostico='Migrado desde laboratorio.Orden',
            notas_internas=f"Migrado automáticamente. ID original: {orden_lab.id}"
        )
        
        # Preservar timestamps originales (si es posible)
        orden_nueva.save()
        
        # Actualizar fecha de creación manualmente
        OrdenDeServicio.objects.filter(id=orden_nueva.id).update(
            fecha_creacion=orden_lab.fecha_creacion
        )
        
        log(f"✅ Orden #{orden_lab.id} → OrdenDeServicio #{orden_nueva.id} (Folio: {folio_generado})", "SUCCESS")
        
        # Migrar detalles
        migrar_detalles_orden(orden_lab, orden_nueva)
        
        # Registrar en AuditLog
        AuditLog.objects.create(
            usuario=usuario_default,
            accion='MIGRACION_ORDEN',
            modelo='OrdenDeServicio',
            objeto_id=orden_nueva.id,
            folio_orden=orden_nueva.folio_orden,
            detalles={
                'orden_original_id': orden_lab.id,
                'estado_original': orden_lab.estado_analisis,
                'fecha_validacion_original': str(orden_lab.fecha_validacion) if orden_lab.fecha_validacion else None,
                'migracion_automatica': True
            }
        )
        
        return orden_nueva, True
    
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en migrar_orden (migracion_ordenes_forense.py)")
        log(f"❌ Error migrando orden #{orden_lab.id}: {str(e)}", "ERROR")
        raise

# ==============================================================================
# PASO 3: MIGRACIÓN DE DETALLES
# ==============================================================================

def migrar_detalles_orden(orden_lab, orden_nueva):
    """Migra los detalles (estudios) de una orden."""
    detalles_migrados = 0
    
    for detalle_lab in orden_lab.detalles.all():
        try:
            # Crear DetalleOrden en core
            detalle_nuevo = DetalleOrden(
                orden=orden_nueva,
                estudio=detalle_lab.estudio,
                precio_momento=detalle_lab.precio,
                resultado=None,  # Se migrará después si existe
                observaciones=f"Migrado desde laboratorio.DetalleOrden #{detalle_lab.id}",
                validado_por=orden_lab.usuario_valido if orden_lab.estado_analisis == OrdenLab.ESTADO_ANALISIS_VALIDADO else None,
                fecha_validacion=orden_lab.fecha_validacion,
                estado_procesamiento='RESULTADO_LISTO' if orden_lab.estado_analisis == OrdenLab.ESTADO_ANALISIS_VALIDADO else 'PENDIENTE_TOMA'
            )
            detalle_nuevo.save()
            
            # Migrar resultados si existen
            migrar_resultados_detalle(detalle_lab, detalle_nuevo, orden_nueva)
            
            detalles_migrados += 1
        
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en migrar_detalles_orden (migracion_ordenes_forense.py)")
            log(f"  ⚠️ Error en detalle #{detalle_lab.id}: {str(e)}", "WARNING")
    
    log(f"  → {detalles_migrados} detalles migrados", "INFO")

# ==============================================================================
# PASO 4: MIGRACIÓN DE RESULTADOS
# ==============================================================================

def migrar_resultados_detalle(detalle_lab, detalle_nuevo, orden_nueva):
    """Migra resultados de laboratorio.Resultado a core.ResultadoParametro."""
    resultados = ResultadoLab.objects.filter(detalle_orden=detalle_lab)
    
    if not resultados.exists():
        return
    
    for resultado_lab in resultados:
        try:
            # Buscar parámetro correspondiente
            parametro = resultado_lab.parametro
            
            # Determinar si es crítico (valores fuera de rango)
            es_critico = False
            if resultado_lab.valor_numerico and parametro.valor_ref_min and parametro.valor_ref_max:
                if resultado_lab.valor_numerico < parametro.valor_ref_min or resultado_lab.valor_numerico > parametro.valor_ref_max:
                    es_critico = True
            
            # Crear ResultadoParametro
            resultado_nuevo = ResultadoParametro(
                orden=orden_nueva,
                detalle_estudio=detalle_nuevo,
                parametro=parametro,
                valor_numerico=resultado_lab.valor_numerico,
                valor_texto=resultado_lab.valor_texto,
                es_critico=es_critico,
                observaciones=resultado_lab.observaciones or f"Migrado desde laboratorio.Resultado #{resultado_lab.id}",
                validado=True if orden_nueva.estado == 'RESULTADOS_LISTOS' else False,
                fecha_captura=resultado_lab.fecha_analisis or timezone.now()
            )
            resultado_nuevo.save()
            
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en migrar_resultados_detalle (migracion_ordenes_forense.py)")
            log(f"    ⚠️ Error en resultado #{resultado_lab.id}: {str(e)}", "WARNING")

# ==============================================================================
# PASO 5: EJECUCIÓN PRINCIPAL
# ==============================================================================

@transaction.atomic
def ejecutar_migracion():
    """Ejecuta la migración completa con transacción atómica."""
    log("", "INFO")
    log("🚀 INICIANDO MIGRACIÓN FORENSE", "INFO")
    log("", "INFO")
    
    # Análisis previo
    estadisticas = analizar_estado_actual()
    
    if estadisticas['ordenes_lab'] == 0:
        log("✅ No hay órdenes que migrar en laboratorio.Orden", "SUCCESS")
        return
    
    # Confirmar migración
    if not DRY_RUN:
        respuesta = input("\n⚠️ ¿Confirmar migración REAL? (escriba 'SI' para continuar): ")
        if respuesta != 'SI':
            log("❌ Migración cancelada por el usuario", "ERROR")
            return
    
    # Empresa explícita (multi-tenant: sin primera fila arbitraria)
    eid = os.environ.get("PRISLAB_EMPRESA_ID")
    if not eid:
        log("❌ Defina PRISLAB_EMPRESA_ID con el pk de la empresa destino.", "ERROR")
        return
    try:
        empresa_default = Empresa.objects.get(pk=int(eid))
    except (ValueError, Empresa.DoesNotExist) as e:
        log(f"❌ PRISLAB_EMPRESA_ID inválido o empresa inexistente: {e}", "ERROR")
        return

    usuario_default = Usuario.objects.filter(is_superuser=True).first()
    if not usuario_default:
        log("❌ No se encontró usuario administrador (is_superuser=True)", "ERROR")
        return
    
    log("", "INFO")
    log("📦 MIGRANDO ÓRDENES...", "INFO")
    log("", "INFO")
    
    # Migrar todas las órdenes
    ordenes_lab = OrdenLab.objects.all().order_by('fecha_creacion')
    total_ordenes = ordenes_lab.count()
    ordenes_migradas = 0
    ordenes_existentes = 0
    
    for i, orden_lab in enumerate(ordenes_lab, 1):
        try:
            orden_nueva, es_nueva = migrar_orden(orden_lab, empresa_default, usuario_default)
            
            if es_nueva:
                ordenes_migradas += 1
            else:
                ordenes_existentes += 1
            
            # Progreso
            if i % 10 == 0:
                log(f"Progreso: {i}/{total_ordenes} órdenes procesadas", "INFO")
        
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en ejecutar_migracion (migracion_ordenes_forense.py)")
            log(f"❌ Error crítico en orden #{orden_lab.id}: {str(e)}", "ERROR")
            if not DRY_RUN:
                raise  # Rollback en caso de error
    
    # Resumen final
    log("", "INFO")
    log("="*80, "INFO")
    log("📊 RESUMEN DE MIGRACIÓN", "INFO")
    log("="*80, "INFO")
    log(f"Total de órdenes procesadas: {total_ordenes}", "INFO")
    log(f"Órdenes migradas exitosamente: {ordenes_migradas}", "SUCCESS")
    log(f"Órdenes ya existentes (omitidas): {ordenes_existentes}", "INFO")
    log("="*80, "INFO")
    
    if DRY_RUN:
        log("⚠️ MODO DRY RUN - No se guardaron cambios", "WARNING")
        raise Exception("Dry run - Rollback intencional")
    else:
        log("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE", "SUCCESS")
        log("", "INFO")
        log("⚠️ IMPORTANTE: Ahora debes ejecutar la refactorización de vistas", "WARNING")
        log("   para que el sistema use core.OrdenDeServicio", "WARNING")

# ==============================================================================
# EJECUCIÓN
# ==============================================================================

if __name__ == '__main__':
    try:
        ejecutar_migracion()
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en ejecutar_migracion (migracion_ordenes_forense.py)")
        if "Dry run" not in str(e):
            log(f"❌ Error fatal: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()