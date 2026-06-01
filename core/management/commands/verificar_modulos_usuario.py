"""
Verificación E2E de módulos como usuario.
Simula login y navegación por URLs críticas.
Si el catálogo de farmacia está vacío, carga productos de prueba.

Uso: python manage.py verificar_modulos_usuario --empresa-id=1 [--username=admin]
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Verificación E2E de módulos como usuario. Corrige catálogo vacío si es necesario.'

    def add_arguments(self, parser):
        from core.utils.tenant_strict import add_argument_empresa_id

        add_argument_empresa_id(parser, required=True)
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Usuario para force_login (debe pertenecer a --empresa-id si no es superusuario).',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('VERIFICACIÓN DE MÓDULOS COMO USUARIO'))
        self.stdout.write(self.style.SUCCESS('=' * 80 + '\n'))

        errores = []
        client = Client()

        from core.models import Empresa

        eid = options['empresa_id']
        try:
            empresa = Empresa.objects.get(pk=eid)
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'[ERROR] No existe Empresa id={eid}'))
            return

        uname = options.get('username')
        if uname:
            try:
                usuario = Usuario.objects.get(username=uname)
            except Usuario.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'[ERROR] Usuario {uname!r} no existe'))
                return
            u_emp = getattr(usuario, 'empresa', None)
            if u_emp and u_emp.pk != empresa.pk and not usuario.is_superuser:
                self.stdout.write(
                    self.style.ERROR(
                        '[ERROR] El usuario no pertenece a la empresa indicada '
                        '(use superusuario o --username de ese tenant).'
                    )
                )
                return
        else:
            usuario = (
                Usuario.objects.filter(empresa_id=eid, is_superuser=True).first()
                or Usuario.objects.filter(empresa_id=eid).first()
            )
            if not usuario:
                usuario = Usuario.objects.filter(is_superuser=True).first()
            if not usuario:
                self.stdout.write(
                    self.style.ERROR(
                        '[ERROR] No hay usuario para esa empresa. Cree uno o use --username=...'
                    )
                )
                return

        self.stdout.write(f'  Usuario de prueba: {usuario.username}')
        self.stdout.write(f'  Empresa: {empresa.nombre}')

        # 3. Verificar y corregir catálogo farmacia
        from core.models import Producto
        total_productos = Producto.objects.filter(empresa=empresa).count()
        if total_productos == 0:
            self.stdout.write(self.style.WARNING('  [CATÁLOGO VACÍO] Cargando productos de prueba...'))
            self._cargar_productos_prueba(empresa)
            total_productos = Producto.objects.filter(empresa=empresa).count()
            self.stdout.write(self.style.SUCCESS(f'  [OK] {total_productos} productos cargados'))

        # 4. Login
        self.stdout.write(self.style.WARNING('\n[2] LOGIN...'))
        if not usuario.check_password('admin123'):
            # Intentar password común
            if usuario.is_superuser and hasattr(usuario, 'set_password'):
                self.stdout.write(self.style.WARNING('  [INFO] Usando force_login (no se verifica password)'))
        client.force_login(usuario)
        self.stdout.write(self.style.SUCCESS('  [OK] Sesión iniciada'))

        # 5. Verificar URLs críticas
        urls_verificar = [
            ('home', 'Dashboard'),
            ('pdv_farmacia', 'PDV Farmacia'),
            ('recepcion_lab', 'Recepción Lab'),
            ('lista_trabajo_lab', 'Lista Trabajo Lab'),
        ]

        self.stdout.write(self.style.WARNING('\n[3] VERIFICANDO URLs...'))
        for url_name, label in urls_verificar:
            try:
                url = reverse(url_name)
                resp = client.get(url, follow=True)
                if resp.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f'  [OK] {label}: {url}'))
                else:
                    errores.append(f'{label}: HTTP {resp.status_code}')
                    self.stdout.write(self.style.ERROR(f'  [FAIL] {label}: HTTP {resp.status_code}'))
            except Exception as e:
                errores.append(f'{label}: {e}')
                self.stdout.write(self.style.ERROR(f'  [FAIL] {label}: {e}'))

        # 6. Verificar búsqueda PDV (AJAX)
        self.stdout.write(self.style.WARNING('\n[4] VERIFICANDO BÚSQUEDA PDV...'))
        try:
            url = reverse('pdv_farmacia') + '?accion=buscar_producto&termino=para'
            resp = client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            if resp.status_code == 200:
                data = resp.json()
                productos = data.get('productos', [])
                if productos:
                    self.stdout.write(self.style.SUCCESS(f'  [OK] Búsqueda "para" retornó {len(productos)} productos'))
                else:
                    diag = data.get('diagnostico', '')
                    if diag == 'sin_productos':
                        self.stdout.write(self.style.WARNING('  [WARN] Sin productos. Ejecuta: python manage.py cargar_productos_csv Productos-farmacia-2026-02-10-10-31.csv'))
                    else:
                        self.stdout.write(self.style.WARNING('  [WARN] No hay productos que coincidan con "para"'))
            else:
                errores.append(f'PDV buscar: HTTP {resp.status_code}')
                self.stdout.write(self.style.ERROR(f'  [FAIL] Búsqueda PDV: HTTP {resp.status_code}'))
        except Exception as e:
            errores.append(f'PDV buscar: {e}')
            self.stdout.write(self.style.ERROR(f'  [FAIL] Búsqueda PDV: {e}'))

        # 7. Resumen
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        if errores:
            self.stdout.write(self.style.ERROR(f'ERRORES: {len(errores)}'))
            for e in errores:
                self.stdout.write(self.style.ERROR(f'  - {e}'))
        else:
            self.stdout.write(self.style.SUCCESS('TODOS LOS MÓDULOS VERIFICADOS CORRECTAMENTE'))
        self.stdout.write('=' * 80 + '\n')

    def _cargar_productos_prueba(self, empresa):
        """Carga productos de prueba para que el PDV funcione."""
        from core.models import Producto, Sucursal
        sucursal = Sucursal.objects.filter(empresa=empresa).first()

        productos_data = [
            ('7501234567890', 'Paracetamol 500mg', 'Paracetamol', Decimal('25.00'), 100),
            ('7501234567891', 'Sucralfato 1g', 'Sucralfato', Decimal('45.00'), 50),
            ('7501234567892', 'Ciprofloxacino 500mg', 'Ciprofloxacino', Decimal('85.00'), 30),
            ('7501234567893', 'Ibuprofeno 400mg', 'Ibuprofeno', Decimal('35.00'), 80),
            ('7501234567894', 'Amoxicilina 500mg', 'Amoxicilina', Decimal('55.00'), 40),
        ]

        for codigo, nombre, sustancia, precio, stock in productos_data:
            Producto.objects.update_or_create(
                codigo_barras=codigo,
                defaults={
                    'empresa': empresa,
                    'sucursal': sucursal,
                    'nombre': nombre,
                    'sustancia_activa': sustancia,
                    'forma_farmaceutica': 'Tableta',
                    'concentracion': 'N/A',
                    'presentacion': '1',
                    'precio_compra': precio * Decimal('0.5'),
                    'precio_publico': precio,
                    'stock': stock,
                    'iva_porcentaje': Decimal('16'),
                    'clasificacion_sanitaria': 'VI',
                    'categoria': 'GENERICO',
                    'es_antibiotico': 'amox' in sustancia.lower() or 'cipro' in sustancia.lower(),
                    'es_servicio': False,
                }
            )
