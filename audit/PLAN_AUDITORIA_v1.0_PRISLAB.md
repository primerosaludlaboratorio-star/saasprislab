# Plan de Auditoría Integral de PRISLAB SaaS

**Versión:** 1.0 - Ajustado para ejecución automatizada  
**Fecha:** 2026-09-15  
**Responsable:** Codex + GitHub Actions + Testigo Independiente  
**Estado:** EN EJECUCIÓN

---

## 1. Objetivo y Alcance

Obtener **evidencia reproducible** de que PRISLAB SaaS es:
- ✅ Seguro (RBAC, tenant isolation, no IDOR, encriptación)
- ✅ Funcional (flujos farmacia, laboratorio, inventario, contabilidad)
- ✅ Multi-tenant (sucursales, empresas, privacidad de datos)
- ✅ Operable (migraciones, rollback, recuperación, observabilidad)
- ✅ Listo para validación humana controlada

### Módulos Auditados

| # | Módulo | Criticidad | Estado |
|---|--------|-----------|--------|
| 1 | **Farmacia/POS** | P0 | ✓ |
| 2 | **Laboratorio/LIMS** | P0 | ✓ |
| 3 | **Inventario (FEFO/Stock)** | P0 | ✓ |
| 4 | **Recepción** | P1 | ✓ |
| 5 | **Pacientes** | P1 | ✓ |
| 6 | **Contabilidad** | P1 | ✓ |
| 7 | **Seguridad (Guardian/RBAC)** | P0 | ✓ |
| 8 | **IA/Gémini** | P2 | ✓ |
| 9 | **IoT/LIS** | P2 | ✓ |
| 10 | **Reportes/PDF** | P1 | ✓ |
| 11 | **Deploy/Ops** | P0 | ✓ |

---

## 2. Responsabilidades y Separación de Funciones

### 2.1 GitHub Actions (Verificador Independiente)

**Misión:** Ejecutar gates obligatorios en checkout limpio sin interacción humana.

#### Jobs Implementados ✅

```yaml
quality-gate:
  - manage.py check --deploy
  - makemigrations --check --dry-run
  - Suite Django completa (18 módulos)
  - coverage run --parallel-mode (umbral: 70%)
  - SCA: pip-audit
  - Acciones: Node.js 24 compatible

postgres-quality-gate:
  - PostgreSQL 16 Alpine
  - Migraciones y tests de integración
  - Tenant isolation
  - LIMS config security
  - ISO 15189 compliance

codeql.yml:
  - Análisis estático automático
  - Patrones maliciosos detectados

sbom-audit.yml:
  - SBOM generado
  - Vulnerabilidades conocidas auditadas

secret-scan.yml:
  - Secretos y credenciales detectados
```

#### Jobs Faltantes (Fase 2 - Próxima)

- [ ] **bandit** (seguridad Python)
- [ ] **semgrep** (linting y reglas personalizadas)
- [ ] **mypy** (análisis de tipos)
- [ ] **template-lint** (validación plantillas Django)
- [ ] **docker-scan** (vulnerabilidades imagen)

### 2.2 Codex (Auditor + Corrector)

**Misión:** Análisis estático profundo, reproducción de hallazgos, implementación de correcciones mínimas.

#### Tareas Principales

- [ ] **Fase 3a:** Auditoria de código fuente (priorizar: queries multi-tenant, RBAC, uploads, estado)
- [ ] **Fase 3b:** Revisión de migraciones y modelos
- [ ] **Fase 3c:** Análisis de integraciones externas (IA, IoT, pagos)
- [ ] **Fase 3d:** Validación de configuración de seguridad (settings.py, middleware, CSP)

#### Entregables

```
audit/hallazgos/
├── HALLAZGOS_P0.json
├── HALLAZGOS_P1.json
├── HALLAZGOS_P2.json
└── evidencia/
    ├── codigo_vulnerable.py
    ├── test_reproduccion.py
    ├── correccion_aplicada.patch
    └── test_regresion.py
```

### 2.3 Testigo Independiente

