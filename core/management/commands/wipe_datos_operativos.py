"""
Wipe Datos Operativos - Limpieza pre-despliegue
================================================
Elimina datos transaccionales generados por pruebas/auditorías.
PRESERVA: Usuarios, Grupos, Permisos, CIE-10, Productos, Empresa, Sucursal.

REQUIERE confirmación manual: escribir 'CONFIRMAR_WIPE_PRISLAB'

Uso:
    python manage.py wipe_datos_operativos
    python manage.py wipe_datos_operativos --media  # incluye archivos en media/
"""
import os

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files.storage import default_storage

CONFIRMACION_REQUERIDA = "CONFIRMAR_WIPE_PRISLAB"


class Command(BaseCommand):
    help = "Elimina datos transaccionales (consultas, recetas, ventas, ordenes, etc.). Preserva maestros."

    def add_arguments(self, parser):
        parser.add_argument(
            "--media",
            action="store_true",
            help="Borrar tambien archivos fisicos en media/ (PDFs, firmas, etc.)",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Saltar confirmacion (SOLO para scripts automatizados)",
        )

    def handle(self, *args, **options):
        borrar_media = options.get("media", False)
        skip_confirm = options.get("yes", False)

        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write(self.style.WARNING("WIPE DATOS OPERATIVOS - PRISLAB"))
        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write("")
        self.stdout.write("Se eliminaran:")
        self.stdout.write("  - ConsultaMedica, Receta, RecetaItem")
        self.stdout.write("  - OrdenDeServicio, DetalleOrden, ResultadoParametro")
        self.stdout.write("  - Venta, DetalleVenta, Pago, DevolucionVenta")
        self.stdout.write("  - DiarioEmocional, IncidenciaSentinel, AuditLog")
        self.stdout.write("  - CitaMedica, PreOrdenLaboratorio, MovimientoInventario, etc.")
        self.stdout.write("")
        self.stdout.write("Se PRESERVAN: Usuarios, Grupos, Permisos, Productos,")
        self.stdout.write("  Empresa, Sucursal, CIE-10, Estudios, Parametros.")
        self.stdout.write("")

        if not skip_confirm:
            confirm = input(f"Escribe '{CONFIRMACION_REQUERIDA}' para continuar: ").strip()
            if confirm != CONFIRMACION_REQUERIDA:
                self.stdout.write(self.style.ERROR("Abortado. Confirmacion incorrecta."))
                return

        rutas_media = []
        with transaction.atomic():
            conteos = self._ejecutar_wipe(borrar_media, rutas_media)
            if borrar_media:
                self._borrar_archivos_media(rutas_media)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Wipe completado:"))
        for modelo, n in sorted(conteos.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  - {modelo}: {n} registros eliminados")
        if borrar_media and rutas_media:
            self.stdout.write(f"  - Archivos media: {len(rutas_media)} eliminados")

    def _get_model(self, app_label, model_name):
        try:
            return apps.get_model(app_label, model_name)
        except LookupError:
            return None

    def _ejecutar_wipe(self, borrar_media, rutas_media):
        conteos = {}
        M = self._get_model

        def _delete(model, label=None):
            if model is None:
                return 0
            c, _ = model.objects.all().delete()
            conteos[label or f"{model._meta.app_label}.{model._meta.model_name}"] = c
            return c

        # 1. Recolectar rutas de archivos antes de borrar (OrdenDeServicio, Receta)
        if borrar_media:
            OrdenDeServicio = M("core", "OrdenDeServicio")
            Receta = M("core", "Receta")
            if OrdenDeServicio:
                for o in OrdenDeServicio.objects.exclude(archivo_resultado=""):
                    if o.archivo_resultado and o.archivo_resultado.name:
                        rutas_media.append(o.archivo_resultado.name)
            if Receta:
                for r in Receta.objects.exclude(medico_firma_digital=""):
                    if r.medico_firma_digital and r.medico_firma_digital.name:
                        rutas_media.append(r.medico_firma_digital.name)

        # 2. Laboratorio - hijos primero
        HistorialResultados = M("core", "HistorialResultados")
        ResultadoParametro = M("core", "ResultadoParametro")
        DetalleOrden = M("core", "DetalleOrden")
        TomaMuestra = M("core", "TomaMuestra")
        BitacoraEntregaResultados = M("core", "BitacoraEntregaResultados")
        EnvioMaquila = M("core", "EnvioMaquila")
        DetallePreOrden = M("core", "DetallePreOrden")
        PreOrdenLaboratorio = M("core", "PreOrdenLaboratorio")
        PagoOrden = M("core", "PagoOrden")

        _delete(HistorialResultados)
        _delete(ResultadoParametro)
        _delete(DetalleOrden)
        _delete(TomaMuestra)
        _delete(BitacoraEntregaResultados)
        if EnvioMaquila:
            for e in EnvioMaquila.objects.all():
                e.ordenes.clear()
            _delete(EnvioMaquila)
        _delete(DetallePreOrden)
        _delete(PreOrdenLaboratorio)
        _delete(PagoOrden)

        # 2b. NotaCredito y ConsentimientoInformado (FK a OrdenDeServicio)
        NotaCredito = M("core", "NotaCredito")
        RegistroAuditoriaConsentimiento = M("core", "RegistroAuditoriaConsentimiento")
        ConsentimientoInformado = M("core", "ConsentimientoInformado")
        _delete(RegistroAuditoriaConsentimiento)
        _delete(ConsentimientoInformado)
        _delete(NotaCredito)

        # 3. OrdenDeServicio
        OrdenDeServicio = M("core", "OrdenDeServicio")
        _delete(OrdenDeServicio)

        # 4. Clinico - hijos de ConsultaMedica
        CertificadoMedico = M("core", "CertificadoMedico")
        EstudioImagen = M("core", "EstudioImagen")
        ImagenDetalle = M("core", "ImagenDetalle")
        HistorialCambiosConsulta = M("core", "HistorialCambiosConsulta")
        NotaClinicaSOAP = M("core", "NotaClinicaSOAP")
        LogAccesoExpediente = M("core", "LogAccesoExpediente")
        ConsentimientoInformado = M("core", "ConsentimientoInformado")
        RegistroAuditoriaConsentimiento = M("core", "RegistroAuditoriaConsentimiento")
        AudioConsulta = M("core", "AudioConsulta")
        Antecedente = M("core", "Antecedente")

        _delete(ImagenDetalle)
        _delete(EstudioImagen)
        _delete(CertificadoMedico)
        _delete(HistorialCambiosConsulta)
        _delete(NotaClinicaSOAP)
        _delete(LogAccesoExpediente)
        _delete(AudioConsulta)
        _delete(Antecedente)

        ConsultaMedica = M("core", "ConsultaMedica")
        _delete(ConsultaMedica)

        CitaMedica = M("core", "CitaMedica")
        _delete(CitaMedica)

        # 5. Ventas - devoluciones y pagos antes de ventas
        DevolucionVentaCore = M("core", "DevolucionVenta")
        DevolucionVentaFarmacia = M("farmacia", "DevolucionVenta")
        SalesReturn = M("core", "SalesReturn")
        MovimientoCaja = M("core", "MovimientoCaja")
        PagoCuentaPorCobrar = M("core", "PagoCuentaPorCobrar")
        CuentaPorCobrar = M("core", "CuentaPorCobrar")
        FacturaSAT = M("core", "FacturaSAT")
        Pago = M("core", "Pago")
        DetalleVenta = M("core", "DetalleVenta")

        _delete(DevolucionVentaCore)
        _delete(DevolucionVentaFarmacia)
        _delete(SalesReturn)
        _delete(MovimientoCaja)
        _delete(PagoCuentaPorCobrar)
        _delete(CuentaPorCobrar)
        _delete(FacturaSAT)
        _delete(Pago)
        MovimientoInventario = M("farmacia", "MovimientoInventario")
        _delete(MovimientoInventario)
        _delete(DetalleVenta)

        Venta = M("core", "Venta")
        _delete(Venta)

        # 6. Recetas
        DemandaInsatisfecha = M("core", "DemandaInsatisfecha")
        RecetaItem = M("core", "RecetaItem")
        Receta = M("core", "Receta")

        _delete(DemandaInsatisfecha)
        _delete(RecetaItem)
        _delete(Receta)

        # 7. Bienestar
        DiarioEmocional = M("bienestar", "DiarioEmocional")
        _delete(DiarioEmocional)

        # 8. Sentinel / Auditoria
        IncidenciaSentinel = M("consultorio", "IncidenciaSentinel")
        AuditLog = M("core", "AuditLog")
        _delete(IncidenciaSentinel)
        _delete(AuditLog)

        # 9. Consultorio legacy (Somatometria FK a ConsultaMedica, borrar primero)
        Somatometria = M("consultorio", "Somatometria")
        ConsultaMedicaLegacy = M("consultorio", "ConsultaMedica")
        NotaMedica = M("consultorio", "NotaMedica")
        if Somatometria:
            _delete(Somatometria)
        if ConsultaMedicaLegacy:
            _delete(ConsultaMedicaLegacy)
        if NotaMedica:
            _delete(NotaMedica)

        return conteos

    def _borrar_archivos_media(self, rutas):
        for ruta in rutas:
            try:
                if default_storage.exists(ruta):
                    default_storage.delete(ruta)
            except Exception:
                pass
