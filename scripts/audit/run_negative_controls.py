#!/usr/bin/env python
"""
PRISLAB Audit Negative Controls

Siembra intencional de defectos en entorno descartable.
Verifica que los detectors (tests, gates) atrapan cada siembra.

Uso:
    python scripts/audit/run_negative_controls.py --mode dry-run
    python scripts/audit/run_negative_controls.py --mode execute

Salida:
    audit/negative-controls/results.json
"""

import json
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
import shutil
import argparse


class NegativeControl:
    """Representa una siembra intencional de defecto."""
    
    def __init__(self, name, description, file_path, original_code, malicious_code, detector_test):
        self.name = name
        self.description = description
        self.file_path = file_path
        self.original_code = original_code
        self.malicious_code = malicious_code
        self.detector_test = detector_test  # Test que debe detectar el defecto
        self.result = None
        self.detected = False


def control_1_missing_tenant_filter():
    """
    Siembra 1: Remover filtro de empresa en manager.
    Detector: tests/test_tenant_isolation.py::test_product_manager_filters_by_company
    """
    return NegativeControl(
        name="CONTROL_1_MISSING_TENANT_FILTER",
        description="Remover filtro de empresa en ProductManager",
        file_path="farmacia/models.py",
        original_code="""class ProductManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(empresa=self.tenant_empresa)""",
        malicious_code="""class ProductManager(models.Manager):
    def get_queryset(self):
        # MALINTENCIONADO: Sin filtro empresa
        return super().get_queryset()""",
        detector_test="core.tests.test_tenant_isolation::test_product_cross_company_leak"
    )


def control_2_bypass_dinero_validation():
    """
    Siembra 2: Bypass de validación de dinero.
    Detector: farmacia.tests.test_venta::test_venta_max_amount_validation
    """
    return NegativeControl(
        name="CONTROL_2_BYPASS_DINERO_VALIDATION",
        description="Permitir valor de venta fuera de rango",
        file_path="farmacia/models.py",
        original_code="""class Venta(models.Model):
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    def clean(self):
        if self.total > 999999.99:
            raise ValidationError('Monto excede límite')""",
        malicious_code="""class Venta(models.Model):
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    def clean(self):
        # MALINTENCIONADO: No valida monto
        pass""",
        detector_test="farmacia.tests.test_venta::test_venta_exceeds_maximum_amount"
    )


def control_3_append_only_bypass():
    """
    Siembra 3: Permite editar resultado ya validado.
    Detector: laboratorio.tests.test_lims::test_resultado_immutable_after_validation
    """
    return NegativeControl(
        name="CONTROL_3_APPEND_ONLY_BYPASS",
        description="Remover protección append-only en Resultado",
        file_path="laboratorio/models.py",
        original_code="""class Resultado(models.Model):
    valor = models.CharField(max_length=100)
    validado = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if self.validado and self.pk:
            raise ValidationError('No puede modificarse resultado validado')
        super().save(*args, **kwargs)""",
        malicious_code="""class Resultado(models.Model):
    valor = models.CharField(max_length=100)
    validado = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        # MALINTENCIONADO: Permite edición sin restricción
        super().save(*args, **kwargs)""",
        detector_test="laboratorio.tests.test_lims::test_resultado_immutable_after_validation"
    )


def control_4_csrf_bypass():
    """
    Siembra 4: Bypass de CSRF en venta.
    Detector: farmacia.tests.test_views::test_venta_post_requires_csrf
    """
    return NegativeControl(
        name="CONTROL_4_CSRF_BYPASS",
        description="Remover verificación CSRF en POST de venta",
        file_path="farmacia/views.py",
        original_code="""@require_http_methods(["GET", "POST"])
@csrf_protect
def venta_create(request):
    if request.method == 'POST':
        # CSRF check automático por @csrf_protect
        venta = Venta.objects.create(...)""",
        malicious_code="""@require_http_methods(["GET", "POST"])
@csrf_exempt  # MALINTENCIONADO
def venta_create(request):
    if request.method == 'POST':
        venta = Venta.objects.create(...)""",
        detector_test="farmacia.tests.test_views::test_venta_csrf_protection"
    )


def control_5_sql_injection_risk():
    """
    Siembra 5: Uso de raw SQL sin sanitización.
    Detector: core.tests.test_security::test_no_raw_sql_in_critical_paths
    """
    return NegativeControl(
        name="CONTROL_5_SQL_INJECTION_RISK",
        description="Query SQL sin parametrizar",
        file_path="laboratorio/views.py",
        original_code="""results = Resultado.objects.filter(laboratorio_id=lab_id)""",
        malicious_code="""# MALINTENCIONADO: SQL sin parametrización
from django.db import connection
cursor = connection.cursor()
cursor.execute(f"SELECT * FROM laboratorio_resultado WHERE laboratorio_id={lab_id}")
results = cursor.fetchall()""",
        detector_test="core.tests.test_security::test_no_raw_sql_queries"
    )


