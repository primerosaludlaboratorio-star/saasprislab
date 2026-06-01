# Bloque 4 - Automatización de Pruebas (Playwright y Cobertura)
## PRISLAB SaaS v5.0 - Auditoría de Seguridad

**Fecha:** Mayo 2026  
**Auditor:** Cascade (Auditor Programador Nivel 5)  
**Estado:** ✅ Completado (Documentación)

---

## 1. Suite de Pruebas E2E - Omni Tester

### Componentes

| Componente | Archivo | Tecnología | Descripción |
|------------|---------|------------|-------------|
| Omni Runner | `tools/run_omni_suite.mjs` | Node.js/Playwright | Runner principal de E2E |
| E2E Tests | `scripts_cursor_e2e/tests/` | Python/Selenium | 10 módulos de prueba |
| Configuración | `package.json` | npm | Scripts: `omni:local`, `omni:cloud` |

### Scripts npm Disponibles

```json
{
  "test": "node --check tools/run_omni_suite.mjs",
  "omni:local": "node tools/run_omni_suite.mjs --target local",
  "omni:cloud": "node tools/run_omni_suite.mjs --target cloud",
  "omni:both": "node tools/run_omni_suite.mjs --target both"
}
```

### Uso del Omni Suite

```bash
# Local (requiere servidor Django corriendo en :8000)
python manage.py runserver &
npm run omni:local -- --user admin --pass PrislabV5_2026

# Cloud (producción)
npm run omni:cloud -- --base https://prislab-v5-xxx.run.app --user admin --pass ***

# Ambos
npm run omni:both -- --user admin --pass ***
```

---

## 2. Módulos de Prueba E2E (scripts_cursor_e2e)

### Lista de Tests (10 módulos)

| # | Archivo | Cobertura | Prioridad |
|---|---------|-----------|-----------|
| 1 | `test_01_guardian_golden_lifecycle.py` | Ciclo de vida completo | Alta |
| 2 | `test_02_lims_inventory_sync.py` | Sincronización LIMS/Inventario | Alta |
| 3 | `test_03_math_ui_integrity.py` | Integridad cálculos UI | Media |
| 4 | `test_04_finance_caja_sync.py` | Sincronización finanzas/caja | Alta |
| 5 | `test_05_hl7_mock_device.py` | Simulador HL7 | Media |
| 6 | `test_06_role_permission_hygiene.py` | Higiene de permisos | Alta |
| 7 | `test_07_pdf_branding_consistency.py` | Consistencia PDF/marca | Media |
| 8 | `test_08_jarvis_escudo_ui.py` | UI Escudo JARVIS | Media |
| 9 | `test_09_sucursal_modo_inventario_ui.py` | UI Modo inventario | Media |
| 10 | `test_robot_chemist_flows.py` | Flujos químico automatizado | Media |

### Ejecución de Tests Python E2E

```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Ejecutar suite de confiabilidad
python scripts_cursor_e2e/run_cursor_reliability_suite.py

# O ejecutar tests individuales
python -m pytest scripts_cursor_e2e/tests/test_01_guardian_golden_lifecycle.py -v
```

---

## 3. Dependencias de Pruebas

### requirements-dev.txt

```
beautifulsoup4>=4.12.0      # Parseo HTML para assertions
selenium>=4.15.0            # E2E browser automation
webdriver-manager>=4.0.0   # ChromeDriver auto-management
pytest>=8.0.0              # Framework de tests
coverage[toml]>=7.4.0       # Medición de cobertura
```

### Instalación Completa

```bash
# Producción
pip install -r requirements.txt

# Desarrollo (+ pruebas)
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Playwright (Node.js)
npm install
npx playwright install
```

---

## 4. Cobertura de Código

### Comandos de Cobertura

```bash
# Ejecutar tests con cobertura
coverage run manage.py test

# Reporte en consola
coverage report -m

# Reporte con umbral mínimo (falla si < 50%)
coverage report -m --fail-under=50

# Reporte HTML detallado
coverage html
# Abrir htmlcov/index.html

# Reporte XML (para CI/CD)
coverage xml
```

### Configuración Sugerida (.coveragerc)

```ini
[run]
source = .
omit = 
    */venv/*
    */migrations/*
    */tests/*
    */settings.py
    */wsgi.py
    */asgi.py

[report]
exclude_lines =
    pragma: no cover
    def __str__
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:
    if DEBUG:
    if settings.DEBUG:

show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

### Objetivos de Cobertura

| Fase | Umbral | Estado |
|------|--------|--------|
| Inicial | 50% | 🟡 Mínimo aceptable |
| Intermedio | 70% | 🟢 Bueno |
| Óptimo | 85%+ | 🟢 Excelente |

---

## 5. Procedimiento de Ejecución Completa

### Paso 1: Instalación

```bash
# 1. Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. Node.js dependencies
npm install