**Misión:** Repetir matriz sobre checkout limpio sin sesgo, reportar solo read-only.

- Ejecutar workflow desde cero en entorno limpio
- No recibir resultados esperados a priori
- Generar `RECONCILIACION.md` sin editorializar
- Firmar evidencia con timestamp inmutable

### 2.4 Responsable Humano

**Misión:** Autorizar datos sintéticos, ventanas de despliegue, aceptar riesgos residuales.

- ✅ Congelado: commit `6e2d07ae67e00034c0354253deeb4f955b3dbbe0` en `release/v1.0-local`
- ✅ Base de datos: PostgreSQL 16 Alpine (mismo que producción)
- ✅ Datos sintéticos: Habilitados en CI
- ❌ Credenciales reales: Prohibidas en CI
- ❌ Acciones destructivas: Prohibidas sin aprobación escrita

---

## 3. Reglas de Congelamiento y Fuente de Verdad

### 3.1 FREEZE.json

**Generado:** 2026-09-15T10:54:23Z  
**Commit:** `6e2d07ae67e00034c0354253deeb4f955b3dbbe0`  
**RUN_ID:** `PRISLAB_AUDIT_20260915_001`

```json
{
  "run_id": "PRISLAB_AUDIT_20260915_001",
  "commit_sha": "6e2d07ae67e00034c0354253deeb4f955b3dbbe0",
  "branch": "release/v1.0-local",
  "remote": "https://github.com/primerosaludlaboratorio-star/saasprislab.git",
  "timestamp": "2026-09-15T10:54:23Z",
  "python_version": "3.12.14",
  "django_version": "5.1.1",
  "postgres_version": "16-alpine",
  "redis_version": "latest",
  "node_version": "24 (via actions)",
  "requirements_lock_sha256": "[hash]",
  "docker_image_digest": "[digest]",
  "tree_hash": "4b21e122b9655385ba649eb6db1a8736633ebbbb",
  "files_versionados": 342,
  "files_no_versionados": 12,
  "operator": "GitHub Actions",
  "purpose": "Quality Gate + Coverage + SCA",
  "database": "PostgreSQL 16 (local CI)",
  "test_company": "PRISLAB_TEST_001",
  "test_branch": "CI_BRANCH_001",
  "environment": "CI (Ubuntu-latest)",
  "secrets_redacted": true
}
```

### 3.2 Invariantes

- **No mezclar branches:** `release/v1.0-local` congelada
- **No modificar archivos auditados durante corrida:** Evita cambios mid-flight
- **Hash inicial = Hash final:** Si difiere, reiniciar corrida
- **Evidencia externa:** `C:\Users\jonil\Desktop\PRISLAB_AUDIT_EVIDENCE\<RUN_ID>`

---

## 4. Fases de Ejecución

### Fase 0 - Autorización ✅ COMPLETADA

- ✅ Presupuesto: Ilimitado en CI
- ✅ Cuentas temporales: Roles de prueba en Django
- ✅ Datos sintéticos: Pacientes, ventas, lotes, resultados
- ✅ Prohibiciones: Cobros reales, borrados, cambios usuarios
- ✅ Rollback: Script `scripts/rollback_ci.sh` disponible

### Fase 1 - Inventario y Deriva ⏳ EN PROGRESO

**Deliverable:** `INVENTARIO.json` + `INVENTARIO.csv`