def execute_control(control, mode="dry-run"):
    """
    Ejecuta una siembra y verifica detección.
    
    Pasos:
    1. Backup del archivo original
    2. Inyectar código malicioso
    3. Ejecutar detector test
    4. Restaurar original
    5. Registrar resultado
    """
    print(f"\n🧪 Ejecutando: {control.name}")
    print(f"   Descripción: {control.description}")
    print(f"   Archivo: {control.file_path}")
    print(f"   Detector: {control.detector_test}")
    
    if mode == "dry-run":
        print(f"   [DRY-RUN] No se inyectará código")
        control.result = "skipped"
        return control
    
    # Backup
    backup_path = f"{control.file_path}.backup"
    try:
        shutil.copy(control.file_path, backup_path)
        print(f"   ✅ Backup creado: {backup_path}")
    except Exception as e:
        print(f"   ❌ Error en backup: {e}")
        control.result = "backup_failed"
        return control
    
    try:
        # Inyectar código malicioso
        with open(control.file_path, 'r') as f:
            original_content = f.read()
        
        # Reemplazar código
        modified_content = original_content.replace(
            control.original_code,
            control.malicious_code
        )
        
        if modified_content == original_content:
            print(f"   ⚠️ No se pudo encontrar patrón a reemplazar")
            control.result = "pattern_not_found"
            return control
        
        with open(control.file_path, 'w') as f:
            f.write(modified_content)
        
        print(f"   ✅ Código malicioso inyectado")
        
        # Ejecutar test detector
        print(f"   🔍 Ejecutando detector: {control.detector_test}")
        result = subprocess.run(
            ["python", "manage.py", "test", control.detector_test, "-v", "2"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Verificar si el test FALLÓ (es lo esperado)
        if result.returncode != 0:
            print(f"   ✅ DETECTOR FUNCIONÓ: Test falló como se esperaba")
            control.detected = True
            control.result = "success_detected"
        else:
            print(f"   ❌ DETECTOR FALLÓ: Test pasó (no detectó defecto)")
            control.detected = False
            control.result = "failure_not_detected"
        
        # Mostrar output
        if result.stdout:
            print(f"   Stdout: {result.stdout[:200]}...")
        if result.stderr:
            print(f"   Stderr: {result.stderr[:200]}...")
    
    except subprocess.TimeoutExpired:
        print(f"   ❌ Test timeout")
        control.result = "timeout"
    except Exception as e:
        print(f"   ❌ Error durante inyección: {e}")
        control.result = "injection_failed"
    finally:
        # Restaurar original
        try:
            shutil.move(backup_path, control.file_path)
            print(f"   ✅ Original restaurado")
        except Exception as e:
            print(f"   ❌ Error restaurando: {e}")
    
    return control


def run_negative_controls(mode="dry-run"):
    """
    Ejecuta todas las siembras.
    """
    print("\n" + "="*70)
    print("🧪 PRISLAB AUDIT - NEGATIVE CONTROLS")
    print("="*70)
    print(f"Modo: {mode.upper()}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    
    controls = [
        control_1_missing_tenant_filter(),
        control_2_bypass_dinero_validation(),
        control_3_append_only_bypass(),
        control_4_csrf_bypass(),
        control_5_sql_injection_risk(),
    ]
    
    results = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": mode,
        "controls": [],
        "summary": {
            "total": len(controls),
            "detected": 0,
            "not_detected": 0,
            "errors": 0,
        }
    }
    
    for control in controls:
        execute_control(control, mode=mode)
        
        control_dict = {
            "name": control.name,
            "description": control.description,
            "file_path": control.file_path,
            "detector_test": control.detector_test,
            "detected": control.detected,
            "result": control.result,
        }
        results["controls"].append(control_dict)
        
        # Actualizar resumen
        if control.result == "success_detected":
            results["summary"]["detected"] += 1
        elif control.result == "failure_not_detected":
            results["summary"]["not_detected"] += 1
        else:
            results["summary"]["errors"] += 1
    
    # Guardar resultados
    output_path = Path("audit/negative-controls")
    output_path.mkdir(parents=True, exist_ok=True)
    
    results_file = output_path / "results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*70)
    print("📊 RESUMEN")
    print("="*70)
    print(f"Total: {results['summary']['total']}")
    print(f"Detectados: {results['summary']['detected']}")
    print(f"No detectados: {results['summary']['not_detected']}")
    print(f"Errores: {results['summary']['errors']}")
    print(f"\nResultados guardados en: {results_file}")
    
    # Fallar si hay no detectados en modo execute
    if mode == "execute" and results['summary']['not_detected'] > 0:
        print(f"\n❌ FALLÓ: {results['summary']['not_detected']} defectos no fueron detectados")
        return 1
    
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PRISLAB Audit Negative Controls")
    parser.add_argument("--mode", choices=["dry-run", "execute"], default="dry-run",
                       help="Modo: dry-run (sin inyectar) o execute (inyectar y verificar)")
    
    args = parser.parse_args()
    
    try:
        sys.exit(run_negative_controls(mode=args.mode))
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
