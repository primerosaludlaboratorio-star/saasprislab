# 📋 PRISLAB Auditoría Integral - Fase 3: Staging Técnico

**Versión:** 1.0  
**Fecha:** 2026-09-15  
**Estado:** Fase 3 - ENTORNO EJECUTABLE PREPARADO
**Commit Anterior:** `88c22cb` (Fase 2 Cerrada)

---

## 🎯 Objetivo Fase 3

Validar que PRISLAB SaaS **funciona correctamente en un entorno equivalente a producción** con:

- ✅ Python 3.12.x (exacto como producción)
- ✅ PostgreSQL 16 Alpine (exacto como producción)
- ✅ Redis/Celery (tareas asincrónicas)
- ✅ Nginx (reverse proxy)
- ✅ Migraciones desde cero + reutilización de BD
- ✅ Tests de integración multi-tenant
- ✅ Validación de controles de seguridad

---

## 📊 Estado Actual

### ✅ Completado en Fase 2
- Fuente congelada: `88c22cb`
- Inventario: 33 apps, 266 modelos, 1956 rutas, 120 dependencias
- Artefactos externos verificados con SHA-256
- Reporte: `REPORTE_CIERRE_FASE_2.md`

### ✅ Preparado para ejecución reproducible
- [x] Workflow aislado `.github/workflows/fase3-staging.yml`
- [x] Python 3.12 via `actions/setup-python`
- [x] PostgreSQL 16 Alpine como servicio efímero
- [x] Redis 7 Alpine como servicio efímero
- [x] Evidencia automática por `github.run_id`

### ⏳ Pendiente de ejecución en Fase 3
- [ ] Entorno staging Python 3.12 + PostgreSQL 16
- [ ] Migraciones: desde cero
- [ ] Migraciones: reutilización (idempotencia)
- [ ] Tests de integración multi-tenant
- [ ] Validación append-only (LIMS)
- [ ] Validación ACID (transacciones)
- [ ] Performance: latencia DDL, round-trip, tests
- [ ] Bloqueos PostgreSQL (concurrencia)
- [ ] Disponibilidad workers Celery/Redis

---

## 🔧 Requisitos Fase 3

### Máquina/Entorno

```
✅ REQUERIDO:
- Python 3.12.x (verificable con: python --version)
- PostgreSQL 16 Alpine (verificable con: psql --version)
- Redis (verificable con: redis-cli --version)
- Docker (para reproducibilidad)
- Docker Compose (para orquestar servicios)

⏳ VERIFICACIÓN:
python --version        # Debe ser 3.12.x
psql --version          # Debe ser 16.x
redis-cli --version     # Debe estar disponible
docker --version        # Debe estar disponible
docker-compose --version # Debe estar disponible
```

### Código

```
✅ Ya disponible:
- scripts/audit/generate_freeze.py
- scripts/audit/generate_inventory.py
- requirements.lock (con hashes verificados)
- manage.py (Django)
- Todas las migraciones en lugar

✅ IMPLEMENTADO:
- `.github/workflows/fase3-staging.yml` (staging efímero reproducible)

⏳ NO SE USA EN ESTA FASE:
- Docker Compose en el VPS: el VPS es producción y no debe reutilizarse como staging.
- Scripts pseudogenericos que no correspondan a modelos y rutas reales.
```

---

## 📋 Subtareas Fase 3

### Subtarea 3.1: Levantar Entorno Staging

**Objetivo:** Ambiente aislado equivalente a producción

**Pasos:**

```yaml
1. Verificar disponibilidad de herramientas
   - python --version → 3.12.x ✅
   - psql --version → 16.x ✅
   - docker --version ✅
   - docker-compose --version ✅

2. Crear docker-compose.yml para staging
   - PostgreSQL 16 Alpine
   - Redis latest
   - App Django (build local)
   - Nginx reverse proxy
   
3. Construir imagen Docker
   - FROM python:3.12-slim
   - COPY requirements.lock
   - pip install -r requirements.lock --require-hashes
   - COPY . /app
   
4. Ejecutar docker-compose up
   - Verificar que todos los servicios inician
   - Verificar logs sin errores críticos
   
5. Registrar estado inicial
   - docker ps (containers activos)
   - psql -l (bases de datos)
   - redis-cli PING
   - curl http://localhost/health (health check)
```

