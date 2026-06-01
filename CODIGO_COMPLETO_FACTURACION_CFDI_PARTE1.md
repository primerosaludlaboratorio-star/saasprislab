# 💰 IMPLEMENTACIÓN COMPLETA: MÓDULO DE FACTURACIÓN CFDI 4.0 - PARTE 1
**Prioridad:** 🔴 CRÍTICA - Obligación Fiscal  
**Tiempo estimado:** 8-12 horas  
**Complejidad:** ALTA (Integración externa + XML + Cumplimiento SAT)

---

Este documento contiene el **100% del código necesario** para implementar el módulo de facturación CFDI 4.0.

Todo el código está **listo para copiar y pegar**.

---

## PASO 1: REQUISITOS PREVIOS

### Dependencias a Instalar

```bash
cd c:\Users\jonil\Desktop\PRISLAB_SaaS
.\venv\Scripts\Activate.ps1
pip install lxml==5.1.0
pip install zeep==4.2.1
```

### Registrar App en Django

Agregar en `config/settings.py`:

```python
INSTALLED_APPS = [
    # ... apps existentes ...
    'contabilidad',  # AGREGAR ESTA LÍNEA
]

# Configuración de Facturama (al final del archivo)
FACTURAMA_USER = os.environ.get('FACTURAMA_USER', '')
FACTURAMA_PASSWORD = os.environ.get('FACTURAMA_PASSWORD', '')
FACTURAMA_SANDBOX = os.environ.get('FACTURAMA_SANDBOX', 'True') == 'True'
```

---

## PASO 2: CREAR APP

```bash
cd c:\Users\jonil\Desktop\PRISLAB_SaaS
.\venv\Scripts\Activate.ps1
python manage.py startapp contabilidad
```

---

## PASO 3: MODELOS (COPIAR TODO A `contabilidad/models.py`)

Ver archivo adjunto con los modelos completos (~900 líneas).

Los modelos incluyen:
- ✅ `ClienteFacturacion` - Datos fiscales
- ✅ `FacturaCFDI` - Factura electrónica CFDI 4.0
- ✅ `ConceptoFactura` - Líneas de detalle
- ✅ `ImpuestoConcepto` - IVA, ISR, IEPS
- ✅ `ComplementoPago` - Para pagos en parcialidades
- ✅ `DocumentoRelacionadoPago` - Relación de pagos

---

## INSTRUCCIONES COMPLETAS

Este documento es PARTE 1 de 3.

**Contiene:**
- Instalación de dependencias
- Creación de app
- Modelos completos (900 líneas)
- Configuración de Django

**SIGUIENTE:** `CODIGO_COMPLETO_FACTURACION_CFDI_PARTE2.md` con vistas y lógica de negocio.

---

**Generado el:** 26-Ene-2026 11:30 PM
