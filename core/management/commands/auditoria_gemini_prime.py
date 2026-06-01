"""
Auditoría Forense Gemini Prime - Nivel 3
=======================================
Detección de errores silenciosos. Construcción por bloques.
Bloque 1: Fundación Core (Salud del servidor, BD, configuración crítica).

Uso:
    python manage.py auditoria_gemini_prime
"""
import os

import psutil
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = 'Auditoría Forense Gemini Prime - Nivel 3 (Detección de Errores Silenciosos)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("[PRIME] Iniciando Auditoria Forense Gemini Prime..."))
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        # Inicializar el contenedor del reporte
        self.report_lines = [
            "# [PRIME] PRISLAB - Reporte de Auditoria Forense (Gemini Prime)",
            f"**Fecha de ejecución:** {timestamp}",
            f"**Entorno:** {'PRODUCCIÓN (Peligro)' if not settings.DEBUG else 'DESARROLLO (Seguro)'}\n",
            "---",
            "## 1. SALUD CORE Y RECURSOS DEL SERVIDOR (Fugas de Memoria y CPU)"
        ]

        self._auditar_recursos_sistema()
        self._auditar_conexiones_db()
        self._auditar_configuracion_critica()
        self._auditar_farmacia_ventas()
        self._auditar_seguridad_2fa()
        self._auditar_consultorio_laboratorio()
        self._auditar_sincronizacion_drive()

        # Guardar reporte en archivo MD
        filename = "REPORTE_GEMINI_PRIME.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(self.report_lines))
        self.stdout.write("\n".join(self.report_lines))
        self.stdout.write(self.style.SUCCESS(f"[OK] Auditoria Gemini Prime completada. Revisa {filename}"))

    def _auditar_recursos_sistema(self):
        """Lógica Forense: Detectar si el servidor de Prislab se está ahogando."""
        proceso = psutil.Process(os.getpid())
        memoria_mb = proceso.memory_info().rss / (1024 * 1024)
        cpu_percent = proceso.cpu_percent(interval=0.1)

        estado_memoria = "CRÍTICO (Posible fuga)" if memoria_mb > 500 else "ESTABLE"

        self.report_lines.extend([
            f"- **Uso de RAM del proceso Django:** {memoria_mb:.2f} MB [{estado_memoria}]",
            f"- **Uso de CPU del proceso:** {cpu_percent}%",
            f"- **Hilos activos (Threads):** {proceso.num_threads()} (Si > 50, revisar concurrencia)",
        ])

    def _auditar_conexiones_db(self):
        """Lógica Forense: Detectar 'database is locked' o conexiones zombis antes de que ocurran."""
        self.report_lines.append("\n## 2. INTEGRIDAD DE CONEXION A BASE DE DATOS")
        try:
            connection.ensure_connection()
            if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
                # Validar timeout en SQLite para evitar bloqueos en el SaaS
                timeout = settings.DATABASES['default'].get('OPTIONS', {}).get('timeout', 0)
                alerta_timeout = "[ALERTA] Timeout bajo o nulo. Riesgo de 'database is locked'." if timeout < 20 else "OK"
                self.report_lines.append(f"- **Motor:** SQLite3 | **Timeout Configurado:** {timeout}s [{alerta_timeout}]")
            else:
                self.report_lines.append(f"- **Motor:** {settings.DATABASES['default']['ENGINE']} | Conexión activa: OK")
        except OperationalError as e:
            self.report_lines.append(f"- [ERROR] **ERROR CRITICO DE BD:** No se pudo asegurar la conexion: {str(e)}")

    def _auditar_configuracion_critica(self):
        """Lógica Forense: Validar que los puentes hacia el exterior (Drive, Seguridad) estén armados."""
        self.report_lines.append("\n## 3. CONFIGURACION CRITICA DEL ENTORNO")

        # Validar almacenamiento (DEFAULT_FILE_STORAGE o STORAGES en Django 4.2+)
        storage = getattr(settings, 'DEFAULT_FILE_STORAGE', None)
        if storage is None and hasattr(settings, 'STORAGES'):
            storage = settings.STORAGES.get('default', {}).get('BACKEND', '')
        storage = str(storage or 'django.core.files.storage.FileSystemStorage')
        es_drive = 'GoogleDriveStorage' in storage or 'GDrive' in storage
        alerta_storage = "OK (Conectado a la nube)" if es_drive else "[ALERTA] Usando almacenamiento local. Los PDFs no iran a los 2TB."
        self.report_lines.append(f"- **Motor de Almacenamiento:** {storage} [{alerta_storage}]")

        # Validar zona horaria (Vital para cortes de caja)
        tz = settings.TIME_ZONE
        alerta_tz = "OK" if tz == 'America/Mexico_City' else "[ALERTA] Zona horaria incorrecta, los cortes de caja de Prislab saldran desfasados."
        self.report_lines.append(f"- **Zona Horaria del Servidor:** {tz} [{alerta_tz}]")

    def _auditar_farmacia_ventas(self):
        """Logica Forense: Cuadre de caja y ventas fantasma en Laboratorio del Valle / Prislab."""
        self.report_lines.append("\n## 4. INTEGRIDAD DE FARMACIA Y CAJA (Silent Fails)")
        try:
            from django.apps import apps
            Venta = apps.get_model('core', 'Venta')

            # 1. Ventas fantasma (Cobradas pero sin ticket/folio)
            ventas_sin_ticket = Venta.objects.filter(
                estado='COMPLETADA',
                folio_operacion__isnull=True
            ).count()
            alerta_ticket = "[CRITICO] Posible evasion o fallo en PDF" if ventas_sin_ticket > 0 else "OK"
            self.report_lines.append(f"- **Ventas cobradas sin folio generado:** {ventas_sin_ticket} [{alerta_ticket}]")

            # 2. Devoluciones sin justificacion detallada (Fuga de dinero)
            DevolucionVenta = apps.get_model('farmacia', 'DevolucionVenta')
            from django.db.models import Q
            devoluciones_vacias = DevolucionVenta.objects.filter(
                Q(motivo_detallado__isnull=True) | Q(motivo_detallado='')
            ).count()
            alerta_dev = "[ADVERTENCIA] Falta control en caja" if devoluciones_vacias > 0 else "OK"
            self.report_lines.append(f"- **Devoluciones registradas sin motivo detallado:** {devoluciones_vacias} [{alerta_dev}]")

        except LookupError:
            self.report_lines.append("- *Modulo Farmacia no encontrado o inactivo para auditar.*")

    def _auditar_seguridad_2fa(self):
        """Logica Forense: Prevenir el Crash 500 por nulos en el Log de Acciones Sensibles."""
        self.report_lines.append("\n## 5. SEGURIDAD Y DOBLE FACTOR (Prevencion de Crashes)")
        try:
            from django.apps import apps
            LogAccionSensible = apps.get_model('seguridad', 'LogAccionSensible')

            # Buscar logs que esten a punto de romper la BD por el IntegrityError detectado previamente
            logs_riesgo = LogAccionSensible.objects.filter(user_agent__isnull=True).count()
            alerta_logs = "[CRITICO] Riesgo de Crash 500 - Validar modelo" if logs_riesgo > 0 else "OK"
            self.report_lines.append(f"- **Logs de seguridad con User-Agent nulo:** {logs_riesgo} [{alerta_logs}]")

        except LookupError:
            self.report_lines.append("- *Modulo Seguridad no encontrado o inactivo para auditar.*")

    def _auditar_consultorio_laboratorio(self):
        """Logica Forense: Evitar expedientes clinicos huerfanos o incompletos."""
        self.report_lines.append("\n## 6. CONSULTORIO Y LABORATORIO (Integridad Clinica)")

        # 1. Auditoria de Consultorio
        try:
            from django.apps import apps
            ConsultaMedica = apps.get_model('core', 'ConsultaMedica')
            consultas_incompletas = ConsultaMedica.objects.filter(
                estado='FINALIZADA',
                diagnostico_cie10__isnull=True
            ).count()
            alerta_cons = "[ADVERTENCIA] Falta CIE-10 en expediente" if consultas_incompletas > 0 else "OK"
            self.report_lines.append(f"- **Consultas finalizadas sin diagnostico CIE-10:** {consultas_incompletas} [{alerta_cons}]")
        except LookupError:
            self.report_lines.append("- *Modulo Consultorio no encontrado.*")

        # 2. Auditoria de Laboratorio
        try:
            from django.apps import apps
            OrdenDeServicio = apps.get_model('core', 'OrdenDeServicio')
            ordenes_huerfanas = OrdenDeServicio.objects.filter(paciente__isnull=True).count()
            alerta_lab = "[CRITICO] Perdida de trazabilidad de paciente" if ordenes_huerfanas > 0 else "OK"
            self.report_lines.append(f"- **Ordenes de Laboratorio sin paciente asignado:** {ordenes_huerfanas} [{alerta_lab}]")
        except LookupError:
            self.report_lines.append("- *Modulo Laboratorio no encontrado.*")

    def _auditar_sincronizacion_drive(self):
        """Logica Forense: Verificacion fisica de archivos cruzada con la BD."""
        self.report_lines.append("\n## 7. SINCRONIZACION DE ARCHIVOS FISICOS (Drive vs BD)")
        try:
            from django.apps import apps
            from django.core.files.storage import default_storage
            OrdenDeServicio = apps.get_model('core', 'OrdenDeServicio')

            # Ultimos 50 registros con archivo_resultado (PDFs de laboratorio)
            ultimos_pdfs = OrdenDeServicio.objects.filter(
                archivo_resultado__isnull=False
            ).exclude(archivo_resultado='').order_by('-fecha_creacion')[:50]
            total_revisados = 0
            archivos_perdidos = 0

            for pdf in ultimos_pdfs:
                if pdf.archivo_resultado and pdf.archivo_resultado.name:
                    total_revisados += 1
                    if not default_storage.exists(pdf.archivo_resultado.name):
                        archivos_perdidos += 1

            if total_revisados == 0:
                self.report_lines.append("- *No hay PDFs recientes en la base de datos para auditar.*")
            else:
                alerta_drive = "[ALERTA ROJA] Fallo de subida. El archivo no existe fisicamente" if archivos_perdidos > 0 else "OK (Sincronizacion Perfecta)"
                self.report_lines.append(f"- **Ultimos {total_revisados} PDFs de Laboratorio validados:** {archivos_perdidos} perdidos fisicamente [{alerta_drive}]")

        except LookupError:
            self.report_lines.append("- *Modulo de Ordenes no encontrado para auditar Drive.*")
        except Exception as e:
            self.report_lines.append(f"- *[ERROR] Error al validar la conexion con Drive: {str(e)}*")
