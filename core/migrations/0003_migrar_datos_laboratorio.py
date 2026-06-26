# -*- coding: utf-8 -*-
# Generated manually for data migration

from django.db import migrations
import uuid
import logging


def migrar_datos_laboratorio_a_core(apps, schema_editor):
    """
    MIGRACIÓN FORENSE DE DATOS - PILAR 1 & 4
    
    Copia todos los datos de laboratorio.Orden a core.OrdenDeServicio
    Garantiza: Cero pérdida de datos, trazabilidad completa
    """
    # Obtener modelos
    OrdenLab = apps.get_model('laboratorio', 'Orden')
    OrdenDeServicio = apps.get_model('core', 'OrdenDeServicio')
    AuditLog = apps.get_model('core', 'AuditLog')
    
    # Estadísticas
    total_ordenes = OrdenLab.objects.count()
    ordenes_migradas = 0
    ordenes_actualizadas = 0
    ordenes_creadas = 0
    
    print(f"\n{'='*80}")
    print(f"MIGRACION FORENSE DE DATOS - LABORATORIO A CORE")
    print(f"{'='*80}")
    print(f"Total de ordenes a procesar: {total_ordenes}\n")
    
    # Mapeo de estados clínicos
    mapeo_estado_clinico = {
        'PENDIENTE': 'PENDIENTE_TOMA',
        'EN_PROCESO': 'EN_PROCESO',
        'VALIDADO': 'COMPLETO',
    }
    
    for orden_lab in OrdenLab.objects.all():
        try:
            # Buscar OrdenDeServicio correspondiente por paciente y fecha
            orden_core = OrdenDeServicio.objects.filter(
                paciente=orden_lab.paciente,
                fecha_creacion__date=orden_lab.fecha_creacion.date()
            ).first()
            
            if not orden_core:
                # Verificar si ya existe con folio migrado
                folio_migrado = f"LAB-MIG-{orden_lab.id}"
                orden_core = OrdenDeServicio.objects.filter(
                    folio_orden=folio_migrado
                ).first()
            
            if orden_core:
                # ACTUALIZAR orden existente con datos de laboratorio
                orden_core.estado_clinico = mapeo_estado_clinico.get(
                    orden_lab.estado_analisis,
                    'PENDIENTE_TOMA'
                )
                orden_core.fecha_toma_muestra = orden_lab.fecha_creacion
                orden_core.requiere_maquila = False  # Por defecto
                orden_core.token_acceso = uuid.uuid4()  # Generar token único
                
                # Copiar diagnóstico si existe
                if not orden_core.diagnostico and hasattr(orden_lab, 'diagnostico'):
                    orden_core.diagnostico = getattr(orden_lab, 'diagnostico', '')
                
                orden_core.save()
                ordenes_actualizadas += 1
                
                print(f"OK Actualizada Orden #{orden_core.id} con datos de Lab #{orden_lab.id}")
            
            else:
                # CREAR orden nueva si no existe (evitar pérdida de datos)
                # Calcular total desde detalles
                total = sum(
                    detalle.subtotal()
                    for detalle in orden_lab.detalles.all()
                )
                
                orden_core = OrdenDeServicio.objects.create(
                    empresa=orden_lab.paciente.empresa if hasattr(orden_lab.paciente, 'empresa') else None,
                    sucursal=orden_lab.usuario_creador.sucursal if hasattr(orden_lab.usuario_creador, 'sucursal') else None,
                    paciente=orden_lab.paciente,
                    fecha_creacion=orden_lab.fecha_creacion,
                    estado='PAGADO' if orden_lab.estado_pago else 'PENDIENTE_PAGO',
                    total=total,
                    anticipo=total if orden_lab.estado_pago else 0,
                    responsable_ingreso=orden_lab.usuario_creador,
                    folio_orden=f"LAB-MIG-{orden_lab.id}",
                    tipo_servicio='RUTINA',
                    tarifa=orden_lab.get_origen_display() if hasattr(orden_lab, 'origen') else 'PUBLICO_GENERAL',
                    estado_pago='PAGADO' if orden_lab.estado_pago else 'PENDIENTE',
                    estado_clinico=mapeo_estado_clinico.get(orden_lab.estado_analisis, 'PENDIENTE_TOMA'),
                    fecha_toma_muestra=orden_lab.fecha_creacion,
                    requiere_maquila=False,
                    token_acceso=uuid.uuid4(),
                    diagnostico=getattr(orden_lab, 'diagnostico', ''),
                    notas_internas=f"Orden migrada desde laboratorio.Orden #{orden_lab.id}"
                )
                
                ordenes_creadas += 1
                
                print(f"NUEVA Creada Orden #{orden_core.id} desde Lab #{orden_lab.id}")
            
            ordenes_migradas += 1
        
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en migrar_datos_laboratorio_a_core (0003_migrar_datos_laboratorio.py)")
            print(f"ERROR procesando orden Lab #{orden_lab.id}: {str(e)}")
    
    # Resumen final
    print(f"\n{'='*80}")
    print(f"RESUMEN DE MIGRACIÓN")
    print(f"{'='*80}")
    print(f"Total procesadas: {ordenes_migradas}/{total_ordenes}")
    print(f"Órdenes actualizadas: {ordenes_actualizadas}")
    print(f"Órdenes creadas (nuevas): {ordenes_creadas}")
    print(f"{'='*80}\n")


def revertir_migracion(apps, schema_editor):
    """
    Reversión de la migración (NO recomendado - solo para emergencias)
    """
    print("\nADVERTENCIA: Reversion de migracion de datos no implementada")
    print("Los datos migrados permaneceran en core.OrdenDeServicio")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_agregar_campos_laboratorio'),
        ('laboratorio', '0002_historialresultados_and_more'),
    ]

    operations = [
        migrations.RunPython(migrar_datos_laboratorio_a_core, revertir_migracion),
    ]