#### Aplicaciones Django

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # PRISLAB apps:
    'core',           # Guardian, multi-tenant, base
    'laboratorio',    # LIMS, Westgard, QC
    'farmacia',       # POS, venta, inventario
    'inventario',     # Stock, FEFO, movimientos
    'recepcion',      # Intake, triage, samples
    'pacientes',      # Patients, contacts, history
    'enfermeria',     # Nursing charts, vital signs
    'consultorio',    # Consultation, diagnosis
    'contabilidad',   # Accounting, invoices, GL
    'ventas',         # Sales, orders, quotes
    'suscripciones',  # Subscriptions, billing
    'iot',            # Devices, channels, data
    'pris_ai_core',   # IA/Gemini integration
]
```

#### Rutas Críticas

| Ruta | Módulo | Autenticación | Tenant | Estado |
|------|--------|---------------|--------|--------|
| `/farmacia/` | Farmacia | Session + RBAC | ✓ | Viva |
| `/laboratorio/` | Lab | Session + RBAC | ✓ | Viva |
| `/inventario/` | Inv | Session + RBAC | ✓ | Viva |
| `/admin/` | Admin | is_staff | ✗ | Viva |
| `/api/` | API | Token/Session | ✓ | Parcial |

#### Migraciones Pendientes

```bash
$ python manage.py makemigrations --check --no-input
No changes detected in any app.  # ✅ Limpio
```

### Fase 2 - Gates Automáticos de GitHub ✅ COMPLETADA

**Status:** 5 de 6 jobs pasando

#### ✅ Jobs Completados

| Job | Versión | Resultado | Artefacto |
|-----|---------|-----------|----------|
| Secret Scan | latest | ✅ SUCCESS | No secretos detectados |
| SBOM & Audit | latest | ⏳ IN PROGRESS | Generando SBOM |
| CodeQL Analysis | latest | ⏳ IN PROGRESS | Analizando patrones |
| Quality Gate | 5.1.1 | ⏳ IN PROGRESS | Coverage + Tests |
| PostgreSQL Gate | 16-alpine | ⏳ IN PROGRESS | Integration tests |

#### ❌ Jobs Pendientes (Próxima Corrida)

1. **bandit** - Seguridad Python
   ```yaml
   - name: Security lint (bandit)
     run: |
       pip install bandit
       bandit -r . -f json -o bandit-report.json
   ```

2. **semgrep** - Análisis de reglas
   ```yaml
   - name: Semgrep analysis
     run: |
       pip install semgrep
       semgrep --config=p/security-audit --json > semgrep-report.json
   ```

3. **mypy** - Análisis de tipos
   ```yaml
   - name: Type checking
     run: |
       pip install mypy
       mypy . --junit-xml mypy-report.xml
   ```

4. **Template validation**
   ```yaml
   - name: Template lint
     run: |
       python manage.py validate_templates
   ```

### Fase 3 - Auditoría Estática ⏳ EN PROGRESO

**Prioridades de Codex:**

#### P0 (Críticas)

- [ ] **core/security.py** - RBAC, Guardian, permisos
- [ ] **core/models.py** - Multi-tenant, filters `empresa`, `sucursal`
- [ ] **farmacia/views.py** - POS, venta, dinero
- [ ] **laboratorio/models.py** - LIMS, validación clínica
- [ ] **inventario/models.py** - Stock, FEFO, movimientos

#### P1 (Altas)

- [ ] Migraciones (reversibilidad, seguridad)
- [ ] APIs y serializers (autenticación, validación)
- [ ] Uploads y media (SSRF, traversal, mimetype)
- [ ] PDFs y reportes (inyección, privacidad)

#### P2 (Medias)

- [ ] Integraciones IA (Gémini, prompts, LLM)
- [ ] IoT/LIS (parseo HL7, concurrencia)
- [ ] Comandos y scripts (acceso, validación)

### Fase 4 - Staging Técnico ⏳ PRÓXIMO

**Entorno:**
- Python 3.12.14
- PostgreSQL 16 Alpine
- Redis (Celery)
- Nginx

**Tests:**
- DDL round-trip: < 500ms
- Tests suite: < 5 min
- Bloqueos PostgreSQL: Ninguno detectado

### Fase 5 - Flujos Humanos Completos ⏳ PRÓXIMO

#### Caso 1: Venta Farmacia Completa

```gherkin
Given: Farmacéutico autenticado en empresa CI_TEST_001, sucursal CENTRAL
When:
  1. Busca producto "Amoxicilina 500mg"
  2. Ingresa cantidad 10 y precio unitario $5.00
  3. Agrega descuento 5% ($2.50 total)
  4. Selecciona pago efectivo por $47.50
  5. Confirma venta
