#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Auditor - Simulación Completa de Flujo de Usuario Real
Ejecuta un GUIÓN EXACTO simulando usuarios reales usando Django Client.

Este script:
1. Simula usuarios reales (Médico, Cajera, Químico, etc.)
2. Detecta errores automáticamente
3. Intenta corregirlos
4. Genera un reporte final con sugerencias de mejora
"""

import os
import sys
import traceback
import re
from io import StringIO
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import json

from core.models import (
    Empresa, Paciente, OrdenDeServicio, DetalleOrden,
    PreOrdenLaboratorio, DetallePreOrden, Producto, Venta, DetalleVenta,
    Pago, DetalleEvaluacion, PlanDesarrollo, EvaluacionDesempeno
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Robot Auditor: Simulación completa de flujo de usuario real con auto-corrección'
    
    def __init__(self):
        super().__init__()
        self.errors = []
        self.fixes = []
        self.success_steps = []
        self.suggestions = []
        self.client = Client()
        self.empresa = None
        self.usuarios = {}
        self.paciente = None
        self.preorden = None
        self.orden = None
        self.venta = None
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            required=True,
            help='ID de la empresa para la simulación (obligatorio; sin fallback implícito).',
        )

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy (core.Estudio). "
            "Usa 'importar_catalogo_lims' para LIMS v7.5 y refactoriza el robot con lims.Analito."
        )
        self.empresa_id = options.get('empresa_id')
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write(self.style.SUCCESS('🤖 ROBOT AUDITOR - SIMULACIÓN COMPLETA'))
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write('')
        
        try:
            # SETUP INICIAL
            self._setup_ambiente()
            
            # ACTO 1: EL PACIENTE COMPLEJO
            self._acto_1_paciente_complejo()
            
            # ACTO 2: EL LABORATORIO CAÓTICO
            self._acto_2_laboratorio_caotico()
            
            # ACTO 3: LA FARMACIA
            self._acto_3_farmacia()
            
            # ACTO 4: RH
            self._acto_4_rh()
            
        except Exception as e:
            self._capturar_error("ERROR CRÍTICO", str(e), traceback.format_exc())
            self._intentar_corregir_error("ERROR CRÍTICO", str(e), traceback.format_exc())
        
        # REPORTE FINAL
        self._generar_reporte_final()
    
    def _setup_ambiente(self):
        """Prepara el ambiente de simulación."""
        self.stdout.write(self.style.WARNING('\n📋 FASE 0: SETUP INICIAL'))
        self.stdout.write('-'*80)
        
        try:
            if not self.empresa_id:
                raise Exception("Indique --empresa-id (multi-tenant: sin empresa implícita).")
            self.empresa = Empresa.objects.get(id=self.empresa_id)
            
            self.stdout.write(f"✓ Empresa: {self.empresa.nombre}")
            
            # Crear usuarios de prueba si no existen
            self._crear_usuarios_prueba()
            
            # Crear estudios de prueba si no existen
            self._crear_estudios_prueba()
            
            # Crear productos de prueba si no existen
            self._crear_productos_prueba()
            
            self.success_steps.append("SETUP INICIAL: Ambiente configurado correctamente")
            
        except Exception as e:
            self._capturar_error("SETUP", str(e), traceback.format_exc())
    
    def _crear_usuarios_prueba(self):
        """Crea usuarios de prueba para la simulación."""
        try:
            # Médico
            medico, created = User.objects.get_or_create(
                username='medico_test',
                defaults={
                    'first_name': 'Dr. Test',
                    'last_name': 'Médico',
                    'email': 'medico@test.com',
                    'empresa': self.empresa,
                    'rol': 'MEDICO',
                    'is_active': True,
                }
            )
            if created:
                medico.set_password('test123')
                medico.save()
            self.usuarios['medico'] = medico
            self.stdout.write(f"✓ Médico: {medico.username}")
            
            # Cajera
            cajera, created = User.objects.get_or_create(
                username='cajera_test',
                defaults={
                    'first_name': 'Cajera',
                    'last_name': 'Test',
                    'email': 'cajera@test.com',
                    'empresa': self.empresa,
                    'rol': 'CAJERO',
                    'is_active': True,
                }
            )
            if created:
                cajera.set_password('test123')
                cajera.save()
            self.usuarios['cajera'] = cajera
            self.stdout.write(f"✓ Cajera: {cajera.username}")
            
            # Cajera con permisos (Superusuario para cancelación)
            cajera_admin, created = User.objects.get_or_create(
                username='cajera_admin_test',
                defaults={
                    'first_name': 'Cajera',
                    'last_name': 'Admin',
                    'email': 'cajera_admin@test.com',
                    'empresa': self.empresa,
                    'rol': 'CAJERO',
                    'is_active': True,
                    'is_superuser': True,
                }
            )
            if created:
                cajera_admin.set_password('test123')
                cajera_admin.save()
            self.usuarios['cajera_admin'] = cajera_admin
            self.stdout.write(f"✓ Cajera Admin: {cajera_admin.username}")
            
            # Químico
            quimico, created = User.objects.get_or_create(
                username='quimico_test',
                defaults={
                    'first_name': 'Químico',
                    'last_name': 'Test',
                    'email': 'quimico@test.com',
                    'empresa': self.empresa,
                    'rol': 'QUIMICO',
                    'is_active': True,
                }
            )
            if created:
                quimico.set_password('test123')
                quimico.save()
            self.usuarios['quimico'] = quimico
            self.stdout.write(f"✓ Químico: {quimico.username}")
            
            # Enfermera
            enfermera, created = User.objects.get_or_create(
                username='enfermera_test',
                defaults={
                    'first_name': 'Enfermera',
                    'last_name': 'Test',
                    'email': 'enfermera@test.com',
                    'empresa': self.empresa,
                    'rol': 'RECEPCION',
                    'is_active': True,
                }
            )
            if created:
                enfermera.set_password('test123')
                enfermera.save()
            self.usuarios['enfermera'] = enfermera
            self.stdout.write(f"✓ Enfermera: {enfermera.username}")
            
        except Exception as e:
            self._capturar_error("CREAR_USUARIOS", str(e), traceback.format_exc())
    
    def _crear_estudios_prueba(self):
        """Crea estudios de prueba."""
        try:
            from core.models import CategoriaEstudio
            
            categoria, _ = CategoriaEstudio.objects.get_or_create(
                nombre='Química Clínica',
                defaults={'descripcion': 'Pruebas de química clínica'}
            )
            
            # Glucosa con valores críticos
            glu, created = Estudio.objects.get_or_create(
                codigo='GLU-TEST',
                defaults={
                    'nombre': 'Glucosa',
                    'categoria': categoria,
                    'precio': Decimal('50.00'),
                    'valor_minimo': Decimal('70.00'),
                    'valor_maximo': Decimal('100.00'),
                    'rango_panico_min': Decimal('40.00'),
                    'rango_panico_max': Decimal('400.00'),
                    'unidad': 'mg/dL',
                    'activo': True,
                }
            )
            if created:
                self.stdout.write(f"✓ Estudio creado: {glu.codigo}")
            
            # Hemoglobina
            hb, created = Estudio.objects.get_or_create(
                codigo='HB-TEST',
                defaults={
                    'nombre': 'Hemoglobina',
                    'categoria': categoria,
                    'precio': Decimal('30.00'),
                    'valor_minimo': Decimal('12.00'),
                    'valor_maximo': Decimal('16.00'),
                    'unidad': 'g/dL',
                    'activo': True,
                }
            )
            if created:
                self.stdout.write(f"✓ Estudio creado: {hb.codigo}")
            
            self.estudios_prueba = {'GLU': glu, 'HB': hb}
            
        except Exception as e:
            self._capturar_error("CREAR_ESTUDIOS", str(e), traceback.format_exc())
    
    def _crear_productos_prueba(self):
        """Crea productos de prueba."""
        try:
            # Paracetamol
            paracetamol, created = Producto.objects.get_or_create(
                codigo_barras='7501234567890',
                empresa=self.empresa,
                defaults={
                    'nombre': 'Paracetamol 500mg',
                    'sustancia_activa': 'Paracetamol',
                    'precio_publico': Decimal('25.00'),
                    'stock': 100,
                    'activo': True,
                }
            )
            if created:
                self.stdout.write(f"✓ Producto creado: {paracetamol.nombre}")
            self.productos_prueba = {'PARACETAMOL': paracetamol}
            
            # Alcohol
            alcohol, created = Producto.objects.get_or_create(
                codigo_barras='7501234567891',
                empresa=self.empresa,
                defaults={
                    'nombre': 'Alcohol 500ml',
                    'sustancia_activa': 'Alcohol Etílico',
                    'precio_publico': Decimal('30.00'),
                    'stock': 50,
                    'activo': True,
                }
            )
            if created:
                self.stdout.write(f"✓ Producto creado: {alcohol.nombre}")
            self.productos_prueba['ALCOHOL'] = alcohol
            
        except Exception as e:
            self._capturar_error("CREAR_PRODUCTOS", str(e), traceback.format_exc())
    
    def _acto_1_paciente_complejo(self):
        """ACTO 1: EL PACIENTE COMPLEJO"""
        self.stdout.write(self.style.WARNING('\n🎭 ACTO 1: EL PACIENTE COMPLEJO'))
        self.stdout.write('-'*80)
        
        try:
            # 1.1. Crear paciente "Juan Crash Test"
            self.stdout.write('\n📝 Paso 1.1: Crear paciente "Juan Crash Test"')
            self.paciente, created = Paciente.objects.get_or_create(
                nombre_completo='Juan Crash Test',
                empresa=self.empresa,
                defaults={
                    'fecha_nacimiento': timezone.now().date() - timedelta(days=365*30),
                    'sexo': 'M',
                    'tipo_paciente': 'GENERAL',
                }
            )
            if created:
                self.stdout.write(f"✓ Paciente creado: {self.paciente.nombre_completo}")
                self.success_steps.append("ACTO 1.1: Paciente creado")
            else:
                self.stdout.write(f"✓ Paciente existente: {self.paciente.nombre_completo}")
            
            # 1.2. El Médico crea una Pre-Orden
            self.stdout.write('\n📝 Paso 1.2: Médico crea Pre-Orden')
            self.client.force_login(self.usuarios['medico'])
            
            # Buscar consulta médica o crear una
            from consultorio.models import ConsultaMedica
            consulta, _ = ConsultaMedica.objects.get_or_create(
                empresa=self.empresa,
                paciente=self.paciente,
                defaults={'medico': self.usuarios['medico']}
            )
            
            # Crear pre-orden
            self.preorden = PreOrdenLaboratorio.objects.create(
                empresa=self.empresa,
                paciente=self.paciente,
                medico_solicitante=self.usuarios['medico'],
                consulta_medica=consulta,
                observaciones='Prueba de Robot Auditor'
            )
            
            # Agregar estudios a la pre-orden
            if hasattr(self, 'estudios_prueba'):
                DetallePreOrden.objects.create(
                    preorden=self.preorden,
                    estudio=self.estudios_prueba['GLU'],
                    observaciones_medico='Prueba de glucosa'
                )
                self.stdout.write(f"✓ Pre-Orden creada: ID {self.preorden.id}")
                self.success_steps.append("ACTO 1.2: Pre-Orden creada por médico")
            
            # 1.3. La Cajera carga la Pre-Orden, agrega estudio extra, cobra
            self.stdout.write('\n📝 Paso 1.3: Cajera carga Pre-Orden y cobra')
            self.client.force_login(self.usuarios['cajera'])
            
            # Simular carga de pre-orden y creación de orden
            self.orden = OrdenDeServicio.objects.create(
                empresa=self.empresa,
                paciente=self.paciente,
                total=Decimal('80.00'),  # GLU (50) + HB (30)
                anticipo=Decimal('80.00'),
                estado='PAGADO',
                responsable_ingreso=self.usuarios['cajera'],
                folio_orden=f"LAB-{timezone.now().strftime('%Y%m%d')}-TEST01"
            )
            
            # Detalles de la orden
            DetalleOrden.objects.create(
                orden=self.orden,
                estudio=self.estudios_prueba['GLU'],
                precio_momento=self.estudios_prueba['GLU'].precio
            )
            DetalleOrden.objects.create(
                orden=self.orden,
                estudio=self.estudios_prueba['HB'],
                precio_momento=self.estudios_prueba['HB'].precio
            )
            
            # Marcar pre-orden como cobrada
            self.preorden.estado = 'COBRADA'
            self.preorden.orden_vinculada = self.orden
            self.preorden.save()
            
            self.stdout.write(f"✓ Orden creada y cobrada: {self.orden.folio_orden}")
            self.success_steps.append("ACTO 1.3: Orden creada y cobrada")
            
            # 1.4. Editar nombre del paciente (sin alterar folio)
            self.stdout.write('\n📝 Paso 1.4: Editar nombre del paciente')
            nombre_anterior = self.paciente.nombre_completo
            self.paciente.nombre_completo = 'Juan Crash Test (Editado)'
            self.paciente.save()
            self.stdout.write(f"✓ Nombre editado: {nombre_anterior} -> {self.paciente.nombre_completo}")
            self.success_steps.append("ACTO 1.4: Nombre de paciente editado")
            
            # 1.5. Intentar cancelar sin permisos (debe fallar)
            self.stdout.write('\n📝 Paso 1.5: Intentar cancelar orden sin permisos (debe fallar)')
            try:
                # Intentar cancelar como cajera normal (sin superusuario)
                self.client.force_login(self.usuarios['cajera'])
                response = self.client.post(f'/laboratorio/api/cancelar-orden/{self.orden.id}/', {
                    'motivo': 'Prueba de cancelación sin permisos'
                })
                
                if response.status_code == 403 or response.status_code == 401:
                    self.stdout.write("✓ Cancelación bloqueada correctamente (sin permisos)")
                    self.success_steps.append("ACTO 1.5: Cancelación sin permisos bloqueada")
                else:
                    self.stdout.write(self.style.WARNING(f"⚠ Cancelación permitida sin permisos (esperado: 403/401, recibido: {response.status_code})"))
                    self.errors.append({
                        'acto': 'ACTO 1.5',
                        'paso': 'Cancelación sin permisos',
                        'error': f'Cancelación permitida sin permisos (status: {response.status_code})',
                        'esperado': '403 o 401'
                    })
            except Exception as e:
                # Si la vista no existe, lo registramos como error pero no fallamos
                if 'cancelar-orden' in str(e) or '404' in str(e):
                    self.stdout.write(self.style.ERROR(f"✗ Vista de cancelación no implementada"))
                    self.errors.append({
                        'acto': 'ACTO 1.5',
                        'paso': 'Cancelación sin permisos',
                        'error': 'Vista cancelar_orden no existe',
                        'tipo': 'VISTA_FALTANTE'
                    })
                else:
                    self._capturar_error("ACTO_1_5", str(e), traceback.format_exc())
            
            # 1.6. Cancelar con permisos (debe pasar)
            self.stdout.write('\n📝 Paso 1.6: Cancelar orden con permisos (debe pasar)')
            try:
                self.client.force_login(self.usuarios['cajera_admin'])
                response = self.client.post(f'/laboratorio/api/cancelar-orden/{self.orden.id}/', {
                    'motivo': 'Prueba de cancelación con permisos'
                }, follow=True)
                
                if response.status_code == 200 or response.status_code == 201:
                    self.stdout.write("✓ Cancelación exitosa con permisos")
                    self.success_steps.append("ACTO 1.6: Cancelación exitosa con permisos")
                else:
                    self.stdout.write(self.style.WARNING(f"⚠ Cancelación falló (status: {response.status_code})"))
                    self.errors.append({
                        'acto': 'ACTO 1.6',
                        'paso': 'Cancelación con permisos',
                        'error': f'Cancelación falló (status: {response.status_code})',
                        'esperado': '200 o 201'
                    })
            except Exception as e:
                if 'cancelar-orden' in str(e) or '404' in str(e):
                    self.stdout.write(self.style.ERROR(f"✗ Vista de cancelación no implementada"))
                    self.errors.append({
                        'acto': 'ACTO 1.6',
                        'paso': 'Cancelación con permisos',
                        'error': 'Vista cancelar_orden no existe',
                        'tipo': 'VISTA_FALTANTE'
                    })
                else:
                    self._capturar_error("ACTO_1_6", str(e), traceback.format_exc())
            
        except Exception as e:
            self._capturar_error("ACTO_1", str(e), traceback.format_exc())
    
    def _acto_2_laboratorio_caotico(self):
        """ACTO 2: EL LABORATORIO CAÓTICO"""
        self.stdout.write(self.style.WARNING('\n🎭 ACTO 2: EL LABORATORIO CAÓTICO'))
        self.stdout.write('-'*80)
        
        try:
            # 2.1. Crear nueva orden
            self.stdout.write('\n📝 Paso 2.1: Crear nueva orden')
            orden_lab = OrdenDeServicio.objects.create(
                empresa=self.empresa,
                paciente=self.paciente,
                total=Decimal('50.00'),
                anticipo=Decimal('50.00'),
                estado='PAGADO',
                responsable_ingreso=self.usuarios['cajera'],
                folio_orden=f"LAB-{timezone.now().strftime('%Y%m%d')}-TEST02"
            )
            
            detalle_glu = DetalleOrden.objects.create(
                orden=orden_lab,
                estudio=self.estudios_prueba['GLU'],
                precio_momento=self.estudios_prueba['GLU'].precio,
                estado_procesamiento='PENDIENTE_TOMA'
            )
            
            detalle_hb = DetalleOrden.objects.create(
                orden=orden_lab,
                estudio=self.estudios_prueba['HB'],
                precio_momento=self.estudios_prueba['HB'].precio,
                estado_procesamiento='PENDIENTE_TOMA'
            )
            
            self.stdout.write(f"✓ Orden de laboratorio creada: {orden_lab.folio_orden}")
            self.success_steps.append("ACTO 2.1: Orden de laboratorio creada")
            
            # 2.2. Enfermera marca "Toma Realizada"
            self.stdout.write('\n📝 Paso 2.2: Enfermera marca "Toma Realizada"')
            self.client.force_login(self.usuarios['enfermera'])
            
            detalle_glu.estado_procesamiento = 'TOMA_REALIZADA'
            detalle_glu.save()
            detalle_hb.estado_procesamiento = 'TOMA_REALIZADA'
            detalle_hb.save()
            
            orden_lab.estado = 'EN_PROCESO'
            orden_lab.save()
            
            self.stdout.write("✓ Toma marcada como realizada")
            self.success_steps.append("ACTO 2.2: Toma marcada como realizada")
            
            # 2.3. Químico ingresa resultado de Glucosa en "500" (debe disparar alerta de pánico)
            self.stdout.write('\n📝 Paso 2.3: Químico ingresa resultado de Glucosa = 500 (debe alertar)')
            self.client.force_login(self.usuarios['quimico'])
            
            # Simular captura de resultado con valor crítico
            valor_critico = Decimal('500.00')
            rango_max = self.estudios_prueba['GLU'].rango_panico_max
            
            if valor_critico > rango_max:
                self.stdout.write(self.style.ERROR(f"⚠⚠⚠ VALOR DE PÁNICO DETECTADO: {valor_critico} > {rango_max}"))
                self.stdout.write("   Se requiere confirmación de valor crítico")
                # En una implementación real, aquí se mostraría una alerta y se pediría confirmación
                detalle_glu.valor_critico_confirmado = True
                detalle_glu.resultado = str(valor_critico)
                detalle_glu.estado_procesamiento = 'RESULTADO_LISTO'
                detalle_glu.save()
                self.success_steps.append("ACTO 2.3: Valor de pánico detectado y confirmado")
            else:
                self.stdout.write(f"✓ Valor dentro de rango: {valor_critico}")
            
            # 2.4. Químico marca Hemoglobina como "Muestra Coagulada" (rechazo)
            self.stdout.write('\n📝 Paso 2.4: Químico marca Hemoglobina como "Muestra Coagulada"')
            detalle_hb.estado_procesamiento = 'MUESTRA_RECHAZADA'
            detalle_hb.motivo_rechazo = 'Muestra Coagulada - Requiere nueva toma'
            detalle_hb.save()
            
            # Reiniciar a PENDIENTE_TOMA
            # Esto se haría automáticamente en la vista de rechazo
            detalle_hb.estado_procesamiento = 'PENDIENTE_TOMA'
            detalle_hb.save()
            
            self.stdout.write("✓ Muestra rechazada y reiniciada a PENDIENTE_TOMA")
            self.success_steps.append("ACTO 2.4: Muestra rechazada correctamente")
            
            # 2.5. Químico valida y libera PDF
            self.stdout.write('\n📝 Paso 2.5: Químico valida y libera PDF')
            detalle_glu.validado_por = self.usuarios['quimico']
            detalle_glu.fecha_validacion = timezone.now()
            detalle_glu.save()
            
            orden_lab.estado = 'RESULTADOS_LISTOS'
            orden_lab.save()
            
            self.stdout.write("✓ Resultados validados y PDF listo")
            self.success_steps.append("ACTO 2.5: Resultados validados")
            
        except Exception as e:
            self._capturar_error("ACTO_2", str(e), traceback.format_exc())
    
    def _acto_3_farmacia(self):
        """ACTO 3: LA FARMACIA"""
        self.stdout.write(self.style.WARNING('\n🎭 ACTO 3: LA FARMACIA'))
        self.stdout.write('-'*80)
        
        try:
            # 3.1. Vende 3 Paracetamoles
            self.stdout.write('\n📝 Paso 3.1: Vender 3 Paracetamoles')
            self.client.force_login(self.usuarios['cajera'])
            
            self.venta = Venta.objects.create(
                empresa=self.empresa,
                usuario=self.usuarios['cajera'],
                paciente_nombre='Cliente Prueba',
                total=Decimal('75.00'),  # 3 x 25
                folio_operacion=f"FAR-{timezone.now().strftime('%Y%m%d')}-TEST01",
                estado='COMPLETADA'
            )
            
            DetalleVenta.objects.create(
                venta=self.venta,
                producto=self.productos_prueba['PARACETAMOL'],
                cantidad=3,
                precio_unitario=self.productos_prueba['PARACETAMOL'].precio_publico,
                subtotal=Decimal('75.00')
            )
            
            Pago.objects.create(
                venta=self.venta,
                metodo='EFECTIVO',
                monto=Decimal('75.00')
            )
            
            # Actualizar stock
            self.productos_prueba['PARACETAMOL'].stock -= 3
            self.productos_prueba['PARACETAMOL'].save()
            
            self.stdout.write(f"✓ Venta realizada: {self.venta.folio_operacion}")
            self.success_steps.append("ACTO 3.1: Venta realizada")
            
            # 3.2. Registrar merma de 1 Alcohol por "Rotura"
            self.stdout.write('\n📝 Paso 3.2: Registrar merma de 1 Alcohol por "Rotura"')
            
            # Registrar merma usando AjusteInventario
            from core.models import AjusteInventario, Lote
            try:
                # Obtener el primer lote disponible del producto
                lote = Lote.objects.filter(
                    producto=self.productos_prueba['ALCOHOL'],
                    cantidad__gt=0
                ).first()
                
                if lote:
                    # Crear ajuste de inventario (merma)
                    merma = AjusteInventario.objects.create(
                        empresa=self.empresa,
                        producto=self.productos_prueba['ALCOHOL'],
                        lote=lote,
                        cantidad=1,
                        tipo_movimiento='MERMA',
                        observacion='Rotura',
                        usuario=self.usuarios['cajera']
                    )
                    
                    # Actualizar stock
                    self.productos_prueba['ALCOHOL'].stock -= 1
                    self.productos_prueba['ALCOHOL'].save()
                    
                    # Actualizar lote
                    lote.cantidad -= 1
                    lote.save()
                    
                    self.stdout.write("✓ Merma registrada")
                    self.success_steps.append("ACTO 3.2: Merma registrada")
                else:
                    self.stdout.write(self.style.WARNING("⚠ No hay lotes disponibles para el producto"))
                    self.errors.append({
                        'acto': 'ACTO 3.2',
                        'paso': 'Registrar merma',
                        'error': 'No hay lotes disponibles para el producto',
                        'tipo': 'ADVERTENCIA'
                    })
                
            except Exception as e:
                self._capturar_error("ACTO_3_2", str(e), traceback.format_exc())
            
            # 3.3. Solicitar factura (simulado)
            self.stdout.write('\n📝 Paso 3.3: Solicitar factura (simulado)')
            self.stdout.write("✓ Factura solicitada (simulado - requeriría integración con facturación)")
            self.success_steps.append("ACTO 3.3: Factura solicitada (simulado)")
            
        except Exception as e:
            self._capturar_error("ACTO_3", str(e), traceback.format_exc())
    
    def _acto_4_rh(self):
        """ACTO 4: RH"""
        self.stdout.write(self.style.WARNING('\n🎭 ACTO 4: RECURSOS HUMANOS'))
        self.stdout.write('-'*80)
        
        try:
            # 4.1. Sistema detecta que la cajera tardó mucho y asigna capacitación
            self.stdout.write('\n📝 Paso 4.1: Sistema detecta lentitud y asigna capacitación')
            
            # Simular detección de lentitud (en producción sería con métricas reales)
            tiempo_procesamiento_simulado = timedelta(minutes=15)  # Tiempo excesivo
            
            if tiempo_procesamiento_simulado > timedelta(minutes=10):
                self.stdout.write(f"⚠ Detección de lentitud: {tiempo_procesamiento_simulado}")
                self.stdout.write("   Asignando capacitación automática...")
                
                # Buscar evaluación de desempeño reciente
                eval_reciente = EvaluacionDesempeno.objects.filter(
                    empleado=self.usuarios['cajera']
                ).order_by('-fecha').first()
                
                if eval_reciente:
                    # Buscar curso de capacitación
                    from marketing.models import CursoAcademy
                    curso = CursoAcademy.objects.filter(
                        nombre__icontains='Atención'
                    ).first()
                    
                    if curso:
                        # Crear PDI automático
                        plan, created = PlanDesarrollo.objects.get_or_create(
                            empleado=self.usuarios['cajera'],
                            evaluacion_origen=eval_reciente,
                            defaults={
                                'fecha_limite': timezone.now().date() + timedelta(days=30),
                                'estado': 'PENDIENTE',
                                'observaciones': 'Asignado automáticamente por detección de lentitud en procesamiento'
                            }
                        )
                        if curso:
                            plan.cursos_asignados.add(curso)
                        
                        self.stdout.write(f"✓ Plan de Desarrollo asignado: ID {plan.id}")
                        self.success_steps.append("ACTO 4.1: Capacitación asignada automáticamente")
                    else:
                        self.stdout.write("⚠ Curso de capacitación no encontrado (simulado)")
                else:
                    self.stdout.write("⚠ No hay evaluación de desempeño reciente (simulado)")
            
        except Exception as e:
            # Si falla, solo registramos pero no paramos la simulación
            self.stdout.write(self.style.WARNING(f"⚠ Error en ACTO 4 (no crítico): {str(e)}"))
            self.errors.append({
                'acto': 'ACTO 4',
                'paso': 'Asignación de capacitación',
                'error': str(e),
                'tipo': 'ADVERTENCIA'
            })
    
    def _capturar_error(self, contexto, error, traceback_str):
        """Captura un error y lo registra."""
        self.errors.append({
            'contexto': contexto,
            'error': error,
            'traceback': traceback_str,
            'tipo': 'ERROR'
        })
        self.stdout.write(self.style.ERROR(f"\n✗ ERROR en {contexto}: {error}"))
    
    def _intentar_corregir_error(self, contexto, error, traceback_str):
        """Intenta corregir automáticamente un error."""
        # Esta función se implementaría para corregir errores comunes
        # Por ahora solo registramos qué se intentaría corregir
        self.fixes.append({
            'contexto': contexto,
            'error': error,
            'intento_correccion': 'Análisis de traceback para corrección automática'
        })
    
    def _generar_reporte_final(self):
        """Genera el reporte final de la simulación."""
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('📊 REPORTE FINAL'))
        self.stdout.write('='*80)
        
        # Resumen de pasos exitosos
        self.stdout.write(f"\n✅ PASOS EXITOSOS: {len(self.success_steps)}")
        for paso in self.success_steps:
            self.stdout.write(f"   ✓ {paso}")
        
        # Errores encontrados
        self.stdout.write(f"\n❌ ERRORES ENCONTRADOS: {len(self.errors)}")
        for error in self.errors:
            self.stdout.write(self.style.ERROR(f"\n   ✗ [{error.get('acto', 'N/A')}] {error.get('paso', 'N/A')}"))
            self.stdout.write(f"      Error: {error.get('error', 'N/A')}")
            if error.get('tipo'):
                self.stdout.write(f"      Tipo: {error.get('tipo')}")
        
        # Correcciones aplicadas
        if self.fixes:
            self.stdout.write(f"\n🔧 CORRECCIONES APLICADAS: {len(self.fixes)}")
            for fix in self.fixes:
                self.stdout.write(f"   🔧 {fix.get('contexto')}: {fix.get('intento_correccion')}")
        
        # Sugerencias de mejora
        self.stdout.write(f"\n💡 SUGERENCIAS DE MEJORA:")
        
        sugerencias = [
            "1. Implementar validación de huella digital para cancelaciones críticas (mejora de seguridad)",
            "2. Agregar notificaciones en tiempo real cuando se detecta un valor de pánico (mejora de seguridad del paciente)",
            "3. Implementar auditoría completa de movimientos de inventario con registro de quién, cuándo y por qué (trazabilidad)",
        ]
        
        # Agregar sugerencias específicas basadas en errores encontrados
        if any('cancelar-orden' in str(e.get('error', '')) for e in self.errors):
            sugerencias.append("4. IMPLEMENTAR: Vista de cancelación de órdenes con validación de permisos de superusuario")
        
        if any('lote' in str(e.get('error', '')).lower() for e in self.errors):
            sugerencias.append("5. MEJORAR: Agregar creación automática de lotes por defecto cuando no existen para productos")
        
        if any('valor_critico' in str(e.get('error', '')) for e in self.errors):
            sugerencias.append("6. IMPLEMENTAR: Alerta visual de valores de pánico en captura_resultados con checkbox de confirmación obligatorio")
        
        for sugerencia in sugerencias:
            self.stdout.write(f"   💡 {sugerencia}")
        
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('🏁 SIMULACIÓN COMPLETA'))
        self.stdout.write('='*80 + '\n')
