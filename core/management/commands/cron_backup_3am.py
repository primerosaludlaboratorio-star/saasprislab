"""
Script para Cron Job - Backup Nocturno 3:00 AM
Este script debe ser ejecutado por el sistema de cron.

Ejemplo de configuración en crontab:
    0 3 * * * cd /ruta/proyecto && /usr/bin/python3 manage.py backup_nocturno >> /var/log/prislab_backup.log 2>&1
"""
from django.core.management import execute_from_command_line
import sys

if __name__ == '__main__':
    sys.argv = ['manage.py', 'backup_nocturno']
    execute_from_command_line(sys.argv)