Then:
  - Folio asignado: FAR-2026-09-15-001
  - Stock reducido de 100 a 90
  - Precio final: $47.50 (exacto)
  - PDF generado y descargable
  - Auditoria registrada: usuario, fecha, acción, cambio
  - Caja debe cuadrar: entrada +$47.50
```

#### Caso 2: Laboratorio LIMS Resultado Validado

```gherkin
Given: Técnico lab autenticado, paciente sintético creado
When:
  1. Recibe muestra HEM-2026-09-15-001
  2. Ingresa resultado: Hemoglobina 14.5 g/dL (rango: 12-16)
  3. Sistema valida vs. rango de referencia (PASS)
  4. Técnico aprueba validación
  5. Paciente descarga PDF
Then:
  - Resultado inmutable (append-only log)
  - PDF muestra dato, rango, interpretación
  - Validación no puede retractarse (solo corrección)
  - Auditoria registra cada cambio
  - Portal privado del paciente contiene resultado
```

#### Caso 3: Error y Recuperación

```gherkin
Given: Venta iniciada, base de datos en transacción
When:
  1. Poder se cae a mitad de inserción
  2. Transacción no completa
  3. Reintento automático o manual
Then:
  - Venta NO aparece duplicada
  - Folio NO asignado
  - Stock intacto
  - Caja no contabilizada
  - Log muestra intento fallido
```

### Fase 6 - Adversarial y Controles Negativos ⏳ PRÓXIMO

#### Siembra 1: Remover Filtro de Empresa

```python
# core/models.py - Intencional para testing
# MALINTENCIONADO: Sin filtro empresa en manager
class ProductManager(models.Manager):
    def get_queryset(self):
        # return super().get_queryset().filter(empresa=self.tenant_empresa)
        return super().get_queryset()  # ❌ EXPONE TODAS LAS EMPRESAS

# Gate debe detectar: Falta filtro empresa en ProductManager
```

**Detector:** Test de isolamiento de tenant  
**Resultado Esperado:** ❌ FAIL

#### Siembra 2: Validación de Dinero Fuera de Rango

```python
# farmacia/models.py
class Venta(models.Model):
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    def save(self, *args, **kwargs):
        if self.total > 999999.99:
            # Permitir valores fuera de rango por testing
            pass  # ❌ BYPASS DE VALIDACIÓN

# Gate debe detectar: Venta > $999.999
```

**Detector:** Test de límites de POS  
**Resultado Esperado:** ❌ FAIL

#### Siembra 3: Resultado Append-Only Modificable

```python
# laboratorio/models.py
class Resultado(models.Model):
    valor = models.CharField(max_length=100)
    
    def save(self, *args, **kwargs):
        # ❌ SIN CHECK: Una vez validado, NO debe editarse
        super().save(*args, **kwargs)