**Deliverable:**
```
audit/fase3/
├── docker-compose.yml
├── docker/Dockerfile.staging
└── logs/
    ├── postgres-startup.log
    ├── redis-startup.log
    ├── app-startup.log
    └── health-check.log
```

---

### Subtarea 3.2: Migraciones desde Cero

**Objetivo:** Validar que la BD puede inicializarse limpia sin corrupción

**Pasos:**

```bash
# En contenedor PostgreSQL limpio
python manage.py migrate --noinput

# Verificar que todas las migraciones se aplican
python manage.py showmigrations

# Contar tablas creadas
psql -c "SELECT count(*) FROM information_schema.tables 
         WHERE table_schema='public'"

# Verificar que las 239 migraciones se aplicaron correctamente
```

**Validaciones:**
- [ ] Todas las 239 migraciones sin errores
- [ ] 266 modelos generaron sus tablas
- [ ] Índices creados correctamente
- [ ] Foreign keys definidas
- [ ] Constraints activos

**Deliverable:**
```
audit/fase3/migrations/
├── migration-log.txt (todas las migraciones listadas)
├── schema-dump.sql (estado final de BD)
├── table-count.txt (número de tablas = esperado)
└── errors.txt (si hubiera, documentados)
```

---

### Subtarea 3.3: Migraciones - Idempotencia

**Objetivo:** Validar que volver a ejecutar migraciones no corrompe nada

**Pasos:**

```bash
# 1. Ejecutar migraciones primera vez
python manage.py migrate --noinput

# 2. Generar hash de todas las tablas/datos
SELECT md5(pg_sleep(0)) FROM information_schema.tables... > hash1.txt

# 3. Ejecutar migraciones de nuevo (should be no-op)
python manage.py migrate --noinput

# 4. Generar hash nuevamente
SELECT md5(...) > hash2.txt

# 5. Comparar hashes
diff hash1.txt hash2.txt  # Debe ser idéntico
```

**Validación:**
- [ ] Segunda ejecución no modifica nada
- [ ] No hay "0002_auto" generados automáticamente
- [ ] Estado final es idéntico

**Deliverable:**
```
audit/fase3/idempotence/
├── hash-before.txt
├── hash-after.txt
├── diff-result.txt (debe estar vacío)
└── verification.md (afirmación de idempotencia)
```

---

### Subtarea 3.4: Tests de Integración Multi-Tenant

**Objetivo:** Validar aislamiento entre empresas/sucursales

**Script:** `scripts/test/integration_tests.py`

```python
"""
PRISLAB Integration Tests - Multi-Tenant Isolation

Verifica que:
1. Usuario de empresa A no ve datos de empresa B
2. Filtros de empresa están activos en todos los QuerySets
3. No hay fugas de datos entre tenants
"""

def test_tenant_isolation_products():
    """Producto de empresa A no visible en empresa B"""
    empresa_a = create_test_company(name="CLINIC_A")
    empresa_b = create_test_company(name="CLINIC_B")
    
    product_a = Product.objects.create(
        name="Amoxicilina",
        empresa=empresa_a
    )
    
    # Switch a empresa B
    request.tenant_empresa = empresa_b
    
    # Debe estar vacío
    assert Product.objects.count() == 0, "FALLO: Producto de A visible en B"
    assert product_a not in Product.objects.all()

def test_tenant_isolation_ventas():
    """Venta de empresa A no visible en empresa B"""
    # ... similar

def test_tenant_isolation_resultados():
    """Resultado de laboratorio aislado por empresa"""
    # ... similar

def test_cross_tenant_attempt_direct_query():
    """Intento de acceso directo a objeto de otra empresa falla"""
    empresa_a = create_test_company(name="CLINIC_A")
    empresa_b = create_test_company(name="CLINIC_B")
    
    venta = Venta.objects.create(empresa=empresa_a, total=100.00)
    
    # Cambiar tenant
    request.tenant_empresa = empresa_b
    
    # Intento de acceso directo
    with pytest.raises(PermissionDenied):
        venta.refresh_from_db()  # O similar validación

def test_rbac_user_role_separation():
    """Usuario con rol 'tecnico' no accede a 'admin'"""
    user_tech = create_test_user(role="TECNICO")
    user_admin = create_test_user(role="ADMIN")
    
    # Tech no ve admin panel
    response = client.get("/admin/", as_user=user_tech)
    assert response.status_code == 403, "FALLO: TECNICO accedió a ADMIN"
    
    # Admin sí ve
    response = client.get("/admin/", as_user=user_admin)
    assert response.status_code == 200
```

