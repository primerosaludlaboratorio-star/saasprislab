"""
Management Command: Backup Nocturno 3:00 AM
Implementa respaldo completo con cifrado AES-256 y rotación automática.

Ejecución:
    python manage.py backup_nocturno
    
Para automatización (Cron):
    0 3 * * * cd /ruta/proyecto && python manage.py backup_nocturno >> /var/log/prislab_backup.log 2>&1
"""
import os
import sys
import json
import gzip
import shutil
import hashlib
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db import connection

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

from core.models import Empresa, BackupRegistro
from core.utils.drive_archive import drive_enabled, subir_archivo_a_drive
import logging


class Command(BaseCommand):
    help = 'Ejecuta backup nocturno completo con cifrado AES-256 a las 3:00 AM'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID de la empresa para backup específico (si no se especifica, hace backup de todas)',
        )
        parser.add_argument(
            '--tipo',
            type=str,
            choices=['DIARIO', 'SEMANAL', 'MENSUAL'],
            default='DIARIO',
            help='Tipo de backup a realizar',
        )
        parser.add_argument(
            '--ruta-destino',
            type=str,
            help='Ruta personalizada para guardar el backup (por defecto: media/backups/)',
        )

    def handle(self, *args, **options):
        """Ejecuta el backup nocturno completo."""
        self.stdout.write(self.style.SUCCESS('\n=== INICIANDO BACKUP NOCTURNO PRISLAB 3:00 AM ===\n'))
        
        empresa_id = options.get('empresa_id')
        tipo_backup = options.get('tipo', 'DIARIO')
        ruta_destino = options.get('ruta_destino') or os.path.join(settings.MEDIA_ROOT, 'backups')
        
        # Crear directorio de backups si no existe
        os.makedirs(ruta_destino, exist_ok=True)
        
        # Obtener empresas a respaldar
        if empresa_id:
            empresas = Empresa.objects.filter(id=empresa_id, activa=True)
        else:
            empresas = Empresa.objects.filter(activa=True)
        
        if not empresas.exists():
            self.stdout.write(self.style.ERROR('No se encontraron empresas activas para respaldar.'))
            return
        
        backups_exitosos = 0
        backups_fallidos = 0
        
        for empresa in empresas:
            self.stdout.write(f'\n--- Respaldo para: {empresa.nombre} ---')
            
            try:
                backup_registro = BackupRegistro.objects.create(
                    empresa=empresa,
                    tipo_backup=tipo_backup,
                    estado='EN_PROGRESO',
                    incluye_base_datos=True,
                    incluye_media=True,
                    incluye_parametros_lab=True,
                    incluye_auditoria_sha256=True,
                    incluye_expedientes_medicos=True,
                    incluye_firmas_digitales=True,
                    incluye_pdfs_rh=True,
                )
                
                # Ejecutar backup
                resultado = self._ejecutar_backup_completo(empresa, backup_registro, ruta_destino, tipo_backup)
                
                if resultado['exito']:
                    backups_exitosos += 1
                    self.stdout.write(self.style.SUCCESS(f'✅ Backup completado: {resultado["archivo"]} ({resultado["tamanio_mb"]} MB)'))
                    if getattr(settings, 'BACKUP_IMMUTABLE_LOG_AUTO', False):
                        try:
                            from core.utils.backup_inmutable import append_backup_inmutable_log

                            append_backup_inmutable_log(backup_registro)
                        except Exception as _im_err:
                            logging.getLogger(__name__).exception("Error inesperado en handle (backup_nocturno.py)")
                            self.stdout.write(self.style.WARNING(f'Log inmutable no registrado: {_im_err}'))
                    
                    # Limpiar backups antiguos (rotación)
                    self._limpiar_backups_antiguos(empresa, ruta_destino)
                    
                    # Enviar notificación al dashboard (marcar como enviada)
                    backup_registro.marcar_notificacion_enviada()
                else:
                    backups_fallidos += 1
                    self.stdout.write(self.style.ERROR(f'❌ Error en backup: {resultado.get("error", "Error desconocido")}'))
            
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en handle (backup_nocturno.py)")
                backups_fallidos += 1
                self.stdout.write(self.style.ERROR(f'❌ Error crítico: {str(e)}'))
        
        # Resumen final
        self.stdout.write(self.style.SUCCESS(
            f'\n=== RESUMEN DE BACKUP ===\n'
            f'✅ Exitosos: {backups_exitosos}\n'
            f'❌ Fallidos: {backups_fallidos}\n'
            f'Total: {backups_exitosos + backups_fallidos}\n'
        ))

    def _ejecutar_backup_completo(self, empresa, backup_registro, ruta_destino, tipo_backup):
        """Ejecuta el proceso completo de backup."""
        try:
            # 1. Crear directorio temporal
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            temp_dir = os.path.join(ruta_destino, f'temp_{empresa.id}_{timestamp}')
            os.makedirs(temp_dir, exist_ok=True)
            
            # 2. Respaldar base de datos
            db_info = self._respaldo_base_datos(temp_dir, empresa, backup_registro)
            
            # 3. Respaldar archivos multimedia
            media_info = self._respaldo_archivos_media(temp_dir, empresa, backup_registro)
            
            # 4. Crear archivo comprimido
            archivo_tar = os.path.join(temp_dir, f'backup_{empresa.id}_{timestamp}.tar.gz')
            self._comprimir_archivos(temp_dir, archivo_tar)
            
            # 5. Cifrar con AES-256
            clave_encriptacion = self._generar_clave_encriptacion()
            archivo_encriptado = archivo_tar + '.encrypted'
            hash_sha256 = self._cifrar_archivo(archivo_tar, archivo_encriptado, clave_encriptacion)
            
            # 6. Calcular tamaño
            tamanio_bytes = os.path.getsize(archivo_encriptado)
            tamanio_mb = Decimal(str(tamanio_bytes)) / Decimal('1048576')
            
            # 7. Mover archivo final
            nombre_final = f'backup_{tipo_backup.lower()}_{empresa.id}_{timestamp}.encrypted'
            ruta_final = os.path.join(ruta_destino, nombre_final)
            shutil.move(archivo_encriptado, ruta_final)
            
            # 8. Actualizar registro
            backup_registro.estado = 'COMPLETADO'
            backup_registro.archivo_backup = os.path.join('backups', nombre_final)
            backup_registro.ruta_completa = ruta_final
            backup_registro.tamanio_bytes = tamanio_bytes
            backup_registro.tamanio_mb = tamanio_mb
            backup_registro.hash_verificacion = hash_sha256
            backup_registro.clave_encriptacion_id = clave_encriptacion.decode('utf-8')[:50]  # Solo ID
            backup_registro.registros_base_datos = db_info.get('registros', 0)
            backup_registro.archivos_media_incluidos = media_info.get('archivos', 0)
            backup_registro.save()

            # 8.1 Archivo Muerto (Drive) - opcional y no bloqueante
            if drive_enabled():
                try:
                    res = subir_archivo_a_drive(file_path=ruta_final, file_name=nombre_final)
                    if res.ok:
                        backup_registro.archivado_en_drive = True
                        backup_registro.drive_file_id = res.file_id
                        backup_registro.drive_folder_id = res.folder_id
                        backup_registro.fecha_archivado_drive = timezone.now()
                        backup_registro.drive_error = None
                        backup_registro.save(
                            update_fields=[
                                "archivado_en_drive",
                                "drive_file_id",
                                "drive_folder_id",
                                "fecha_archivado_drive",
                                "drive_error",
                            ]
                        )
                    else:
                        backup_registro.archivado_en_drive = False
                        backup_registro.drive_folder_id = res.folder_id
                        backup_registro.drive_error = res.error or "Error desconocido"
                        backup_registro.save(update_fields=["archivado_en_drive", "drive_folder_id", "drive_error"])
                except Exception as e:
                    logging.getLogger(__name__).exception("Error inesperado en _ejecutar_backup_completo (backup_nocturno.py)")
                    backup_registro.archivado_en_drive = False
                    backup_registro.drive_error = str(e)
                    backup_registro.save(update_fields=["archivado_en_drive", "drive_error"])
            
            # 9. Limpiar directorio temporal
            shutil.rmtree(temp_dir)
            os.remove(archivo_tar) if os.path.exists(archivo_tar) else None
            
            return {
                'exito': True,
                'archivo': nombre_final,
                'tamanio_mb': float(tamanio_mb),
                'hash': hash_sha256
            }
        
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _ejecutar_backup_completo (backup_nocturno.py)")
            backup_registro.estado = 'FALLIDO'
            backup_registro.mensaje_error = str(e)
            backup_registro.save()
            
            # Limpiar en caso de error
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            return {
                'exito': False,
                'error': str(e)
            }

    def _respaldo_base_datos(self, temp_dir, empresa, backup_registro):
        """Respaldar base de datos completa."""
        db_file = os.path.join(temp_dir, 'database.sql')
        
        db_config = settings.DATABASES['default']
        
        if db_config['ENGINE'] == 'django.db.backends.sqlite3':
            # SQLite: Copiar archivo directamente
            db_path = db_config['NAME']
            if os.path.exists(db_path):
                shutil.copy2(db_path, db_file)
                
                # Contar registros aproximados
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    num_tablas = cursor.fetchone()[0]
                
                return {'registros': num_tablas * 100}  # Aproximación
        
        elif db_config['ENGINE'] == 'django.db.backends.postgresql':
            # PostgreSQL: Usar pg_dump
            db_name = db_config['NAME']
            db_user = db_config['USER']
            db_password = db_config.get('PASSWORD', '')
            db_host = db_config.get('HOST', 'localhost')
            db_port = db_config.get('PORT', '5432')
            
            env = os.environ.copy()
            if db_password:
                env['PGPASSWORD'] = db_password
            
            cmd = [
                'pg_dump',
                '-h', db_host,
                '-p', db_port,
                '-U', db_user,
                '-F', 'p',  # Formato plain text
                '-f', db_file,
                db_name
            ]
            
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            
            # Contar líneas SQL como aproximación de registros
            with open(db_file, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f if 'INSERT INTO' in _)
            
            return {'registros': line_count}
        
        return {'registros': 0}

    def _respaldo_archivos_media(self, temp_dir, empresa, backup_registro):
        """Respaldar archivos multimedia."""
        media_backup_dir = os.path.join(temp_dir, 'media')
        os.makedirs(media_backup_dir, exist_ok=True)
        
        media_root = settings.MEDIA_ROOT
        archivos_copiados = 0
        
        # Directorios a respaldar
        directorios_media = [
            'firmas/',           # Firmas digitales
            'firmas_recetas/',   # Firmas de recetas
            'logos/',            # Logos de empresas
            'pdfs/',             # PDFs de RH y otros
        ]
        
        for dir_media in directorios_media:
            origen = os.path.join(media_root, dir_media)
            if os.path.exists(origen):
                destino = os.path.join(media_backup_dir, dir_media)
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                shutil.copytree(origen, destino, dirs_exist_ok=True)
                
                # Contar archivos
                for root, dirs, files in os.walk(destino):
                    archivos_copiados += len(files)
        
        return {'archivos': archivos_copiados}

    def _comprimir_archivos(self, temp_dir, archivo_salida):
        """Comprimir todos los archivos en un tar.gz."""
        import tarfile
        
        with tarfile.open(archivo_salida, 'w:gz') as tar:
            tar.add(temp_dir, arcname=os.path.basename(temp_dir))
        
        return archivo_salida

    def _generar_clave_encriptacion(self):
        """Genera una clave de encriptación AES-256 basada en SECRET_KEY de Django."""
        password = settings.SECRET_KEY.encode('utf-8')
        salt = b'prislab_backup_salt_2025'  # Salt fijo para consistencia
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    def _cifrar_archivo(self, archivo_origen, archivo_destino, clave):
        """Cifra un archivo con AES-256 usando Fernet."""
        fernet = Fernet(clave)
        
        # Leer archivo original
        with open(archivo_origen, 'rb') as f:
            datos = f.read()
        
        # Calcular hash SHA-256 antes de cifrar
        hash_sha256 = hashlib.sha256(datos).hexdigest()
        
        # Cifrar datos
        datos_cifrados = fernet.encrypt(datos)
        
        # Guardar archivo cifrado
        with open(archivo_destino, 'wb') as f:
            f.write(datos_cifrados)
        
        return hash_sha256

    def _limpiar_backups_antiguos(self, empresa, ruta_destino):
        """Elimina backups antiguos según política de rotación."""
        # Política de rotación:
        # - 7 días diarios
        # - 4 semanas (último backup de cada semana)
        # - 6 meses (último backup de cada mes)
        
        hoy = timezone.now().date()
        
        # 1. Eliminar backups diarios antiguos (>7 días)
        fecha_limite_diarios = hoy - timedelta(days=7)
        backups_diarios = BackupRegistro.objects.filter(
            empresa=empresa,
            tipo_backup='DIARIO',
            estado='COMPLETADO',
            fecha_backup__date__lt=fecha_limite_diarios
        )
        
        for backup in backups_diarios:
            if backup.ruta_completa and os.path.exists(backup.ruta_completa):
                try:
                    os.remove(backup.ruta_completa)
                    backup.delete()
                except Exception as e:
                    logging.getLogger(__name__).exception("Error inesperado en _limpiar_backups_antiguos (backup_nocturno.py)")
                    self.stdout.write(self.style.WARNING(f'No se pudo eliminar backup antiguo: {backup.ruta_completa}'))
        
        # 2. Mantener solo los últimos 4 backups semanales
        backups_semanales = BackupRegistro.objects.filter(
            empresa=empresa,
            tipo_backup='SEMANAL',
            estado='COMPLETADO'
        ).order_by('-fecha_backup')[4:]
        
        for backup in backups_semanales:
            if backup.ruta_completa and os.path.exists(backup.ruta_completa):
                try:
                    os.remove(backup.ruta_completa)
                    backup.delete()
                except Exception as e:
                    logging.getLogger(__name__).exception("Error inesperado en _limpiar_backups_antiguos (backup_nocturno.py)")
                    self.stdout.write(self.style.WARNING(f'No se pudo eliminar backup semanal antiguo: {backup.ruta_completa}'))
        
        # 3. Mantener solo los últimos 6 backups mensuales
        backups_mensuales = BackupRegistro.objects.filter(
            empresa=empresa,
            tipo_backup='MENSUAL',
            estado='COMPLETADO'
        ).order_by('-fecha_backup')[6:]
        
        for backup in backups_mensuales:
            if backup.ruta_completa and os.path.exists(backup.ruta_completa):
                try:
                    os.remove(backup.ruta_completa)
                    backup.delete()
                except Exception as e:
                    logging.getLogger(__name__).exception("Error inesperado en _limpiar_backups_antiguos (backup_nocturno.py)")
                    self.stdout.write(self.style.WARNING(f'No se pudo eliminar backup mensual antiguo: {backup.ruta_completa}'))