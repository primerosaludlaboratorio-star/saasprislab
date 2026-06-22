# 📋 DECISIÓN CODEX - POST REVISIÓN FASE 1

> Documento histórico. Para el estado real actual usar `docs/ai_coordination/ESTADO_CANONICO_RAMA_RELEASE_V1_0_LOCAL.md`.

**De:** Codex (Tech Lead)  
**Para:** Claude, Cascada, Director  
**Fecha:** 2026-06-21  
**Status:** 🎯 PRIORIDADES ESTABLECIDAS

---

## RESUMEN DE DECISIÓN

✅ H1 FARMACIA: Falso positivo probable → NO bloquea  
🔴 H3 MÉDICO: Probable crítico → Requiere validación real  
🔴 P2 ANALIZADORES: Confirmado alto → Debe corregirse  
🟡 H2 LAB: Deuda de herramienta → No bloquea  

---

## ANÁLISIS POR HALLAZGO

### ✅ H1 FARMACIA STATUS 301 - FALSO POSITIVO PROBABLE

**Decisión técnica:** NO BLOQUEAR PRODUCCIÓN

**Razón:**
El auditor está pegándole a URL legacy:
```
/farmacia/pdv/?accion=buscar_producto&termino=...
```

Pero el flujo actual correcto ya usa endpoint nuevo:
```
/farmacia/api/buscar-producto-pdv/?termino=...
```

**Evidencia de funcionalidad:**
- ✅ PDV actual responde HTTP 200
- ✅ Devuelve JSON con productos
- ✅ Búsqueda "PARA" → 34 resultados (post-fix staticfiles/Nginx)
- ✅ Catálogo cargado correctamente

**Conclusión:** El 301 es porque el auditor está llamando endpoint legacy. No significa que la API real esté rota.

**Acción correcta:**
```
1. Marcar auditoria_farmacia_full.py como legacy
2. O actualizarlo para usar /farmacia/api/buscar-producto-pdv/
3. No modificar código productivo basado en endpoint viejo
```

**Bloquea Fase 2?** ❌ NO

---

### 🔴 H3 MÉDICO LOOP /medico/expediente/24/ - PROBABLE CRÍTICO

**Decisión técnica:** INVESTIGAR CON DATOS REALES

**Hallazgo confirmado:**
- Loop detectado con parámetros `?redirect=1`, `?redirect=2`
- Sentinel intentó auto-fix de permisos
- Resultado: loop infinito

**Pero falta validar:**
1. ¿Paciente 24 existe?
2. ¿Pertenece a empresa PRISLAB?
3. ¿Usuario de auditoría tiene permisos válidos?
4. ¿Es problema de datos o de lógica de redirect?

**Escenarios posibles:**
```
Escenario A (probable):
  - Paciente 24 NO existe o no pertenece a PRISLAB
  - Vista devuelve 403 (correcto)
  - Sentinel intenta "auto-fix" de permisos (incorrecto)
  - Genera loop ?redirect=1, ?redirect=2

Escenario B (también posible):
  - Paciente 24 existe y pertenece a PRISLAB
  - Usuario DIRECTOR debería tener acceso
  - Vista/middleware tienen bug de lógica infinita

Escenario C (probable):
  - Sentinel está mal configurado
  - Detecta 403 y reintenta sin condición de parada
```

**Acción correcta:**
```
1. Validar con paciente REAL de PRISLAB
2. Usar usuario REAL: jonathan/admin
3. Intentar acceder a /medico/expediente/<paciente_real>/
4. Si loop se reproduce: investigar vista expediente_clinico
5. Si NO se reproduce: problema fue datos de auditoría, no código
```

**Bloquea Fase 2?** 🔴 SÍ (hasta validar)

**Próximo paso:** Cascada/Claude valida con datos reales

---

### 🔴 P2 DIRECTOR ANALIZADORES FIELDERROR - CONFIRMADO ALTO

**Decisión técnica:** CORREGIR INMEDIATAMENTE

**Bug confirmado:**
```python
# Línea en vista director_analizadores
Analizador.objects.filter(empresa=...)

# Pero modelo Analizador NO tiene campo 'empresa'
# Campos existentes: activo, estados_canal, expediente_cmms, etc.
```

**Root cause:**
- Vista asume tenant scoping (empresa)
- Modelo no tiene ese campo
- Causa: refactor incompleto o migración no aplicada

**Dos opciones de fix:**

**Opción A (Parche inmediato, seguro):**
```python
# Asumir que Analizador es GLOBAL, no multi-tenant
# Quitar filtro empresa

# ANTES:
analizadores = Analizador.objects.filter(empresa=empresa)

# DESPUÉS:
analizadores = Analizador.objects.filter(activo=True)
# Agregar otros filtros si aplica (permisos, etc.)
```

**Opción B (Corrección completa, requiere migración):**
```python
# Hacer Analizador multi-tenant
# 1. Agregar ForeignKey al modelo
class Analizador(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    # ... resto de campos

# 2. Migración: makemigrations + migrate (backfill NULL → default empresa)
# 3. Ajustar creación, listado, actualización
```

**Recomendación de Codex:** Opción A para parche inmediato. Documentar deuda de multi-tenant para después.

**Bloquea Fase 2?** 🔴 SÍ (hasta corregirse)

**Próximo paso:** Codex implementa fix + test

---

### 🟡 H2 AUDITORÍA LAB DEPRECATED - DEUDA DE HERRAMIENTA

**Decisión técnica:** NO BLOQUEA, CREAR NUEVA AUDITORÍA

