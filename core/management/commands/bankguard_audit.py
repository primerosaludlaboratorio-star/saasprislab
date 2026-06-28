"""
Bankguard Audit — Nivel 4: Auditoría de Integridad Financiera
==============================================================

Comando de auditoría con modo --strict para CI/CD.
Valida:
1. Hash de cierres (no alterados)
1b. Cierre consolidado vs suma diaria de MovimientoCaja (>1 %)
2. Pagos vs MovimientosCaja (conciliación 1:1)
3. Duplicados INGRESO/VENTA por venta (idempotencia)
4. Tickets de investigación abiertos

Uso:
    python manage.py bankguard_audit
    python manage.py bankguard_audit --strict  # Exit code 1 si hay errores
    python manage.py bankguard_audit --empresa=1 --fecha-desde=2026-01-01

Despliegue PostgreSQL (orden sugerido):
    python manage.py migrate
    python manage.py bankguard_backfill --apply --fecha-corte-ventas=YYYY-MM-DD
    python manage.py bankguard_audit --strict

Registro: logger ``bankguard`` -> logs/bankguard_audit.log (rotativo) + consola.
"""
import logging
import sys
from datetime import date as date_cls, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from core.models import (
    CierreDiaConsolidado,
    TicketInvestigacionCaja,
    MovimientoCaja,
    Venta,
)

_bankguard_log = logging.getLogger('bankguard')