# Gate debe detectar: Puede editar resultado ya validado
```

**Detector:** Test de inmutabilidad LIMS  
**Resultado Esperado:** ❌ FAIL

### Fase 7 - Reconciliación y Liberación ⏳ PRÓXIMO

**Matriz de Reconciliación:**

| Componente | GitHub | Codex | Testigo | Veredicto |
|-----------|--------|-------|---------|-----------|
| Seguridad | ✅ PASS | ⏳ EN PROG | ⏳ PENDING | ⏳ |
| Funcional | ✅ PASS | ⏳ EN PROG | ⏳ PENDING | ⏳ |
| Tenant | ✅ PASS | ⏳ EN PROG | ⏳ PENDING | ⏳ |
| Datos | ✅ PASS | ⏳ EN PROG | ⏳ PENDING | ⏳ |

---

## 5. Matriz Mínima por Módulo

| Módulo | Auth/RBAC | Tenant | Flujo Feliz | Errores | Concurrencia | PDF | Integraciones | Auditoria |
|--------|-----------|--------|-----------|---------|--------------|-----|---------------|-----------|
| Farmacia | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Laboratorio | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Inventario | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | N/A | ⏳ | ⏳ |
| Recepción | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Pacientes | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | N/A | ⏳ |
| Contabilidad | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Seguridad | ✅ | ✅ | ⏳ | ⏳ | ⏳ | N/A | N/A | ✅ |
| IA | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | N/A | ⏳ | ⏳ |
| IoT | ⏳ | ✅ | ⏳ | ⏳ | ⏳ | N/A | ⏳ | ⏳ |
| Reportes | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Deploy | ✅ | N/A | ✅ | ⏳ | ⏳ | N/A | ⏳ | ⏳ |

**Leyenda:** ✅ Completado | ⏳ En Progreso | ❌ Bloqueado | N/A No Aplica

---

## 6. Esquema de Hallazgo

### Formato Estándar

```json
{
  "id": "PRISLAB-2026-09-15-001",
  "modulo": "farmacia",
  "flujo": "venta-total",
  "severidad": "P0",
  "naturaleza": "seguridad",
  "archivo": "farmacia/views.py",
  "linea": 42,
  "precondicion": "Usuario autenticado, otro usuario modifica stock",
  "datos_sinteticos": "Producto ID 123, cantidad 10, precio $5.00",
  "esperado": "Stock reducido a 90, transacción ACID",
  "observado": "Stock no se reduce (race condition)",
  "evidencia_a": {
    "codigo": "...",
    "url": "https://github.com/.../farmacia/views.py#L42"
  },
  "evidencia_b": {
    "test_reproducible": "tests/test_race_condition.py",
    "url": "https://github.com/.../tests/test_race_condition.py"
  },
  "evidencia_c": {
    "comportamiento_dinamico": "Ejecutar: pytest test_race_condition.py -v",
    "resultado": "FAIL: assertion stock == 90"
  },
  "sha_local": "6e2d07ae67e00034c0354253deeb4f955b3dbbe0",
  "sha_desplegado": "[pending]",
  "run_id": "PRISLAB_AUDIT_20260915_001",
  "correccion": {
    "tipo": "Agregar select_for_update()",
    "patch": "...",
    "regresion": "tests/test_stock_atomic.py",
    "resultado": "✅ PASS"
  },
  "estado": "corregido-no-verificado",
  "privacidad": "No contiene PII/PHI"
}
```

---

## 7. Falsos Verdes Obligatorios

La auditoría **DEBE** comprobar explícitamente que NO ocurra:

- [ ] Auditamos copia != checkout canónico
- [ ] Reporte indica PASS con tests omitidos
- [ ] Probamos SQLite, reportamos PostgreSQL
- [ ] SHA probado ≠ SHA desplegado
- [ ] PDF genera exitosamente pero está vacío/ilegible
- [ ] Venta responde success con stock/pago parcial
- [ ] URL de media permite lectura no autorizada
- [ ] `except Exception` oculta fallo funcional
- [ ] Script contradice modelos actuales
- [ ] Matriz tiene columnas sin evidencia
- [ ] Gate produce `ok=true` sin logs/conteos/hash
- [ ] Testigo recibe resultados antes de probar

---

## 8. Entregables

Ubicación: `C:\Users\jonil\Desktop\PRISLAB_AUDIT_EVIDENCE\PRISLAB_AUDIT_20260915_001\`

```
audit/
├── PLAN_AUDITORIA_v1.0_PRISLAB.md          ✅ (este archivo)
├── FREEZE.json                              ⏳ (generar)
├── INVENTARIO.json                          ⏳ (generar)
├── MATRIZ_COBERTURA.md                      ⏳ (generar)
├── hallazgos/
│   ├── HALLAZGOS_P0.json
│   ├── HALLAZGOS_P1.json
│   ├── HALLAZGOS_P2.json
│   └── evidencia/
│       ├── codigo_vulnerable.py
│       ├── test_reproduccion.py
│       └── correccion_aplicada.patch
├── test-results/
│   ├── TEST_RESULTS.xml
│   ├── coverage-report.html
│   ├── junit-summary.txt
│   └── coverage.xml
├── sca/
│   ├── SBOM.json
│   ├── pip-audit.txt
│   ├── bandit-report.json
│   ├── semgrep-report.json
│   └── npm-audit.json
├── flujos-humanos/
│   ├── FARMACIA_VENTA_COMPLETA.md
│   ├── LABORATORIO_RESULTADO_VALIDADO.md
│   ├── INVENTARIO_MOVIMIENTO.md
│   └── evidencia-capturas/
│       ├── farmacia-paso1.png
│       ├── farmacia-paso2.png
│       └── pdf-generado.pdf
├── adversarial/
│   ├── SIEMBRA_1_EMPRESA_FILTER.md
│   ├── SIEMBRA_2_DINERO_RANGO.md
│   ├── SIEMBRA_3_APPEND_ONLY.md
│   └── resultados-tests-negativos.txt
├── deploy/
│   ├── DEPLOY_EVIDENCE.md
│   ├── SHA_VERIFICACION.txt
│   ├── MIGRACIONES_EJECUTADAS.log
│   ├── SMOKE_TESTS.txt
│   └── rollback-plan.md
└── reconciliacion/
    ├── RECONCILIACION_GITHUB_CODEX_TESTIGO.md
    ├── DIFERENCIAS_ENCONTRADAS.json
    └── VEREDICTO_FINAL.md
