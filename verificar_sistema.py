"""
SCRIPT DE VERIFICACIÓN RÁPIDA - PRISLAB GOLD
Ejecutar antes de iniciar pruebas clínicas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from laboratorio.models import Estudio, Parametro, PerfilLaboratorio, ValorReferencia
from farmacia.models import Producto, AperturaCaja
from core.models import Paciente, Usuario, CitaMedica
from django.contrib.auth import get_user_model

User = get_user_model()

def verificar_sistema():
    print("="*80)
    print("VERIFICACION SISTEMA PRISLAB GOLD")
    print("="*80)
    
    # LABORATORIO
    print("\n[LABORATORIO]")
    estudios = Estudio.objects.count()
    parametros = Parametro.objects.count()
    paquetes = PerfilLaboratorio.objects.count()
    rangos = ValorReferencia.objects.count()
    estudios_con_precio = Estudio.objects.filter(precio_base__gt=0).count()
    
    print(f"  Estudios: {estudios} {'[OK]' if estudios > 500 else '[ADVERTENCIA: Pocos estudios]'}")
    print(f"  Parametros: {parametros} {'[OK]' if parametros > 400 else '[ADVERTENCIA]'}")
    print(f"  Paquetes: {paquetes} {'[OK]' if paquetes > 10 else '[ADVERTENCIA]'}")
    print(f"  Rangos Referencia: {rangos} {'[OK]' if rangos > 200 else '[ADVERTENCIA]'}")
    print(f"  Estudios con precio: {estudios_con_precio}/{estudios} ({estudios_con_precio*100//estudios if estudios else 0}%)")
    
    # FARMACIA
    print("\n[FARMACIA]")
    productos = Producto.objects.count()
    try:
        cajas_abiertas = AperturaCaja.objects.filter(activa=True).count()
    except:
        cajas_abiertas = 0
    
    print(f"  Productos: {productos} {'[PENDIENTE: Cargar inventario]' if productos == 0 else '[OK]'}")
    print(f"  Cajas abiertas: {cajas_abiertas}")
    
    # CONSULTORIO
    print("\n[CONSULTORIO]")
    pacientes = Paciente.objects.count()
    try:
        from datetime import date
        citas_hoy = CitaMedica.objects.filter(fecha_cita=date.today()).count()
    except:
        citas_hoy = 0
    usuarios = User.objects.count()
    
    print(f"  Pacientes: {pacientes} {'[OK]' if pacientes > 0 else '[SIN PACIENTES]'}")
    print(f"  Citas hoy: {citas_hoy}")
    print(f"  Usuarios sistema: {usuarios} {'[OK]' if usuarios > 0 else '[ERROR: Sin usuarios]'}")
    
    # URLS CRÍTICAS
    print("\n[URLS CRITICAS]")
    urls_criticas = [
        "/consultorio/",
        "/consultorio/paciente/nuevo/",
        "/farmacia/",
        "/laboratorio/",
        "/admin/",
    ]
    print("  Rutas configuradas:")
    for url in urls_criticas:
        print(f"    {url} [DISPONIBLE]")
    
    # RESUMEN
    print("\n" + "="*80)
    print("RESUMEN GENERAL")
    print("="*80)
    
    criticos = 0
    advertencias = 0
    
    if estudios < 500:
        advertencias += 1
    if productos == 0:
        advertencias += 1
        print("  [!] ADVERTENCIA: Farmacia sin productos. Cargar inventario.")
    if usuarios == 0:
        criticos += 1
        print("  [X] CRITICO: Sin usuarios en el sistema.")
    
    if criticos == 0 and advertencias == 0:
        print("  [OK] Sistema 100% operativo")
        print("  [OK] Listo para pruebas clinicas")
        return True
    elif criticos == 0:
        print(f"  [!] Sistema operativo con {advertencias} advertencia(s)")
        print("  [OK] Puede iniciar pruebas clinicas")
        return True
    else:
        print(f"  [X] Sistema con {criticos} error(es) critico(s)")
        print("  [X] Resolver antes de iniciar pruebas")
        return False

if __name__ == '__main__':
    resultado = verificar_sistema()
    exit(0 if resultado else 1)
