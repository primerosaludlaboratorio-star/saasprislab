"""
═══════════════════════════════════════════════════════════════════════════════
COMANDO: anclar_hashes_diarios
═══════════════════════════════════════════════════════════════════════════════

Reparación Grieta #2: Anclaje Externo (La prueba de "No Manipulación")

Cada medianoche, este comando genera un hash de todos los hashes del día
y lo envía por email automático a una cuenta externa. Crea evidencia de
tiempo (Timestamping) fuera del servidor. Si alguien altera la base de datos,
el hash diario ya no coincidirá con el email enviado hace tres meses.

Fórmula: Hash_Raiz = SHA256(Hash1 + Hash2 + ... + HashN + Fecha)

Uso:
    python manage.py anclar_hashes_diarios [--fecha YYYY-MM-DD] [--email dest@correo.com]

Configuración en settings.py:
    HASH_ROOT_EXTERNAL_EMAIL = 'auditoria@prislab.app'  # Email externo obligatorio
    HASH_ROOT_BACKUP_EMAILS = ['copia1@prislab.app', 'copia2@prislab.app']
═══════════════════════════════════════════════════════════════════════════════
"""

import hashlib
import logging
from datetime import datetime, timedelta, date
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from core.models import ExpedienteNotaSHA, HashRaizDiario

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Genera el hash raíz diario del blockchain y lo ancla externamente vía email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha específica a procesar (YYYY-MM-DD). Por defecto: ayer',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email externo de destino. Por defecto: HASH_ROOT_EXTERNAL_EMAIL',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin enviar email ni guardar en BD',
        )
        parser.add_argument(
            '--verificar',
            action='store_true',
            help='Verificar integridad de un hash raíz existente',
        )

    def handle(self, *args, **options):
        # Determinar fecha a procesar
        if options['fecha']:
            try:
                fecha_procesar = datetime.strptime(options['fecha'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Formato de fecha inválido. Use YYYY-MM-DD')
        else:
            # Por defecto: ayer (para asegurar que el día haya terminado)
            fecha_procesar = date.today() - timedelta(days=1)
        
        email_destino = options['email'] or getattr(settings, 'HASH_ROOT_EXTERNAL_EMAIL', None)
        
        if not email_destino and not options['dry_run']:
            raise CommandError(
                'Debe configurar HASH_ROOT_EXTERNAL_EMAIL en settings.py '
                'o proporcionar --email'
            )
        
        # Verificar modo
        if options['verificar']:
            self.verificar_hash_existente(fecha_procesar)
            return
        
        # Generar hash raíz
        self.stdout.write(self.style.NOTICE(f'Procesando hash raíz para: {fecha_procesar}'))
        
        # Calcular rangos de tiempo
        inicio_dia = timezone.make_aware(datetime.combine(fecha_procesar, datetime.min.time()))
        fin_dia = timezone.make_aware(datetime.combine(fecha_procesar, datetime.max.time()))
        
        # Obtener todos los hashes del día (solo notas selladas/firmadas)
        hashes_del_dia = list(ExpedienteNotaSHA.objects.filter(
            timestamp_creacion__range=(inicio_dia, fin_dia),
            firmado_con_pin=True
        ).values_list('hash_sha256', flat=True).order_by('hash_sha256'))
        
        total_hashes = len(hashes_del_dia)
        total_notas = ExpedienteNotaSHA.objects.filter(
            timestamp_creacion__range=(inicio_dia, fin_dia)
        ).values('nota_soap').distinct().count()
        
        self.stdout.write(f'  → Hashes acumulados: {total_hashes}')
        self.stdout.write(f'  → Notas selladas: {total_notas}')
        
        if total_hashes == 0:
            self.stdout.write(self.style.WARNING('No hay hashes para esta fecha. Omitiendo.'))
            return
        
        # Obtener hash del día anterior para encadenamiento
        dia_anterior = fecha_procesar - timedelta(days=1)
        hash_anterior = None
        try:
            hash_raiz_anterior = HashRaizDiario.objects.get(fecha=dia_anterior)
            hash_anterior = hash_raiz_anterior.hash_raiz
        except HashRaizDiario.DoesNotExist:
            pass
        
        # Calcular hash raíz
        hashes_ordenados = sorted(hashes_del_dia)
        bloque = f"{'|'.join(hashes_ordenados)}|{fecha_procesar.isoformat()}"
        if hash_anterior:
            bloque = f"{bloque}|{hash_anterior}"
        
        hash_raiz = hashlib.sha256(bloque.encode('utf-8')).hexdigest()
        
        self.stdout.write(self.style.SUCCESS(f'  → Hash Raíz: {hash_raiz[:32]}...'))
        self.stdout.write(f'  → Hash Anterior: {hash_anterior[:32] if hash_anterior else "GENESIS"}...')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Modo DRY-RUN: No se guardará ni enviará'))
            return
        
        # Crear o actualizar registro
        hash_raiz_obj, created = HashRaizDiario.objects.update_or_create(
            fecha=fecha_procesar,
            defaults={
                'año': fecha_procesar.year,
                'mes': fecha_procesar.month,
                'dia': fecha_procesar.day,
                'hash_raiz': hash_raiz,
                'total_notas_selladas': total_notas,
                'total_hashes_acumulados': total_hashes,
                'hash_anterior_dia': hash_anterior,
                'timestamp_calculo': timezone.now(),
                'ip_calculador': '127.0.0.1',  # Se actualizará si hay request
            }
        )
        
        accion = 'creado' if created else 'actualizado'
        self.stdout.write(self.style.SUCCESS(f'Registro {accion}: ID={hash_raiz_obj.id}'))
        
        # Enviar email de anclaje externo
        if email_destino:
            self.enviar_email_anclaje(hash_raiz_obj, email_destino, hashes_ordenados)
        
        self.stdout.write(self.style.SUCCESS('✓ Anclaje diario completado'))
    
    def enviar_email_anclaje(self, hash_raiz_obj, email_destino, hashes_ordenados):
        """Envía el email con el hash raíz a la cuenta externa."""
        
        subject = f'[PRISLAB-ANCLAJE] Hash Raíz Diario — {hash_raiz_obj.fecha}'
        
        # Construir cuerpo del email
        message = f"""
══════════════════════════════════════════════════════════════════
ANCLAJE FORENSE DIARIO — PRISLAB v2.0
Fecha de Cálculo: {hash_raiz_obj.timestamp_calculo or timezone.now()}
══════════════════════════════════════════════════════════════════

FECHA ANCLADA: {hash_raiz_obj.fecha}
HASH RAÍZ: {hash_raiz_obj.hash_raiz}

RESUMEN DEL DÍA:
  • Notas selladas: {hash_raiz_obj.total_notas_selladas}
  • Hashes acumulados: {hash_raiz_obj.total_hashes_acumulados}
  • Hash día anterior: {hash_raiz_obj.hash_anterior_dia or 'GENESIS'}

FÓRMULA DE CÁLCULO:
  SHA256(sorted(hashes) | fecha | hash_anterior)

VERIFICACIÓN:
  Para verificar la integridad, ejecute:
  python manage.py anclar_hashes_diarios --fecha {hash_raiz_obj.fecha} --verificar

══════════════════════════════════════════════════════════════════
Este email es una evidencia de tiempo legalmente vinculante.
Si la base de datos es alterada, este hash ya no coincidirá.
══════════════════════════════════════════════════════════════════
        """
        
        # Lista de destinatarios
        recipient_list = [email_destino]
        
        # Agregar emails de copia si están configurados
        copias = getattr(settings, 'HASH_ROOT_BACKUP_EMAILS', [])
        if copias:
            recipient_list.extend(copias)
        
        try:
            from django.core.mail import EmailMessage
            
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@prislab.app'),
                to=[email_destino],
                cc=copias if copias else None,
            )
            
            # Adjuntar archivo con los hashes individuales (opcional)
            if len(hashes_ordenados) > 0:
                hashes_content = '\n'.join(hashes_ordenados)
                email.attach(
                    f'hashes_{hash_raiz_obj.fecha}.txt',
                    hashes_content,
                    'text/plain'
                )
            
            sent = email.send(fail_silently=False)
            
            if sent:
                # Actualizar registro con evidencia de envío
                hash_raiz_obj.email_enviado_a = email_destino
                hash_raiz_obj.timestamp_envio = timezone.now()
                hash_raiz_obj.email_message_id = email.extra_headers.get('Message-ID', '')
                hash_raiz_obj.save(update_fields=['email_enviado_a', 'timestamp_envio', 'email_message_id'])
                
                self.stdout.write(self.style.SUCCESS(f'✓ Email enviado a: {email_destino}'))
                if copias:
                    self.stdout.write(f'  → Copias: {", ".join(copias)}')
            
        except Exception as e:
            logger.error(f'Error enviando email de anclaje: {e}')
            self.stdout.write(self.style.ERROR(f'✗ Error enviando email: {e}'))
    
    def verificar_hash_existente(self, fecha):
        """Verifica la integridad de un hash raíz existente."""
        
        try:
            hash_raiz_obj = HashRaizDiario.objects.get(fecha=fecha)
        except HashRaizDiario.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'No existe hash raíz para {fecha}'))
            return
        
        self.stdout.write(f'Verificando hash raíz del {fecha}...')
        
        resultado = hash_raiz_obj.verificar_integridad_anclaje()
        
        if resultado['valido']:
            self.stdout.write(self.style.SUCCESS('✓ INTEGRIDAD VERIFICADA'))
            self.stdout.write(f'  → Hashes verificados: {resultado["total_hashes_verificados"]}')
            self.stdout.write(f'  → Hash almacenado: {resultado["hash_almacenado"][:32]}...')
        else:
            self.stdout.write(self.style.ERROR('✗ ALERTA: INTEGRIDAD COMPROMETIDA'))
            self.stdout.write(f'  → Hash almacenado: {resultado["hash_almacenado"]}')
            self.stdout.write(f'  → Hash calculado:  {resultado["hash_calculado"]}')
            self.stdout.write(self.style.ERROR('  → Posible manipulación detectada'))