**Ejecución:**

```bash
pytest scripts/test/integration_tests.py -v --tb=short
```

**Deliverable:**
```
audit/fase3/integration/
├── test-results.xml (JUnit format)
├── test-log.txt (PASS/FAIL/SKIP)
├── coverage-report.html
└── failed-tests.md (si las hay)
```

---

### Subtarea 3.5: Validación Append-Only (LIMS)

**Objetivo:** Resultados de laboratorio NO pueden modificarse después de validación

**Script:** `scripts/test/lims_immutability_tests.py`

```python
def test_resultado_inmutable_after_validation():
    """Resultado validado no puede editarse"""
    resultado = Resultado.objects.create(
        valor="14.5",
        unidad="g/dL",
        validado=False
    )
    
    # Validar
    resultado.validado = True
    resultado.save()
    
    # Intentar modificar
    resultado.valor = "15.0"  # Cambio intencional
    
    with pytest.raises(ValidationError) as exc:
        resultado.save()
    
    assert "immutable" in str(exc.value).lower()

def test_resultado_audit_log():
    """Cada cambio debe estar registrado en log append-only"""
    resultado = Resultado.objects.create(valor="14.5", validado=False)
    
    # Log inicial
    assert AuditLog.objects.filter(resultado=resultado).count() == 1
    
    # Cambio 1
    resultado.valor = "14.6"
    resultado.save()
    assert AuditLog.objects.filter(resultado=resultado).count() == 2
    
    # Log nunca se modifica
    first_log = AuditLog.objects.filter(resultado=resultado).first()
    original_timestamp = first_log.created_at
    
    # Intentar modificar log (debería fallar)
    with pytest.raises(ValidationError):
        first_log.created_at = now()
        first_log.save()
```

**Deliverable:**
```
audit/fase3/lims/
├── immutability-test-results.xml
├── audit-log-sample.json
└── validation-report.md
```

---

### Subtarea 3.6: Validación ACID (Transacciones)

**Objetivo:** Transacciones no quedan en estado parcial

**Script:** `scripts/test/acid_tests.py`

```python
def test_venta_atomic_transaction():
    """Venta: crear + reducir stock + registrar en caja = atómico"""
    
    producto = Product.objects.create(name="Producto", stock=10)
    caja = Caja.objects.create(empresa=empresa, saldo=0)
    
    try:
        with transaction.atomic():
            venta = Venta.objects.create(
                producto=producto,
                cantidad=5,
                total=50.00,
                empresa=empresa
            )
            
            # Reducir stock
            producto.stock -= 5
            producto.save()
            
            # Registrar en caja
            caja.saldo += 50.00
            caja.save()
            
            # Simular error a mitad de transacción
            if test_mode:
                raise IntegrationError("Simulated failure")
    
    except IntegrationError:
        pass  # Rollback automático
    
    # Verificar rollback completo
    assert Venta.objects.filter(id=venta.id).count() == 0, "FALLO: Venta quedó sin rollback"
    assert producto.stock == 10, "FALLO: Stock modificado sin confirmar"
    assert caja.saldo == 0, "FALLO: Caja modificada sin confirmar"
```

**Deliverable:**
```
audit/fase3/acid/
├── transaction-test-results.xml
├── rollback-verification.md
└── consistency-checks.log
```

---

### Subtarea 3.7: Performance Baseline

**Objetivo:** Establecer línea base de latencias

**Script:** `scripts/test/performance_tests.py`

```python
def measure_ddl_roundtrip():
    """Tiempo: consulta simple → BD → respuesta"""
    times = []
    for i in range(100):
        start = time.time()
        Product.objects.filter(empresa=empresa).count()
        elapsed = time.time() - start
        times.append(elapsed)
    
    return {
        "min_ms": min(times) * 1000,
        "max_ms": max(times) * 1000,
        "avg_ms": (sum(times) / len(times)) * 1000,
        "p95_ms": np.percentile(times, 95) * 1000,
    }

def measure_migration_time():
    """Tiempo total para ejecutar todas las migraciones"""
    start = time.time()
    subprocess.run(["python", "manage.py", "migrate", "--noinput"])
    elapsed = time.time() - start
    return elapsed

def measure_test_suite_time():
    """Tiempo para ejecutar suite completa de tests"""
    start = time.time()
    subprocess.run(["pytest", ".", "-q"])
    elapsed = time.time() - start
    return elapsed
```