class Command(BaseCommand):
    help = "Bankguard Audit v1.14 — Auditoría de integridad financiera"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Exit code 1 si hay inconsistencias (para CI/CD)'
        )
        parser.add_argument(
            '--empresa',
            type=int,
            help='ID de empresa específica a auditar'
        )
        parser.add_argument(
            '--fecha-desde',
            type=str,
            help='Fecha inicio auditoría (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--fecha-hasta',
            type=str,
            help='Fecha fin auditoría (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--crear-tickets',
            action='store_true',
            help='Crear tickets automáticamente para discrepancias'
        )
    
    def handle(self, *args, **options):
        self.strict = options.get('strict', False)
        self.empresa_id = options.get('empresa')
        self.crear_tickets = options.get('crear_tickets', False)
        
        # Fechas default: últimos 30 días
        fecha_hasta = options.get('fecha_hasta') or timezone.now().strftime('%Y-%m-%d')
        fecha_desde = options.get('fecha_desde') or (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 80))
        self.stdout.write(self.style.MIGRATE_HEADING('BANKGUARD AUDIT v1.14'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 80))
        
        if self.strict:
            self.stdout.write(self.style.WARNING('MODO STRICT: Fallará si hay errores'))
        
        self.stdout.write(f"Rango: {fecha_desde} -> {fecha_hasta}")
        if self.empresa_id:
            self.stdout.write(f"Empresa: {self.empresa_id}")
        self.stdout.write('')
        _bankguard_log.info(
            'bankguard_audit inicio strict=%s empresa=%s rango=%s..%s',
            self.strict,
            self.empresa_id,
            fecha_desde,
            fecha_hasta,
        )
        
        errores = []
        warnings = []
        
        # FASE 1: Validar hashes de cierres
        self.stdout.write(self.style.WARNING('[FASE 1] Validando hashes de cierres...'))
        errores_hashes = self._validar_hashes_cierres(fecha_desde, fecha_hasta)
        errores.extend(errores_hashes)

        self.stdout.write(self.style.WARNING('\n[FASE 1b] Cierres vs kardex diario (umbral 1%)...'))
        errores_cvk = self._validar_cierres_vs_movimientos(fecha_desde, fecha_hasta)
        errores.extend(errores_cvk)
        
        # FASE 2: Conciliación Pagos vs Movimientos
        self.stdout.write(self.style.WARNING('\n[FASE 2] Conciliando pagos vs movimientos...'))
        errores_conciliacion = self._conciliar_pagos_movimientos(fecha_desde, fecha_hasta)
        errores.extend(errores_conciliacion)
        
        # FASE 3: Duplicados de movimiento de caja por venta
        self.stdout.write(self.style.WARNING('\n[FASE 3] Verificando idempotencia INGRESO/VENTA...'))
        errores_dup = self._verificar_duplicados_movimiento_venta(fecha_desde, fecha_hasta)
        errores.extend(errores_dup)
        
        # FASE 4: Políticas de límites
        self.stdout.write(self.style.WARNING('\n[FASE 4] Validando políticas de límites...'))
        warnings_politicas = self._validar_politicas()
        warnings.extend(warnings_politicas)
        
        # FASE 5: Tickets abiertos
        self.stdout.write(self.style.WARNING('\n[FASE 5] Verificando tickets abiertos...'))
        warnings_tickets = self._verificar_tickets()
        warnings.extend(warnings_tickets)
        
        # RESUMEN
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '=' * 80))
        self.stdout.write(self.style.MIGRATE_HEADING('RESUMEN'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 80))
        
        total_errores = len(errores)
        total_warnings = len(warnings)
        
        if total_errores == 0:
            self.stdout.write(self.style.SUCCESS(f"[OK] Errores criticos: {total_errores}"))
        else:
            self.stdout.write(self.style.ERROR(f"[ERR] Errores criticos: {total_errores}"))
            for err in errores[:10]:  # Mostrar primeros 10
                self.stdout.write(self.style.ERROR(f"   - {err}"))
            if len(errores) > 10:
                self.stdout.write(self.style.ERROR(f"   ... y {len(errores) - 10} mas"))
        
        if total_warnings == 0:
            self.stdout.write(self.style.SUCCESS(f"[OK] Warnings: {total_warnings}"))
        else:
            self.stdout.write(self.style.WARNING(f"[WARN] Warnings: {total_warnings}"))
            for warn in warnings[:5]:
                self.stdout.write(self.style.WARNING(f"   - {warn}"))
        
        # EXIT CODE
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 80))
        
        if total_errores > 0:
            for err in errores:
                _bankguard_log.error('bankguard_audit hallazgo: %s', err)
            _bankguard_log.warning(
                'bankguard_audit resumen errores=%s warnings=%s strict=%s',
                total_errores,
                total_warnings,
                self.strict,
            )
            if self.strict:
                self.stdout.write(self.style.ERROR("\n[ERR] AUDITORIA FALLIDA (strict mode)"))
                _bankguard_log.error('bankguard_audit ABORT strict: puerta cerrada (exit 1)')
                sys.exit(1)
            self.stdout.write(self.style.WARNING("\n[WARN] AUDITORIA CON ERRORES (non-strict)"))
            _bankguard_log.warning('bankguard_audit errores en modo no-strict (exit 0)')
            sys.exit(0)
        elif total_warnings > 0:
            for w in warnings:
                _bankguard_log.info('bankguard_audit warning: %s', w)
            self.stdout.write(self.style.WARNING("\n[WARN] AUDITORIA CON WARNINGS"))
            _bankguard_log.info(
                'bankguard_audit fin OK con warnings=%s (exit 0)', total_warnings
            )
            sys.exit(0)
        else:
            self.stdout.write(self.style.SUCCESS("\n[OK] AUDITORIA EXITOSA - Integridad confirmada"))
            _bankguard_log.info('bankguard_audit fin OK sin hallazgos (exit 0)')
            sys.exit(0)
    
    def _validar_hashes_cierres(self, fecha_desde, fecha_hasta):
        """Valida que los hashes de cierres coincidan con los datos."""
        errores = []
        
        fd = date_cls.fromisoformat(fecha_desde)
        fh = date_cls.fromisoformat(fecha_hasta)
        queryset = CierreDiaConsolidado.objects.filter(
            fecha__gte=fd,
            fecha__lte=fh
        )
        if self.empresa_id:
            queryset = queryset.filter(empresa_id=self.empresa_id)
        
        for cierre in queryset:
            if not cierre.verificar_integridad():
                msg = f"Hash inválido: Cierre {cierre.fecha} (Empresa {cierre.empresa_id})"
                errores.append(msg)
                self.stdout.write(self.style.ERROR(f"  [ERR] {msg}"))
                
                if self.crear_tickets:
                    TicketInvestigacionCaja.objects.create(
                        empresa=cierre.empresa,
                        cierre_dia=cierre,
                        tipo_discrepancia='HASH_INVALIDO',
                        descripcion=f"El hash SHA-256 no coincide. Posible alteración post-cierre.",
                        creado_por=None  # Sistema
                    )
                    self.stdout.write(self.style.NOTICE("     -> Ticket creado"))
            else:
                self.stdout.write(self.style.SUCCESS(f"  [OK] Cierre {cierre.fecha} - Hash OK"))
        
        return errores

    def _validar_cierres_vs_movimientos(self, fecha_desde, fecha_hasta):
        from core.services.bankguard_cierre import discrepancia_cierre_vs_kardex, UMBRAL_DISCREPANCIA_DEFAULT

        errores = []
        fd = date_cls.fromisoformat(fecha_desde)
        fh = date_cls.fromisoformat(fecha_hasta)
        queryset = CierreDiaConsolidado.objects.filter(fecha__gte=fd, fecha__lte=fh)
        if self.empresa_id:
            queryset = queryset.filter(empresa_id=self.empresa_id)
        for cierre in queryset:
            excede, det = discrepancia_cierre_vs_kardex(cierre, UMBRAL_DISCREPANCIA_DEFAULT)
            if excede:
                msg = (
                    f"Cierre {cierre.fecha} (emp {cierre.empresa_id}): "
                    f"discrepancia vs MovimientoCaja ratio_max={det['ratio_max']:.4f}"
                )
                errores.append(msg)
                self.stdout.write(self.style.ERROR(f"  [ERR] {msg}"))
                if self.crear_tickets:
                    from core.services.bankguard_cierre import (
                        ticket_cierre_vs_kardex_ya_existe,
                        verificar_discrepancia_cierre_y_ticket,
                    )

                    if not ticket_cierre_vs_kardex_ya_existe(cierre):
                        verificar_discrepancia_cierre_y_ticket(cierre)
                        self.stdout.write(self.style.NOTICE("     -> Ticket cierre vs kardex"))
            else:
                self.stdout.write(self.style.SUCCESS(f"  [OK] Cierre {cierre.fecha} - vs kardex OK"))
        return errores
    
    def _conciliar_pagos_movimientos(self, fecha_desde, fecha_hasta):
        """Concilia que cada venta pagada tenga su movimiento de caja."""
        errores = []
        
        fd = date_cls.fromisoformat(fecha_desde)
        fh = date_cls.fromisoformat(fecha_hasta)
        # Ventas completadas en el período (fecha es DateTimeField)
        ventas = Venta.objects.filter(
            estado__in=['PAGADO', 'COMPLETADO', 'COMPLETADA'],
            fecha__date__gte=fd,
            fecha__date__lte=fh,
            total__gt=0
        )
        if self.empresa_id:
            ventas = ventas.filter(empresa_id=self.empresa_id)
        
        # Contar
        total_ventas = ventas.count()
        ventas_con_movimiento = 0
        ventas_sin_movimiento = []
        
        for venta in ventas:
            tiene_movimiento = MovimientoCaja.objects.filter(
                venta=venta,
                tipo_movimiento='INGRESO',
                concepto='VENTA'
            ).exists()
            
            if tiene_movimiento:
                ventas_con_movimiento += 1
            else:
                ventas_sin_movimiento.append(venta)
        
        # Reportar
        self.stdout.write(f"  Ventas completadas: {total_ventas}")
        self.stdout.write(self.style.SUCCESS(f"  [OK] Con MovimientoCaja: {ventas_con_movimiento}"))
        
        if ventas_sin_movimiento:
            self.stdout.write(self.style.ERROR(f"  [ERR] Sin MovimientoCaja: {len(ventas_sin_movimiento)}"))
            for venta in ventas_sin_movimiento[:5]:
                msg = f"Venta #{venta.id} ({venta.fecha}) - ${venta.total} sin movimiento caja"
                errores.append(msg)
                
                if self.crear_tickets:
                    TicketInvestigacionCaja.objects.create(
                        empresa=venta.empresa,
                        venta=venta,
                        tipo_discrepancia='PAGO_SIN_MOVIMIENTO',
                        descripcion=f"Venta completada sin MovimientoCaja correspondiente",
                        monto_esperado=venta.total,
                        monto_real=Decimal('0.00'),
                        diferencia=venta.total,
                        creado_por=None
                    )
        
        return errores
    
    def _verificar_duplicados_movimiento_venta(self, fecha_desde, fecha_hasta):
        """Más de un MovimientoCaja INGRESO/VENTA por la misma venta (fallo de idempotencia)."""
        errores = []
        fd = date_cls.fromisoformat(fecha_desde)
        fh = date_cls.fromisoformat(fecha_hasta)
        dup_qs = MovimientoCaja.objects.filter(
            venta_id__isnull=False,
            concepto='VENTA',
            tipo_movimiento='INGRESO',
            fecha_movimiento__date__gte=fd,
            fecha_movimiento__date__lte=fh,
        )
        if self.empresa_id:
            dup_qs = dup_qs.filter(empresa_id=self.empresa_id)
        grouped = list(
            dup_qs.values('venta_id').annotate(c=Count('id')).filter(c__gt=1)[:50]
        )
        for row in grouped:
            msg = (
                f"Venta id={row['venta_id']}: {row['c']} movimientos INGRESO/VENTA "
                f"(esperado 1 por idempotencia)"
            )
            errores.append(msg)
            self.stdout.write(self.style.ERROR(f"  [ERR] {msg}"))
        if not grouped:
            self.stdout.write(self.style.SUCCESS("  [OK] Sin duplicados INGRESO/VENTA por venta"))
        return errores
    
    def _validar_politicas(self):
        """Valida que todas las empresas tengan políticas configuradas."""
        warnings = []
        
        from core.models import Empresa
        
        empresas_sin_politica = Empresa.objects.filter(
            politica_caja__isnull=True
        )
        
        for emp in empresas_sin_politica:
            warnings.append(f"Empresa '{emp.nombre}' sin Política de Límites configurada")
        
        if warnings:
            self.stdout.write(self.style.WARNING(f"  [WARN] {len(warnings)} empresas sin politica"))
        else:
            self.stdout.write(self.style.SUCCESS("  [OK] Todas las empresas tienen politica"))
        
        return warnings
    
    def _verificar_tickets(self):
        """Verifica tickets de investigación abiertos."""
        warnings = []
        
        tickets_abiertos = TicketInvestigacionCaja.objects.filter(
            estado__in=['ABIERTO', 'EN_INVESTIGACION']
        )
        
        if self.empresa_id:
            tickets_abiertos = tickets_abiertos.filter(empresa_id=self.empresa_id)
        
        count = tickets_abiertos.count()
        
        if count > 0:
            warnings.append(f"{count} tickets de investigación abiertos")
            self.stdout.write(self.style.WARNING(f"  [WARN] {count} tickets abiertos"))
        else:
            self.stdout.write(self.style.SUCCESS("  [OK] Sin tickets abiertos"))
        
        return warnings
