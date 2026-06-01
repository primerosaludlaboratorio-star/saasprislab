"""
SCRIPT DE PRUEBA: Registro de Pacientes
Verifica que el sistema de alta express funcione correctamente
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Paciente, Empresa
from datetime import date

def probar_registro():
    print("=" * 80)
    print("PRUEBA: REGISTRO EXPRESS DE PACIENTES")
    print("=" * 80)
    print()
    
    eid = os.environ.get("PRISLAB_EMPRESA_ID")
    if not eid:
        print("[ERROR] Defina PRISLAB_EMPRESA_ID (pk de Empresa).")
        return False
    try:
        empresa = Empresa.objects.get(pk=int(eid))
    except (ValueError, Empresa.DoesNotExist):
        print(f"[ERROR] Empresa id={eid!r} no válida.")
        return False
    
    print(f"[OK] Empresa: {empresa.nombre}")
    print()
    
    # Datos de prueba
    paciente_prueba = {
        'nombre_completo': 'Prueba Sistema Test',
        'fecha_nacimiento': date(1990, 1, 1),
        'sexo': 'M',
        'telefono': '5551234567',
        'email': 'prueba@test.com',
    }
    
    print("[PRUEBA] Creando paciente de prueba...")
    print(f"  Nombre: {paciente_prueba['nombre_completo']}")
    print(f"  Fecha Nac: {paciente_prueba['fecha_nacimiento']}")
    print(f"  Sexo: {paciente_prueba['sexo']}")
    print(f"  Teléfono: {paciente_prueba['telefono']}")
    print(f"  Email: {paciente_prueba['email']}")
    print()
    
    try:
        # Crear paciente
        paciente = Paciente.objects.create(
            empresa=empresa,
            **paciente_prueba,
            activo=True
        )
        
        print(f"[OK] Paciente creado con ID: {paciente.id}")
        print(f"[OK] Nombre completo: {paciente.nombre_completo}")
        print(f"[OK] Edad calculada: {paciente.edad} años")
        print()
        
        # Verificar que se guardó
        paciente_db = Paciente.objects.get(id=paciente.id)
        print("[OK] Paciente recuperado de BD correctamente")
        print()
        
        # Verificar campos
        checks = [
            ('nombre_completo', paciente_db.nombre_completo == paciente_prueba['nombre_completo']),
            ('fecha_nacimiento', paciente_db.fecha_nacimiento == paciente_prueba['fecha_nacimiento']),
            ('sexo', paciente_db.sexo == paciente_prueba['sexo']),
            ('telefono', paciente_db.telefono == paciente_prueba['telefono']),
            ('email', paciente_db.email == paciente_prueba['email']),
            ('activo', paciente_db.activo == True),
        ]
        
        print("[VERIFICACION DE CAMPOS]:")
        todos_ok = True
        for campo, resultado in checks:
            status = "[OK]" if resultado else "[FALLO]"
            print(f"  {status} {campo}")
            if not resultado:
                todos_ok = False
        
        print()
        
        if todos_ok:
            print("=" * 80)
            print("[EXITO] Todas las pruebas pasaron correctamente")
            print("=" * 80)
            print()
            print("RESUMEN:")
            print(f"  - Paciente de prueba creado: {paciente.nombre_completo}")
            print(f"  - ID: {paciente.id}")
            print(f"  - Todos los campos verificados: SI")
            print()
            
            # Limpiar (opcional)
            respuesta = input("¿Eliminar paciente de prueba? (s/n): ")
            if respuesta.lower() == 's':
                paciente.delete()
                print("[OK] Paciente de prueba eliminado")
            else:
                print(f"[INFO] Paciente {paciente.id} quedó en la BD")
            
            return True
        else:
            print("[FALLO] Algunos campos no coinciden")
            return False
            
    except Exception as e:
        print(f"[ERROR] Fallo al crear paciente: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    resultado = probar_registro()
    exit(0 if resultado else 1)