**Deliverable:**
```
audit/fase3/performance/
├── baseline.json
│   {
│       "ddl_roundtrip_ms": {"min": 0.5, "avg": 1.2, "p95": 2.1},
│       "migration_time_s": 23.4,
│       "test_suite_time_s": 156.7
│   }
└── performance-report.md
```

---

### Subtarea 3.8: Concurrencia - Bloqueos PostgreSQL

**Objetivo:** Verificar que no hay deadlocks ni bloqueos anormales

**Script:** `scripts/test/concurrency_tests.py`

```python
def test_concurrent_venta_creation():
    """Múltiples usuarios creando ventas simultáneamente"""
    import threading
    
    results = []
    errors = []
    
    def create_venta():
        try:
            venta = Venta.objects.create(
                empresa=empresa,
                total=100.00
            )
            results.append(venta.id)
        except Exception as e:
            errors.append(str(e))
    
    threads = [threading.Thread(target=create_venta) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Verificar que todas se crearon sin error
    assert len(errors) == 0, f"FALLO: Concurrencia errores: {errors}"
    assert len(results) == 50, "FALLO: No todas las ventas se crearon"

def test_concurrent_stock_reduction():
    """Múltiples usuarios reduciendo stock del mismo producto"""
    producto = Product.objects.create(
        name="Producto",
        stock=1000,
        empresa=empresa
    )
    
    # 100 threads, cada uno reduce 10 unidades
    # Resultado final debe ser stock = 0 (exacto, no negativo)
    # ...
```

**Deliverable:**
```
audit/fase3/concurrency/
├── concurrency-test-results.xml
├── deadlock-analysis.log
└── pg_stat_activity.txt (estado de BD durante tests)
```

---

### Subtarea 3.9: Disponibilidad de Workers Celery

**Objetivo:** Verificar que tareas asincrónicas se ejecutan correctamente

**Pasos:**

```bash
# 1. Verificar que Celery está activo
celery -A config inspect active

# 2. Enviar tarea de prueba
python manage.py shell
>>> from tasks import test_task
>>> test_task.delay()
# Verificar que se ejecuta

# 3. Registrar estado
ps aux | grep celery > audit/fase3/celery/workers.log
celery -A config inspect active > audit/fase3/celery/active-tasks.json
```

**Deliverable:**
```
audit/fase3/celery/
├── workers.log
├── active-tasks.json
└── worker-availability.md
```

---

## 📊 Matriz de Validación Fase 3

| Subtarea | Objetivo | Artefacto | Estado |
|----------|----------|-----------|--------|
| 3.1 | Staging docker-compose | docker-compose.yml + logs | ⏳ |
| 3.2 | Migraciones desde cero | migration-log.txt + schema.sql | ⏳ |
| 3.3 | Idempotencia migraciones | hash comparison | ⏳ |
| 3.4 | Multi-tenant isolation | test-results.xml | ⏳ |
| 3.5 | LIMS append-only | immutability-results.xml | ⏳ |
| 3.6 | ACID transactions | transaction-results.xml | ⏳ |
| 3.7 | Performance baseline | baseline.json | ⏳ |
| 3.8 | Concurrency/deadlocks | concurrency-results.xml | ⏳ |
| 3.9 | Celery workers | active-tasks.json | ⏳ |

---

## 🚀 Próximos Pasos

**ANTES de ejecutar Fase 3:**

1. [x] El workflow define Python 3.12, PostgreSQL 16 Alpine y Redis 7
2. [x] El VPS productivo queda fuera del staging
3. [x] Se usan pruebas Django reales existentes, no pseudopruebas
4. [ ] Ejecutar manualmente el workflow y conservar el artifact `prislab-fase3-<run_id>`
5. [ ] Copiar el artifact fuera del checkout y documentar su SHA-256

**Veredicto al cierre de Fase 3:**

- 🟢 `FASE_3_CERRADA - STAGING VALIDADO` (si todos los tests pasan)
- 🟡 `FASE_3_PARCIAL - [Qué falta]` (si hay limitaciones documentadas)
- 🔴 `FASE_3_FALLÓ - [Errores críticos]` (si hay bloqueadores)

---

**Documento:** Especificación Fase 3  
**Versión:** 1.0  
**Fecha:** 2026-09-15  
**Responsable:** Codex (Auditor)  
