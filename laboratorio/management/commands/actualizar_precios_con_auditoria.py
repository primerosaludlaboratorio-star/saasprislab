"""
Comando de Management: Actualizar Precios con Auditoría Forense

Este comando actualiza los precios de Estudios y Perfiles de Laboratorio
desde un archivo CSV, generando logs de auditoría inalterables para cada cambio.

Formato CSV esperado:
- Para Estudios: codigo, precio_nuevo
- Para Perfiles: nombre_perfil, precio_nuevo

Ejemplo:
codigo,precio_nuevo,tipo
QUI-001,150.50,estudio
Química Básica,380.00,perfil
"""

import csv
import hashlib
import json
import os
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from laboratorio.models import Estudio, PerfilLaboratorio
from core.models import Empresa, AuditLog, Usuario


class Command(BaseCommand):
    help = 'Actualiza precios de Estudios y Perfiles desde CSV, generando logs de auditoría'

    def add_arguments(self, parser):
        parser.add_argument(
            'archivo_csv',
            type=str,
            help='Ruta al archivo CSV con los nuevos precios'
        )
        parser.add_argument(
            '--empresa',
            type=str,
            default='PRISLAB',
            help='Nombre de la empresa (default: PRISLAB)'
        )
        parser.add_argument(
            '--usuario',
            type=str,
            default=None,
            help='Username del usuario que realiza la actualización (default: None)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular actualización sin guardar cambios (no genera logs)'
        )

    def calcular_hash_auditoria(self, datos):
        """
        Calcula hash SHA-256 de los datos de auditoría para prevenir alteraciones.
        """
        datos_str = json.dumps(datos, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(datos_str.encode('utf-8')).hexdigest()

    def crear_log_auditoria(self, empresa, usuario, accion, modelo, objeto_id, datos_anterior, datos_nuevo, sucursal=None):
        """
        Crea un log de auditoría inalterable para un cambio de precio.
        """
        datos_auditoria = {
            'accion': accion,
            'modelo': modelo,
            'objeto_id': str(objeto_id),
            'fecha': timezone.now().isoformat(),
            'datos_anterior': datos_anterior,
            'datos_nuevo': datos_nuevo,
        }
        
        hash_verificacion = self.calcular_hash_auditoria(datos_auditoria)
        
        return AuditLog.objects.create(
            empresa=empresa,
            sucursal=sucursal,
            usuario=usuario,
            accion=accion,
            modelo_afectado=modelo,
            objeto_id=str(objeto_id),
            datos_anteriores=datos_anterior,
            datos_nuevos=datos_nuevo,
            hash_verificacion=hash_verificacion,
            ip_address=None,  # Se puede mejorar obteniendo la IP real
            user_agent='Management Command: actualizar_precios_con_auditoria'
        )

    def actualizar_precio_estudio(self, estudio, precio_nuevo, empresa, usuario, dry_run=False):
        """
        Actualiza el precio de un estudio y genera log de auditoría.
        """
        precio_anterior = estudio.precio_base
        
        # Validar precisión decimal (máximo 2 decimales)
        try:
            precio_nuevo_decimal = Decimal(str(precio_nuevo))
            # Redondear a 2 decimales para garantizar precisión
            precio_nuevo_decimal = precio_nuevo_decimal.quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError) as e:
            return False, f"Precio invalido: {precio_nuevo} - {str(e)}"
        
        # Si el precio no cambió, no hacer nada
        if precio_anterior == precio_nuevo_decimal:
            return True, "Precio sin cambios"
        
        datos_anterior = {
            'precio_base': str(precio_anterior),
            'nombre': estudio.nombre,
            'codigo': estudio.codigo or '',
        }
        
        datos_nuevo = {
            'precio_base': str(precio_nuevo_decimal),
            'nombre': estudio.nombre,
            'codigo': estudio.codigo or '',
        }
        
        if not dry_run:
            # Actualizar precio
            estudio.precio_base = precio_nuevo_decimal
            estudio.save()
            
            # Crear log de auditoría
            self.crear_log_auditoria(
                empresa=empresa,
                usuario=usuario,
                accion=AuditLog.ACCION_UPDATE,
                modelo='Estudio',
                objeto_id=estudio.id,
                datos_anterior=datos_anterior,
                datos_nuevo=datos_nuevo
            )
        
        cambio = precio_nuevo_decimal - precio_anterior
        porcentaje = (cambio / precio_anterior * 100) if precio_anterior > 0 else 0
        
        return True, f"${precio_anterior:.2f} -> ${precio_nuevo_decimal:.2f} ({cambio:+.2f}, {porcentaje:+.2f}%)"

    def actualizar_precio_perfil(self, perfil, precio_nuevo, empresa, usuario, dry_run=False):
        """
        Actualiza el precio de un perfil y genera log de auditoría.
        """
        precio_anterior = perfil.precio
        
        # Validar precisión decimal (máximo 2 decimales)
        try:
            precio_nuevo_decimal = Decimal(str(precio_nuevo))
            precio_nuevo_decimal = precio_nuevo_decimal.quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError) as e:
            return False, f"Precio inválido: {precio_nuevo} - {str(e)}"
        
        # Si el precio no cambió, no hacer nada
        if precio_anterior == precio_nuevo_decimal:
            return True, "Precio sin cambios"
        
        datos_anterior = {
            'precio': str(precio_anterior),
            'nombre': perfil.nombre,
            'area_pertenencia': perfil.area_pertenencia.nombre if perfil.area_pertenencia else '',
            'cantidad_estudios': perfil.pruebas.count(),
        }
        
        datos_nuevo = {
            'precio': str(precio_nuevo_decimal),
            'nombre': perfil.nombre,
            'area_pertenencia': perfil.area_pertenencia.nombre if perfil.area_pertenencia else '',
            'cantidad_estudios': perfil.pruebas.count(),
        }
        
        if not dry_run:
            # Actualizar precio
            perfil.precio = precio_nuevo_decimal
            perfil.save()
            
            # Crear log de auditoría
            self.crear_log_auditoria(
                empresa=empresa,
                usuario=usuario,
                accion=AuditLog.ACCION_UPDATE,
                modelo='PerfilLaboratorio',
                objeto_id=perfil.id,
                datos_anterior=datos_anterior,
                datos_nuevo=datos_nuevo
            )
        
        cambio = precio_nuevo_decimal - precio_anterior
        porcentaje = (cambio / precio_anterior * 100) if precio_anterior > 0 else 0
        
        return True, f"${precio_anterior:.2f} -> ${precio_nuevo_decimal:.2f} ({cambio:+.2f}, {porcentaje:+.2f}%)"

    def handle(self, *args, **options):
        archivo_csv = options['archivo_csv']
        empresa_nombre = options['empresa']
        usuario_username = options['usuario']
        dry_run = options['dry_run']
        
        # Validar archivo
        if not os.path.exists(archivo_csv):
            self.stdout.write(self.style.ERROR(f'[ERROR] El archivo "{archivo_csv}" no existe.'))
            return
        
        # Obtener empresa
        try:
            empresa = Empresa.objects.get(nombre=empresa_nombre)
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'[ERROR] La empresa "{empresa_nombre}" no existe.'))
            return
        
        # Obtener usuario (opcional)
        usuario = None
        if usuario_username:
            try:
                usuario = Usuario.objects.get(username=usuario_username)
            except Usuario.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'[ADVERTENCIA] Usuario "{usuario_username}" no encontrado. Continuando sin usuario.'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY-RUN] Modo de simulación activado. No se guardarán cambios.\n'))
        
        self.stdout.write(self.style.SUCCESS(f'\n[INICIO] Actualizando precios para {empresa.nombre}...\n'))
        
        # Estadísticas
        estudios_actualizados = 0
        perfiles_actualizados = 0
        estudios_no_encontrados = []
        perfiles_no_encontrados = []
        errores = []
        
        try:
            with transaction.atomic():
                # Leer CSV línea por línea para manejar múltiples encabezados
                with open(archivo_csv, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    headers = None
                    modo_actual = None
                    
                    for idx, row in enumerate(reader, start=1):
                        try:
                            # Si es la primera fila o detectamos un nuevo encabezado
                            if not headers or (len(row) > 0 and row[0].lower() in ['codigo', 'nombre_perfil']):
                                headers = row
                                # Determinar modo por el primer campo del encabezado
                                if headers and headers[0].lower() == 'codigo':
                                    modo_actual = 'estudio'
                                elif headers and headers[0].lower() == 'nombre_perfil':
                                    modo_actual = 'perfil'
                                continue  # Saltar fila de encabezado
                            
                            if not row or len(row) < 2:
                                continue  # Fila vacía
                            
                            # Convertir a diccionario
                            row_dict = dict(zip(headers, row))
                            precio_str = row_dict.get('precio_nuevo', '').strip() or row_dict.get('precio', '').strip()
                            
                            if modo_actual == 'estudio':
                                codigo = row_dict.get('codigo', '').strip()
                                if not codigo or codigo.lower() in ['codigo', 'nombre_perfil']:
                                    continue
                                
                                try:
                                    estudio = Estudio.objects.get(codigo=codigo)
                                    exito, mensaje = self.actualizar_precio_estudio(
                                        estudio, precio_str, empresa, usuario, dry_run
                                    )
                                    if exito:
                                        if "sin cambios" not in mensaje.lower():
                                            estudios_actualizados += 1
                                            self.stdout.write(self.style.SUCCESS(f'  [OK] {estudio.nombre} ({codigo}): {mensaje}'))
                                    else:
                                        errores.append(f"Fila {idx} ({codigo}): {mensaje}")
                                except Estudio.DoesNotExist:
                                    estudios_no_encontrados.append(codigo)
                                    self.stdout.write(self.style.WARNING(f'  [NO ENCONTRADO] Estudio con código: {codigo}'))
                            
                            elif modo_actual == 'perfil':
                                nombre_perfil = row_dict.get('nombre_perfil', '').strip() or row_dict.get('nombre', '').strip()
                                if not nombre_perfil or nombre_perfil.lower() in ['codigo', 'nombre_perfil', 'nombre']:
                                    continue
                                
                                try:
                                    perfil = PerfilLaboratorio.objects.get(nombre=nombre_perfil)
                                    exito, mensaje = self.actualizar_precio_perfil(
                                        perfil, precio_str, empresa, usuario, dry_run
                                    )
                                    if exito:
                                        if "sin cambios" not in mensaje.lower():
                                            perfiles_actualizados += 1
                                            self.stdout.write(self.style.SUCCESS(f'  [OK] {perfil.nombre}: {mensaje}'))
                                    else:
                                        errores.append(f"Fila {idx} ({nombre_perfil}): {mensaje}")
                                except PerfilLaboratorio.DoesNotExist:
                                    perfiles_no_encontrados.append(nombre_perfil)
                                    self.stdout.write(self.style.WARNING(f'  [NO ENCONTRADO] Perfil: {nombre_perfil}'))
                            
                        except Exception as e:
                            errores.append(f"Fila {idx}: {str(e)}")
                            continue
                                
                        except Exception as e:
                            errores.append(f"Fila {idx}: {str(e)}")
                            continue
                
                # Si es dry-run, hacer rollback manual
                if dry_run:
                    transaction.set_rollback(True)
                
                # Resumen final
                self.stdout.write(self.style.SUCCESS('\n' + '='*60))
                self.stdout.write(self.style.SUCCESS('[COMPLETADO] ACTUALIZACIÓN DE PRECIOS FINALIZADA'))
                self.stdout.write(self.style.SUCCESS('='*60))
                self.stdout.write(f'\nResumen:')
                self.stdout.write(f'   - Estudios actualizados: {estudios_actualizados}')
                self.stdout.write(f'   - Perfiles actualizados: {perfiles_actualizados}')
                self.stdout.write(f'   - Estudios no encontrados: {len(estudios_no_encontrados)}')
                self.stdout.write(f'   - Perfiles no encontrados: {len(perfiles_no_encontrados)}')
                self.stdout.write(f'   - Errores: {len(errores)}')
                
                if estudios_no_encontrados:
                    self.stdout.write(self.style.WARNING(f'\nEstudios no encontrados: {", ".join(estudios_no_encontrados[:10])}'))
                if perfiles_no_encontrados:
                    self.stdout.write(self.style.WARNING(f'\nPerfiles no encontrados: {", ".join(perfiles_no_encontrados)}'))
                if errores:
                    self.stdout.write(self.style.ERROR(f'\nErrores:'))
                    for error in errores[:10]:
                        self.stdout.write(self.style.ERROR(f'   - {error}'))
                
                self.stdout.write(self.style.SUCCESS(f'\n[EXITO] Actualización completada con auditoría!\n'))
                
        except transaction.TransactionManagementError:
            # Dry-run: transacción revertida intencionalmente
            self.stdout.write(self.style.WARNING('\n[DRY-RUN] Transacción revertida. No se guardaron cambios.\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Error durante la actualización: {str(e)}'))
            self.stdout.write(self.style.ERROR('   La transacción ha sido revertida.'))
            raise