# 3. Playwright browsers
npx playwright install chromium
```

### Paso 2: Preparación de BD

```bash
# SQLite (desarrollo)
python manage.py migrate

# O PostgreSQL (si está configurado)
python manage.py migrate
python manage.py createsuperuser

# Cargar datos de prueba (opcional)
python manage.py migrar_lab_completo
python cargar_tarifas.py
```

### Paso 3: Levantar Servidor

```bash
# Terminal 1: Servidor Django
python manage.py runserver 0.0.0.0:8000
```

### Paso 4: Ejecutar E2E

```bash
# Terminal 2: Tests E2E
npm run omni:local -- --user admin --pass admin123

# O con Python puro
python -m pytest scripts_cursor_e2e/tests/ -v
```

### Paso 5: Cobertura

```bash
# Terminal 3: Cobertura
coverage run manage.py test
coverage report -m
```

---

## 6. Resultados Esperados

### Omni Suite (npm run omni:local)

**Salida Exitosa:**
```
[omni] start: api_smoke (node _audit_api_smoke.mjs)
[omni] end:   api_smoke (ms=5234, status=0)
[omni] start: farmacia_full (node _audit_farmacia_full.mjs)
[omni] end:   farmacia_full (ms=8912, status=0)
[omni] start: pdv_audit (node _e2e_pdv_audit.mjs)
[omni] end:   pdv_audit (ms=12453, status=0)
...
Resumen: 5/5 auditors PASSED
```

### Errores Comunes y Soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `net::ERR_CONNECTION_REFUSED` | Servidor no corriendo | `python manage.py runserver` |
| `login failed: redirectedToLogin` | Credenciales incorrectas | Verificar usuario/contraseña |
| `timeout 120000ms` | Servidor lento | Aumentar OMNI_TIMEOUT_MS |
| `browser not found` | Playwright no instalado | `npx playwright install` |

### Cobertura Esperada

```
Name                                          Stmts   Miss  Cover   Missing
---------------------------------------------------------------------------
core/models.py                                  450    120    73%
core/views.py                                   380    200    47%
laboratorio/models.py                           280     80    71%
farmacia/models.py                              220     60    73%
...
---------------------------------------------------------------------------
TOTAL                                          5000   2500    50%
```

---

## 7. Integración CI/CD

### GitHub Actions (Sugerido)

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'
      
      - name: Install Dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
          npm install
          npx playwright install chromium
      
      - name: Setup Database
        run: |
          python manage.py migrate
          python manage.py createsuperuser --noinput --username admin --email test@test.com
      
      - name: Start Server
        run: python manage.py runserver 0.0.0.0:8000 &
      
      - name: Run E2E
        run: npm run omni:local -- --user admin --pass admin
      
      - name: Coverage
        run: |
          coverage run manage.py test
          coverage report -m --fail-under=50
```

---

## 8. Documentación de Tests

### README para Auditoría Externa

**Archivo:** `scripts_cursor_e2e/README_CURSOR_E2E.txt`

```
PRISLAB - Suite E2E Cursor
==========================

Este directorio contiene tests E2E para validación del sistema.

Ejecución:
    python run_cursor_reliability_suite.py

Tests Individuales:
    python tests/test_01_guardian_golden_lifecycle.py
    python tests/test_02_lims_inventory_sync.py
    ...

Requisitos:
    - Servidor Django corriendo en :8000
    - Chrome/Chromium instalado
    - Usuario admin creado
```

---

## Checklist Bloque 4

- [ ] Instalar Playwright: `npx playwright install`
- [ ] Levantar servidor Django: `python manage.py runserver`
- [ ] Ejecutar `npm run omni:local` (esperar resultado)
- [ ] Ejecutar `coverage run manage.py test`
- [ ] Generar reporte HTML: `coverage html`
- [ ] Verificar umbral mínimo 50%
- [ ] Documentar fallos encontrados
- [ ] Crear `docs/E2E_GUIDE.md` para auditoría externa

---

## Resumen de Estado

| Componente | Estado | Notas |
|------------|--------|-------|
| Omni Suite | ✅ Configurado | Playwright + Node.js |
| Tests Python | ✅ 10 módulos | Selenium E2E |
| Cobertura | ⚠️ Pendiente ejecutar | Configuración lista |
| CI/CD | 📝 Plantilla creada | GitHub Actions |
| Documentación | ✅ README existe | `README_CURSOR_E2E.txt` |

---

**Fin del Reporte Bloque 4**
**Estado:** ✅ Documentación completa - Ejecución de pruebas pendiente

---

## Próximos Pasos (Bloque 5)

1. **Ejecutar pruebas reales** para obtener métricas de cobertura
2. **Verificar flujos críticos** (recepción → laboratorio → farmacia)
3. **Validar mensajes de error** honestos
4. **Prueba de accesibilidad** básica

---

*Generado automáticamente por Cascade - Auditoría PRISLAB SaaS*