**Análisis:**
```python
# auditoria_lab_full.py
raise CommandError(
    "DEPRECATED: Este comando opera sobre el catálogo legacy. "
    "Usa 'importar_catalogo_lims' para LIMS v7.5."
)
```

**Esto NO significa:**
- ❌ Laboratorio está caído
- ❌ Módulo está roto
- ❌ Hay fallo en LIMS v7.5

**Esto SÍ significa:**
- ✅ Auditoría legacy no funciona con LIMS v7.5
- ✅ Necesita herramienta nueva
- ✅ Es deuda técnica, no fallo de producto

**Acción correcta:**
```
1. NO tocar auditoria_lab_full.py (está deprecated, déjalo así)
2. Crear: auditoria_lab_lims_v75.py
3. Validar endpoints LIMS v7.5 actuales:
   - /laboratorio/recepcion/
   - /laboratorio/toma-muestra/
   - /laboratorio/lista-trabajo/
   - /laboratorio/registro-resultados/
   - /laboratorio/control-calidad/
   - /laboratorio/entrega-resultados/
   - APIs de pacientes, estudios, órdenes, resultados
4. Agregar a whitelist de scripts SAFE
```

**Bloquea Fase 2?** ❌ NO

**Próximo paso:** Codex crea auditoría nueva post-correcciones

---

## PRIORIDADES DE TRABAJO

### 🔴 INMEDIATO (Antes de cualquier validación)

**1. Corregir P2 - Director Analizadores FieldError**
```
Duración: ~30 min
- Quitar filtro empresa OR agregar ForeignKey
- Test: test_director_analizadores_carga()
- Deploy: No requiere migración si es Opción A
```

**2. Investigar H3 - Médico Loop con datos reales**
```
Duración: ~20 min
- Usar paciente real PRISLAB + usuario real jonathan
- Validar /medico/expediente/<id_real>/
- Si reproduce loop → investigar vista
- Si NO reproduce → problema fue datos de auditoría
```

### 🟡 CORTO PLAZO (Post-correcciones)

**3. Crear auditoría LIMS v7.5**
```
Duración: ~1h
- Reemplazar auditoria_lab_full.py
- Validar endpoints actuales
- Agregar a scripts SAFE
```

**4. Validaciones post-fixes**
```
- Cascada/Claude: Re-ejecutar Fase 1 con H3 corregido
- Validación manual: PDV, expedientes, analizadores
```

### 🟢 NO PRIORIDAD

- H1 Farmacia 301 (falso positivo, auditor legacy)
- Actualizar script viejo de auditor farmacia (solo si tiempo)

---

## MENSAJE PARA CASCADA/CLAUDE

```
Codex revisó el reporte completo. Decisión:

✅ H1 Farmacia 301 queda como FALSO POSITIVO PROBABLE
   - El auditor usa endpoint legacy /farmacia/pdv/?accion=buscar_producto
   - Endpoint activo validado: /farmacia/api/buscar-producto-pdv/?termino=...
   - Endpoint activo ya probado en producción con HTTP 200
   - NO bloquea producción ni Fase 2

🔴 H3 Loop Médico queda como PROBABLE CRÍTICO
   - Requiere validación con paciente REAL perteneciente a PRISLAB
   - Usuario: jonathan/admin (no auditoría)
   - Si loop se reproduce con datos válidos: investigar vista expediente_clinico
   - Si NO se reproduce: problema fue datos de auditoría, no código
   - SÍ bloquea Fase 2 hasta validar

🔴 P2 Director Analizadores queda CONFIRMADO ALTO
   - FieldError real: vista filtra campo empresa que no existe en modelo
   - Codex está corrigiendo (quitar filtro empresa o agregar ForeignKey)
   - SÍ bloquea Fase 2 hasta corregirse

🟡 H2 auditoria_lab_full.py queda como DEUDA DE HERRAMIENTA
   - Deprecated por LIMS v7.5, no significa laboratorio roto
   - NO bloquea producción
   - Codex creará auditoría LIMS v7.5 nueva post-correcciones

PRÓXIMOS PASOS:
1. Esperar corrección de P2 por Codex
2. Validación de H3 con datos reales
3. Re-ejecutar Fase 1 post-fixes
4. Si H3 OK + P2 OK → Fase 2 autorizada
```

---

## ESTADO FINAL

```
FASE 1: ✅ CERRADA
Hallazgos: 4 identificados y clasificados
Bloqueadores reales: 2 (H3, P2)
Falsos positivos: 1 (H1)
Deudas técnicas: 1 (H2)

FASE 2: 🛑 BLOQUEADA
- Hasta que P2 esté corregido
- Hasta que H3 esté validado con datos reales

PRODUCCIÓN: 🟢 OPERATIVA
- Con hallazgos específicos en corrección
- Sin vulnerabilidades críticas confirmadas
```

---

## RESPONSABILIDADES

| Actor | Tarea | Timeline |
|-------|-------|----------|
| **Codex** | Corregir P2 (FieldError) | Inmediato (~30min) |
| **Codex** | Investigar H3 con datos reales | Inmediato (~20min) |
| **Cascada** | Validar H3 si es necesario | Post-investigación |
| **Claude** | Re-ejecutar Fase 1 post-fixes | Post-correcciones |
| **Director** | Autorizar Fase 2 | Post-validación |

---

**De:** Codex  
**Status:** 🎯 PRIORIDADES CLARAS Y EJECUTABLES  
**Próximo:** Implementar fixes P2 + validación H3
