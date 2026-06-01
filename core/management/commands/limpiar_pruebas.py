"""
Script de limpieza de datos de prueba.
Borra Órdenes y Resultados, pero respeta Usuarios y Catálogos.

Uso:
    python manage.py limpiar_pruebas [--confirmar]
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from core.models import (
    OrdenDeServicio, DetalleOrden, Venta, DetalleVenta, Pago,
    ReporteUltrasonido, ImagenUltrasonido, BitacoraConsultaIA,
    TomaMuestra, EnvioMaquila
)
from core.models import Paciente

Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Limpia datos de prueba (Órdenes y Resultados), respeta Usuarios y Catálogos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma la limpieza (sin este flag solo muestra qué se borraría)',
        )

    def handle(self, *args, **options):
        confirmar = options['confirmar']
        
        if not confirmar:
            self.stdout.write(self.style.WARNING(
                '\n[ADVERTENCIA] MODO SIMULACION - No se borrara nada\n'
                'Use --confirmar para ejecutar la limpieza real\n'
            ))
        
        try:
            with transaction.atomic():
                # Contar registros antes de borrar
                ordenes_count = OrdenDeServicio.objects.count()
                detalles_count = DetalleOrden.objects.count()
                ventas_count = Venta.objects.count()
                pagos_count = Pago.objects.count()
                reportes_usg_count = ReporteUltrasonido.objects.count()
                imagenes_usg_count = ImagenUltrasonido.objects.count()
                bitacoras_ia_count = BitacoraConsultaIA.objects.count()
                tomas_muestra_count = TomaMuestra.objects.count()
                envios_maquila_count = EnvioMaquila.objects.count()
                
                self.stdout.write(self.style.WARNING('\n=== DATOS A BORRAR ==='))
                self.stdout.write(f'Órdenes de Servicio: {ordenes_count}')
                self.stdout.write(f'Detalles de Orden: {detalles_count}')
                self.stdout.write(f'Ventas: {ventas_count}')
                self.stdout.write(f'Pagos: {pagos_count}')
                self.stdout.write(f'Reportes Ultrasonido: {reportes_usg_count}')
                self.stdout.write(f'Imágenes Ultrasonido: {imagenes_usg_count}')
                self.stdout.write(f'Bitácoras IA: {bitacoras_ia_count}')
                self.stdout.write(f'Tomas de Muestra: {tomas_muestra_count}')
                self.stdout.write(f'Envíos Maquila: {envios_maquila_count}')
                
                # Datos que NO se borran
                usuarios_count = Usuario.objects.count()
                pacientes_count = Paciente.objects.count()
                estudios_count = self._contar_estudios()
                productos_count = self._contar_productos()
                
                self.stdout.write(self.style.SUCCESS('\n=== DATOS QUE SE CONSERVAN ==='))
                self.stdout.write(f'Usuarios: {usuarios_count}')
                self.stdout.write(f'Pacientes: {pacientes_count}')
                self.stdout.write(f'Estudios: {estudios_count}')
                self.stdout.write(f'Productos: {productos_count}')
                
                if not confirmar:
                    self.stdout.write(self.style.WARNING(
                        '\n[INFO] Para ejecutar la limpieza, use: python manage.py limpiar_pruebas --confirmar'
                    ))
                    return
                
                # Confirmación final
                self.stdout.write(self.style.ERROR(
                    '\n[ADVERTENCIA] Esta operacion NO se puede deshacer'
                ))
                
                # Borrar en orden (respetando foreign keys)
                self.stdout.write(self.style.WARNING('\n=== INICIANDO LIMPIEZA ==='))
                
                # 1. Borrar imágenes de ultrasonido (dependen de reportes)
                if imagenes_usg_count > 0:
                    ImagenUltrasonido.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'[OK] Borradas {imagenes_usg_count} imagenes de ultrasonido'))
                
                # 2. Borrar reportes de ultrasonido
                if reportes_usg_count > 0:
                    ReporteUltrasonido.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'[OK] Borrados {reportes_usg_count} reportes de ultrasonido'))
                
                # 3. Borrar bitácoras IA
                if bitacoras_ia_count > 0:
                    BitacoraConsultaIA.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'[OK] Borradas {bitacoras_ia_count} bitacoras IA'))
                
                # 4. Borrar tomas de muestra
                if tomas_muestra_count > 0:
                    TomaMuestra.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'[OK] Borradas {tomas_muestra_count} tomas de muestra'))
                
                # 5. Borrar envíos maquila
                if envios_maquila_count > 0:
                    EnvioMaquila.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'[OK] Borrados {envios_maquila_count} envios maquila'))
                
                # 6. Borrar detalles de orden (dependen de órdenes)
                if detalles_count > 0:
                    DetalleOrden.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'[OK] Borrados {detalles_count} detalles de orden'))
                
                # 7. Borrar órdenes de servicio
                if ordenes_count > 0:
                    OrdenDeServicio.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'[OK] Borradas {ordenes_count} ordenes de servicio'))
                
                # 8. Borrar detalles de venta (dependen de ventas)
                detalles_venta_count = DetalleVenta.objects.count()
                if detalles_venta_count > 0:
                    DetalleVenta.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'[OK] Borrados {detalles_venta_count} detalles de venta'))
                
                # 9. Borrar pagos (dependen de ventas/órdenes)
                if pagos_count > 0:
                    Pago.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'[OK] Borrados {pagos_count} pagos'))
                
                # 10. Borrar ventas
                if ventas_count > 0:
                    Venta.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'[OK] Borradas {ventas_count} ventas'))
                
                self.stdout.write(self.style.SUCCESS('\n[COMPLETADO] LIMPIEZA COMPLETADA'))
                self.stdout.write(self.style.SUCCESS('Los Usuarios, Pacientes, Estudios y Productos se conservaron intactos.'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Error durante la limpieza: {str(e)}'))
            raise
    
    def _contar_estudios(self):
        """Cuenta estudios de laboratorio (legacy app laboratorio)."""
        try:
            from laboratorio.models import Estudio
            return Estudio.objects.count()
        except Exception:
            return 0
    
    def _contar_productos(self):
        """Cuenta productos sin importar el modelo exacto."""
        try:
            from core.models import Producto
            return Producto.objects.count()
        except:
            return 0