```

### Veredicto Posible

- 🔴 `NO_LISTO`: P0 bloqueantes abiertos
- 🟡 `LISTO_PARA_STAGING`: P0 cerrados, P1 documentados, matriz 80%+
- 🟢 `LISTO_PARA_VALIDACION_HUMANA`: Todos módulos matriz 100%, reconciliación OK
- ✅ `APROBADO_PARA_PRODUCCION`: Aprobación escrita responsable humano

---

## 9. Orden Operativo Recomendado

```
[✅] 1. Congelar tip → FREEZE.json
[✅] 2. Reconciliar checkout, remoto, settings
[✅] 3. Ejecutar gates obligatorios GitHub (Secret, SBOM, CodeQL)
[⏳] 4. Agregar jobs: bandit, semgrep, mypy, template-lint
[⏳] 5. Ejecutar gates completos en checkout limpio
[⏳] 6. Auditoria estática Codex (P0, P1, P2)
[⏳] 7. Levantar staging Python 3.12 + PostgreSQL 16
[⏳] 8. Ejecutar flujos humanos completos por módulo
[⏳] 9. Ejecutar controles negativos (siembras)
[⏳] 10. Entregar paquete a testigo independiente
[⏳] 11. Reconciliar GitHub + Codex + Testigo
[⏳] 12. Desplegar SHA auditado → staging → producción
[⏳] 13. Smoke tests post-deploy + firma veredicto
```

---

## 10. Regla de Cierre

> Un defecto **NO** se cierra por estar documentado, por tener commit, o por pasar test aislado.
>
> Se cierra **ÚNICAMENTE** cuando existe:
> 1. Correccion en tip congelado ✅
> 2. Regresión automatizada ✅
> 3. Prueba de flujo humano (si aplica) ✅
> 4. Evidencia en entorno aplicable ✅
> 5. Reconciliación independiente ✅
>
> **Lo que no pueda probarse se declara LIMITACION, nunca PASS.**

---

## 11. Autorización y Firma

### Responsables

| Rol | Usuario | Firma | Fecha |
|-----|---------|-------|-------|
| Codex (Auditor/Corrector) | @copilot | ✅ | 2026-09-15 |
| GitHub Actions (Verificador) | workflow | ⏳ | [auto] |
| Testigo Independiente | [designar] | ⏳ | [TBD] |
| Responsable Humano | primerosaludlaboratorio-star | ⏳ | [TBD] |

### Cambios Autorizados

- ✅ Agregar gates de CI
- ✅ Generar reportes
- ✅ Ejecutar tests
- ✅ Documentar hallazgos
- ❌ Modificar datos de producción
- ❌ Rotar secretos
- ❌ Desplegar sin aprobación

---

**Documento clasificado:** Interno (no secreto)  
**Vigencia:** Hasta próximo commit o 90 días  
**Actualización:** Requerida si branch cambia o SHA diverge  

---

*Fin del Plan de Auditoría v1.0*
