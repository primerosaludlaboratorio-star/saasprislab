#!/usr/bin/env python3
"""
Script de backup de base de datos a Google Drive.
Se ejecuta desde el contenedor Docker o directamente en el servidor.

Uso:
    docker-compose exec app python scripts/backup_to_drive.py
    o
    python scripts/backup_to_drive.py (desde host con PostgreSQL expuesto)

Crontab sugerido (en el host):
    0 2 * * * cd /opt/prislab && docker-compose exec -T app python scripts/backup_to_drive.py
"""

import os
import sys
import subprocess
import gzip
from datetime import datetime
from pathlib import Path

# Agregar el proyecto al path para importar settings
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings


def backup_database():
    """
    Realiza backup de PostgreSQL y lo sube a Google Drive.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"backup_{timestamp}.sql.gz"
    
    # Configuración de base de datos desde settings
    db_settings = settings.DATABASES['default']
    db_name = db_settings.get('NAME', 'prislab')
    db_user = db_settings.get('USER', 'prislab_user')
    db_password = db_settings.get('PASSWORD', '')
    db_host = db_settings.get('HOST', 'db')
    db_port = db_settings.get('PORT', '5432')
    
    print(f"[BACKUP] Iniciando backup de la base de datos: {db_name}")
    print(f"[BACKUP] Host: {db_host}:{db_port}, Usuario: {db_user}")
    
    # Directorio temporal para el backup
    backup_dir = Path('/tmp/prislab_backups')
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    local_path = backup_dir / backup_filename
    
    try:
        # Variables de entorno para pg_dump
        env = os.environ.copy()
        if db_password:
            env['PGPASSWORD'] = db_password
        
        # Comando pg_dump
        pg_dump_cmd = [
            'pg_dump',
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
            '--verbose',
            '--clean',
            '--if-exists',
            '--create'
        ]
        
        print(f"[BACKUP] Ejecutando pg_dump...")
        
        # Ejecutar pg_dump y comprimir con gzip
        with gzip.open(local_path, 'wb') as f_out:
            result = subprocess.run(
                pg_dump_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            if result.returncode != 0:
                print(f"[ERROR] pg_dump falló: {result.stderr.decode()}")
                return False
            
            f_out.write(result.stdout)
        
        file_size = local_path.stat().st_size
        print(f"[BACKUP] Backup local creado: {local_path} ({file_size / 1024 / 1024:.2f} MB)")
        
        # Subir a Google Drive
        upload_to_drive(local_path, backup_filename)
        
        # Limpiar archivo local
        local_path.unlink()
        print(f"[BACKUP] Archivo local eliminado: {local_path}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error durante el backup: {e}")
        # Limpiar archivo local si existe
        if local_path.exists():
            local_path.unlink()
        return False


def upload_to_drive(local_path: Path, filename: str):
    """
    Sube el archivo de backup a Google Drive usando la utilidad del proyecto.
    """
    print(f"[DRIVE] Subiendo {filename} a Google Drive...")
    
    try:
        # Importar la utilidad de Google Drive del proyecto
        from core.utils.google_drive import upload_file_to_drive, get_or_create_folder
        
        # Crear/obtener carpeta de backups
        folder_id = get_or_create_folder('PRISLAB_Backups')
        
        # Subir archivo
        with open(local_path, 'rb') as f:
            file_content = f.read()
        
        file_id = upload_file_to_drive(
            filename=filename,
            content=file_content,
            mime_type='application/gzip',
            folder_id=folder_id
        )
        
        print(f"[DRIVE] ✅ Backup subido exitosamente. File ID: {file_id}")
        
        # Limpiar backups antiguos (mantener últimos 30 días)
        cleanup_old_backups(folder_id)
        
    except ImportError:
        print("[DRIVE] ⚠️  Utilidad de Google Drive no disponible.")
        print(f"[DRIVE] Manteniendo backup local en: {local_path}")
        # No eliminar el archivo local si no se pudo subir
        return False
    except Exception as e:
        print(f"[DRIVE] ❌ Error al subir a Drive: {e}")
        return False


def cleanup_old_backups(folder_id: str, keep_days: int = 30):
    """
    Elimina backups antiguos de Google Drive, manteniendo solo los últimos N días.
    """
    print(f"[CLEANUP] Limpiando backups antiguos (manteniendo {keep_days} días)...")
    
    try:
        from core.utils.google_drive import list_files_in_folder, delete_file
        
        files = list_files_in_folder(folder_id)
        cutoff_date = datetime.now() - __import__('datetime').timedelta(days=keep_days)
        
        deleted_count = 0
        for file in files:
            # Los archivos de backup tienen formato: backup_YYYYMMDD_HHMMSS.sql.gz
            if file['name'].startswith('backup_') and file['name'].endswith('.sql.gz'):
                try:
                    # Extraer fecha del nombre
                    date_str = file['name'].replace('backup_', '').replace('.sql.gz', '').split('_')[0]
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        delete_file(file['id'])
                        print(f"[CLEANUP] Eliminado: {file['name']}")
                        deleted_count += 1
                except (ValueError, IndexError):
                    # Ignorar archivos con formato inesperado
                    pass
        
        print(f"[CLEANUP] ✅ {deleted_count} backups antiguos eliminados")
        
    except Exception as e:
        print(f"[CLEANUP] ⚠️  Error al limpiar backups antiguos: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("PRISLAB SaaS - Backup a Google Drive")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    success = backup_database()
    
    print("-" * 60)
    if success:
        print("✅ Backup completado exitosamente")
        sys.exit(0)
    else:
        print("❌ Backup falló")
        sys.exit(1)
