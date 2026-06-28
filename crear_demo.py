
import os
from datetime import date, timedelta
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from core.models import Empresa, Usuario, Paciente, Producto, Lote
from laboratorio.models import Estudio, Parametro, ValorReferencia, CategoriaExamen
from core.tenant import set_current_empresa, clear_current_empresa

empresa, _ = Empresa.objects.get_or_create(nombre='Clinica Demo', defaults={'rfc': 'DEMO123456789'})
# Crear usuario admin si no tiene empresa
admin = Usuario.objects.filter(username='admin').first()
if admin and not admin.empresa:
    admin.empresa = empresa
    admin.save()

# Crear un paciente demo
paciente, _ = Paciente.objects.get_or_create(
    nombre_completo='Juan Perez',
    empresa=empresa,
    defaults={'nombres': 'Juan', 'apellido_paterno': 'Perez', 'telefono': '5551234567'}
)

# Crear producto demo
producto, _ = Producto.objects.get_or_create(
    nombre='Paracetamol 500mg',
    empresa=empresa,
    defaults={
        'codigo_barras': '7501234567890123',
        'forma_farmaceutica': 'Tabletas',
        'concentracion': '500mg',
        'presentacion': '20 tabletas',
        'precio_publico': 45.0,
        'stock': 100
    }
)
lote, _ = Lote.objects.get_or_create(
    producto=producto, numero_lote='LOTE001', empresa=empresa,
    defaults={
        'cantidad': 100,
        'fecha_caducidad': date.today() + timedelta(days=365),
        'costo_adquisicion': 30.0
    }
)

# Crear categoria primero (requerida por Estudio)
categoria, _ = CategoriaExamen.objects.get_or_create(nombre='Quimica Clinica')

# Crear estudio demo (glucosa) - Estudio no tiene campo empresa directo
estudio, _ = Estudio.objects.get_or_create(
    nombre='Glucosa',
    defaults={
        'codigo': 'GLU',
        'categoria': categoria,
        'unidades': 'mg/dL',
        'precio_base': 150.00,
        'activo': True
    }
)
# Crear parametro con valores de referencia
parametro, _ = Parametro.objects.get_or_create(
    nombre='Glucosa',
    estudio=estudio,
    defaults={'unidades': 'mg/dL', 'codigo_interfaz': 'GLU'}
)
# Nota: sexo=null significa ambos sexos en este modelo
ValorReferencia.objects.get_or_create(
    estudio=estudio,
    sexo=None,
    edad='ADULTO',
    defaults={'valor_minimo': 70.0, 'valor_maximo': 110.0}
)
print("[OK] Datos demo creados")
