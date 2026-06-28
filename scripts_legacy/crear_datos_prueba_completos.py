# -*- coding: utf-8 -*-
"""
Script para crear datos de prueba completos con diferentes escenarios.
Valida: PDF, Notificaciones de Panico, Rangos por Edad/Sexo, Validacion en Tiempo Real.

Autor: PRIS
Fecha: 2026-01-25
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from datetime import date, timedelta, datetime
from django.contrib.auth import get_user_model
from core.models import (
    Empresa, Sucursal, Paciente, OrdenDeServicio, DetalleOrden,
    SeccionLaboratorio, Estudio, Parametro, RangoReferencia
)

User = get_user_model()

print("="*70)
print("CREANDO DATOS DE PRUEBA - PRISLAB V5.0")
print("="*70)

# ============================================================================
# 1. EMPRESA Y SUCURSAL
# ============================================================================
print("\n[1/7] Creando Empresa y Sucursal...")
empresa, _ = Empresa.objects.get_or_create(
    nombre="PRISLAB S.A. de C.V.",
    defaults={
        'rfc': 'PRS123456789',
        'direccion': 'Av. Principal #123, Col. Centro',
        'telefono': '2281234567'
    }
)

sucursal, _ = Sucursal.objects.get_or_create(
    empresa=empresa,
    nombre="Matriz",
    defaults={
        'codigo_sucursal': 'SUC-001',
        'direccion': 'Av. Principal #123',
        'telefono': '2281234567',
        'activa': True
    }
)
print(f"   [OK] Empresa: {empresa.nombre}")
print(f"   [OK] Sucursal: {sucursal.nombre}")

# ============================================================================
# 2. PACIENTES CON DIFERENTES CARACTERÍSTICAS
# ============================================================================
print("\n[2/7] Creando Pacientes con diferentes perfiles...")

# Usuario admin como responsable
admin_user = User.objects.get(username='admin')

# Paciente 1: ADULTO MASCULINO NORMAL (30 años)
paciente1, _ = Paciente.objects.get_or_create(
    empresa=empresa,
    nombre_completo="JUAN CARLOS MARTINEZ LOPEZ",
    defaults={
        'fecha_nacimiento': date.today() - timedelta(days=30*365),
        'sexo': 'M',
        'telefono': '2281111111',
        'email': 'juan.martinez@email.com',
        'sucursal': sucursal
    }
)
print(f"   [OK] Paciente 1: {paciente1.nombre_completo} (30 años, M) - VALORES NORMALES")

# Paciente 2: ADULTO FEMENINO CON ALERTA (45 años)
paciente2, _ = Paciente.objects.get_or_create(
    empresa=empresa,
    nombre_completo="MARIA GUADALUPE FERNANDEZ TORRES",
    defaults={
        'fecha_nacimiento': date.today() - timedelta(days=45*365),
        'sexo': 'F',
        'telefono': '2282222222',
        'email': 'maria.fernandez@email.com',
        'sucursal': sucursal
    }
)
print(f"   [OK] Paciente 2: {paciente2.nombre_completo} (45 años, F) - VALORES FUERA DE RANGO")

# Paciente 3: ADULTO MASCULINO CON PÁNICO (55 años)
paciente3, _ = Paciente.objects.get_or_create(
    empresa=empresa,
    nombre_completo="ROBERTO SANCHEZ GARCIA",
    defaults={
        'fecha_nacimiento': date.today() - timedelta(days=55*365),
        'sexo': 'M',
        'telefono': '2283333333',
        'email': 'roberto.sanchez@email.com',
        'sucursal': sucursal
    }
)
print(f"   [OK] Paciente 3: {paciente3.nombre_completo} (55 años, M) - VALORES CRITICOS (PANICO)")

# Paciente 4: NIÑO (8 años)
paciente4, _ = Paciente.objects.get_or_create(
    empresa=empresa,
    nombre_completo="LUIS ALBERTO RAMIREZ HERNANDEZ",
    defaults={
        'fecha_nacimiento': date.today() - timedelta(days=8*365),
        'sexo': 'M',
        'telefono': '2284444444',
        'email': 'luis.ramirez@email.com',
        'sucursal': sucursal
    }
)
print(f"   [OK] Paciente 4: {paciente4.nombre_completo} (8 años, M) - PACIENTE PEDIATRICO")

# Paciente 5: ADULTO MAYOR (75 años)
paciente5, _ = Paciente.objects.get_or_create(
    empresa=empresa,
    nombre_completo="PEDRO GONZALEZ MORALES",
    defaults={
        'fecha_nacimiento': date.today() - timedelta(days=75*365),
        'sexo': 'M',
        'telefono': '2285555555',
        'email': 'pedro.gonzalez@email.com',
        'sucursal': sucursal
    }
)
print(f"   [OK] Paciente 5: {paciente5.nombre_completo} (75 años, M) - ADULTO MAYOR")

# ============================================================================
# 3. SECCIONES DE LABORATORIO
# ============================================================================
print("\n[3/7] Creando Secciones de Laboratorio...")
seccion_quimica, _ = SeccionLaboratorio.objects.get_or_create(
    nombre="QUIMICA CLINICA",
    defaults={'descripcion': 'Analisis quimicos generales'}
)

seccion_hematologia, _ = SeccionLaboratorio.objects.get_or_create(
    nombre="HEMATOLOGIA",
    defaults={'descripcion': 'Estudio de la sangre'}
)
print(f"   [OK] Seccion 1: {seccion_quimica.nombre}")
print(f"   [OK] Seccion 2: {seccion_hematologia.nombre}")

# ============================================================================
# 4. ESTUDIOS Y PARÁMETROS
# ============================================================================
print("\n[4/7] Creando Estudios con Parámetros...")

# ESTUDIO 1: GLUCOSA
estudio_glucosa, _ = Estudio.objects.get_or_create(
    codigo='GLU001',
    defaults={
        'nombre': "GLUCOSA EN AYUNAS",
        'seccion': seccion_quimica,
        'precio': Decimal('150.00')
    }
)

param_glucosa, _ = Parametro.objects.get_or_create(
    estudio=estudio_glucosa,
    nombre="Glucosa",
    defaults={
        'unidad': 'mg/dL',
        'tipo_dato': 'NUMERICO',
        'orden_impresion': 1,
        'activo': True
    }
)
print(f"   [OK] Estudio 1: {estudio_glucosa.nombre}")
print(f"      -> Parametro: {param_glucosa.nombre}")

# ESTUDIO 2: HEMOGLOBINA
estudio_hemoglobina, _ = Estudio.objects.get_or_create(
    codigo='HEM001',
    defaults={
        'nombre': "HEMOGLOBINA",
        'seccion': seccion_hematologia,
        'precio': Decimal('120.00')
    }
)

param_hemoglobina, _ = Parametro.objects.get_or_create(
    estudio=estudio_hemoglobina,
    nombre="Hemoglobina",
    defaults={
        'unidad': 'g/dL',
        'tipo_dato': 'NUMERICO',
        'orden_impresion': 1,
        'activo': True
    }
)
print(f"   [OK] Estudio 2: {estudio_hemoglobina.nombre}")
print(f"      ------ Parametro: {param_hemoglobina.nombre}")

# ============================================================================
# 5. RANGOS DE REFERENCIA CON VALORES DE PÁNICO
# ============================================================================
print("\n[5/7] Creando Rangos de Referencia con Valores de Pánico...")

# GLUCOSA - ADULTOS
rango_glucosa_adulto, _ = RangoReferencia.objects.get_or_create(
    parametro=param_glucosa,
    sexo='I',  # Indiferente
    edad_minima=18*365,
    edad_maxima=999999,
    defaults={
        'valor_minimo': Decimal('70.00'),
        'valor_maximo': Decimal('100.00'),
        'panico_minimo': Decimal('40.00'),  # PANICO: < 40
        'panico_maximo': Decimal('400.00'),  # PANICO: > 400
    }
)
print(f"   [OK] Rango Glucosa Adultos: 70-100 mg/dL (Panico: <40 o >400)")

# GLUCOSA - PEDIATRICO
rango_glucosa_pediatrico, _ = RangoReferencia.objects.get_or_create(
    parametro=param_glucosa,
    sexo='I',
    edad_minima=0,
    edad_maxima=18*365,
    defaults={
        'valor_minimo': Decimal('60.00'),
        'valor_maximo': Decimal('110.00'),
        'panico_minimo': Decimal('40.00'),
        'panico_maximo': Decimal('300.00'),
    }
)
print(f"   [OK] Rango Glucosa Pediatrico: 60-110 mg/dL (Panico: <40 o >300)")

# HEMOGLOBINA - HOMBRE ADULTO
rango_hb_hombre, _ = RangoReferencia.objects.get_or_create(
    parametro=param_hemoglobina,
    sexo='M',
    edad_minima=18*365,
    edad_maxima=999999,
    defaults={
        'valor_minimo': Decimal('13.50'),
        'valor_maximo': Decimal('17.50'),
        'panico_minimo': Decimal('7.00'),  # PANICO: < 7
        'panico_maximo': Decimal('20.00'),  # PANICO: > 20
    }
)
print(f"   [OK] Rango Hemoglobina Hombres: 13.5-17.5 g/dL (Panico: <7 o >20)")

# HEMOGLOBINA - MUJER ADULTO
rango_hb_mujer, _ = RangoReferencia.objects.get_or_create(
    parametro=param_hemoglobina,
    sexo='F',
    edad_minima=18*365,
    edad_maxima=999999,
    defaults={
        'valor_minimo': Decimal('12.00'),
        'valor_maximo': Decimal('16.00'),
        'panico_minimo': Decimal('7.00'),
        'panico_maximo': Decimal('20.00'),
    }
)
print(f"   [OK] Rango Hemoglobina Mujeres: 12.0-16.0 g/dL (Panico: <7 o >20)")

# ============================================================================
# 6. ÓRDENES CON DIFERENTES ESCENARIOS
# ============================================================================
print("\n[6/7] Creando Órdenes con Diferentes Escenarios...")

# Generar folio único con timestamp
timestamp = datetime.now().strftime('%H%M%S')

# ORDEN 1: PACIENTE 1 - VALORES NORMALES (TODO VERDE)
orden1 = OrdenDeServicio.objects.create(
    empresa=empresa,
    sucursal=sucursal,
    paciente=paciente1,
    folio_orden=f"ORD-{date.today().strftime('%Y%m%d')}-{timestamp}-001",
    estado='PAGADO',
    total=Decimal('150.00'),
    responsable_ingreso=admin_user
)
DetalleOrden.objects.create(
    orden=orden1,
    estudio=estudio_glucosa,
    precio_momento=Decimal('150.00')
)
print(f"   [OK] ORDEN 1: {orden1.folio_orden}")
print(f"      ------ Paciente: {paciente1.nombre_completo}")
print(f"      ------ Estudio: Glucosa")
print(f"      ------ Escenario: VALORES NORMALES (Verde) [OK]")
print(f"      ------ Valor Esperado: 85 mg/dL (dentro de 70-100)")

# ORDEN 2: PACIENTE 2 - VALORES FUERA DE RANGO (AMARILLO)
orden2 = OrdenDeServicio.objects.create(
    empresa=empresa,
    sucursal=sucursal,
    paciente=paciente2,
    folio_orden=f"ORD-{date.today().strftime('%Y%m%d')}-{timestamp}-002",
    estado='PAGADO',
    total=Decimal('120.00'),
    responsable_ingreso=admin_user
)
DetalleOrden.objects.create(
    orden=orden2,
    estudio=estudio_hemoglobina,
    precio_momento=Decimal('120.00')
)
print(f"   [OK] ORDEN 2: {orden2.folio_orden}")
print(f"      ------ Paciente: {paciente2.nombre_completo}")
print(f"      ------ Estudio: Hemoglobina")
print(f"      ------ Escenario: FUERA DE RANGO (Amarillo) [!!]")
print(f"      ------ Valor Esperado: 10.5 g/dL (fuera de 12-16, pero no panico)")

# ORDEN 3: PACIENTE 3 - VALORES DE PÁNICO (ROJO CON MODAL)
orden3 = OrdenDeServicio.objects.create(
    empresa=empresa,
    sucursal=sucursal,
    paciente=paciente3,
    folio_orden=f"ORD-{date.today().strftime('%Y%m%d')}-{timestamp}-003",
    estado='PAGADO',
    total=Decimal('150.00'),
    responsable_ingreso=admin_user
)
DetalleOrden.objects.create(
    orden=orden3,
    estudio=estudio_glucosa,
    precio_momento=Decimal('150.00')
)
print(f"   [OK] ORDEN 3: {orden3.folio_orden}")
print(f"      ------ Paciente: {paciente3.nombre_completo}")
print(f"      ------ Estudio: Glucosa")
print(f"      ------ Escenario: VALOR CRITICO (Rojo + Modal) [!!!]")
print(f"      ------ Valor Esperado: 500 mg/dL (>400 = PANICO)")

# ORDEN 4: PACIENTE 4 - PEDIÁTRICO
orden4 = OrdenDeServicio.objects.create(
    empresa=empresa,
    sucursal=sucursal,
    paciente=paciente4,
    folio_orden=f"ORD-{date.today().strftime('%Y%m%d')}-{timestamp}-004",
    estado='PAGADO',
    total=Decimal('150.00'),
    responsable_ingreso=admin_user
)
DetalleOrden.objects.create(
    orden=orden4,
    estudio=estudio_glucosa,
    precio_momento=Decimal('150.00')
)
print(f"   [OK] ORDEN 4: {orden4.folio_orden}")
print(f"      ------ Paciente: {paciente4.nombre_completo}")
print(f"      ------ Estudio: Glucosa")
print(f"      ------ Escenario: PACIENTE PEDIATRICO")
print(f"      ------ Valor Esperado: 90 mg/dL (rango pediatrico: 60-110)")

# ORDEN 5: PACIENTE 5 - ADULTO MAYOR
orden5 = OrdenDeServicio.objects.create(
    empresa=empresa,
    sucursal=sucursal,
    paciente=paciente5,
    folio_orden=f"ORD-{date.today().strftime('%Y%m%d')}-{timestamp}-005",
    estado='PAGADO',
    total=Decimal('120.00'),
    responsable_ingreso=admin_user
)
DetalleOrden.objects.create(
    orden=orden5,
    estudio=estudio_hemoglobina,
    precio_momento=Decimal('120.00')
)
print(f"   [OK] ORDEN 5: {orden5.folio_orden}")
print(f"      ------ Paciente: {paciente5.nombre_completo}")
print(f"      ------ Estudio: Hemoglobina")
print(f"      ------ Escenario: ADULTO MAYOR")
print(f"      ------ Valor Esperado: 14.0 g/dL (dentro de rango)")

# ============================================================================
# 7. RESUMEN FINAL
# ============================================================================
print("\n" + "="*70)
print("[OK] DATOS DE PRUEBA CREADOS EXITOSAMENTE")
print("="*70)

print("\nESTADISTICAS:")
print(f"   - Empresas: 1")
print(f"   - Sucursales: 1")
print(f"   - Pacientes: 5 (diferentes edades y sexos)")
print(f"   - Secciones: 2")
print(f"   - Estudios: 2 (Glucosa, Hemoglobina)")
print(f"   - Parametros: 2")
print(f"   - Rangos de Referencia: 4 (con valores de panico)")
print(f"   - Ordenes: 5 (5 escenarios diferentes)")

print("\nESCENARIOS DE VALIDACION:")
print(f"   1. ORDEN {orden1.folio_orden}: Valores NORMALES (Verde) [OK]")
print(f"   2. ORDEN {orden2.folio_orden}: Valores FUERA DE RANGO (Amarillo) [!!]")
print(f"   3. ORDEN {orden3.folio_orden}: Valores CRITICOS (Rojo + Modal) [!!!]")
print(f"   4. ORDEN {orden4.folio_orden}: Paciente PEDIATRICO (8 años)")
print(f"   5. ORDEN {orden5.folio_orden}: Paciente ADULTO MAYOR (75 años)")

print("\nVALORES DE PRUEBA SUGERIDOS:")
print(f"\n   ORDEN 1 ({orden1.folio_orden}) - NORMAL:")
print(f"      Glucosa: 85 mg/dL -�� Verde [OK]")
print(f"\n   ORDEN 2 ({orden2.folio_orden}) - ALERTA:")
print(f"      Hemoglobina: 10.5 g/dL -�� Amarillo [!!] (fuera de 12-16)")
print(f"\n   ORDEN 3 ({orden3.folio_orden}) - PANICO:")
print(f"      Glucosa: 500 mg/dL -�� Rojo [!!!] + MODAL ISO 15189")
print(f"      (Debe aparecer: SweetAlert + Modal de Notificacion)")
print(f"\n   ORDEN 4 ({orden4.folio_orden}) - PEDIATRICO:")
print(f"      Glucosa: 90 mg/dL -�� Verde [OK] (rango pediatrico: 60-110)")
print(f"\n   ORDEN 5 ({orden5.folio_orden}) - ADULTO MAYOR:")
print(f"      Hemoglobina: 14.0 g/dL -�� Verde [OK]")

print("\nACCESO AL SISTEMA:")
print(f"   URL: http://127.0.0.1:8000/login/")
print(f"   Usuario: admin")
print(f"   Password: admin123")

print("\nPROXIMOS PASOS PARA VALIDAR:")
print(f"   1. Login en el sistema")
print(f"   2. Ir a: Laboratorio > Captura de Resultados")
print(f"   3. Seleccionar ORDEN 1 y capturar: Glucosa = 85 -�� Debe ser VERDE")
print(f"   4. Seleccionar ORDEN 2 y capturar: Hemoglobina = 10.5 -�� Debe ser AMARILLO")
print(f"   5. Seleccionar ORDEN 3 y capturar: Glucosa = 500 -�� Debe ser ROJO + MODAL")
print(f"   6. En ORDEN 3, registrar notificacion en el modal")
print(f"   7. Verificar en: Laboratorio > Imprimir PDF de cualquier orden")
print(f"      ------ Debe aparecer: Q.F.B. GISELL MARGATITA LOPEZ GUTIERRES")
print(f"      ------ Cedula: 9439502")
print(f"      ------ Universidad: UNIVERSIDAD VERACRUZANA")

print("\n" + "="*70)
print("SISTEMA LISTO PARA VALIDACION COMPLETA")
print("="*70)



