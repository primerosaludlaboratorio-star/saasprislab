# 🎯 GUÍA OPERATIVA FINAL - PROTOCOLO DE AUDITORÍA PRISLAB

> Estado canónico actual: `docs/ai_coordination/ESTADO_CANONICO_RAMA_RELEASE_V1_0_LOCAL.md`

**Aprobado por:** Director  
**Vigencia:** 2026-06-21 en adelante  
**Aplicable a:** Claude, Cascada, Codex  
**Versión:** 2.0 (Ejecutiva y Operativa)

---

## 📋 PRINCIPIOS RECTORES

### 1️⃣ Evidencia sin Burocracia

**Hallazgo simple** (ej: typo, línea rota):
- ✅ Archivo + línea
- ✅ Ruta/función
- ✅ Evidencia (código/traceback)
- ✅ Esperado vs Real
- ✅ Clasificación
- ✅ Recomendación

**Hallazgo complejo** (ej: arquitectura, multi-módulo):
- ✅ Todos los 10 puntos del protocolo riguroso

**Regla:** Mínimo suficiente para que Codex decida y actúe.

---

### 2️⃣ Cascada = Recolector de Evidencia Fría

**QUE HAGA:**
- ✅ Leer código fuente
- ✅ Buscar archivos y líneas exactas
- ✅ Ejecutar scripts SAFE (auditorías, no destructivos)
- ✅ Reportar tracebacks reales
- ✅ Documentar rutas en urls.py
- ✅ Capturar contradicciones (código dice X, pero auditor ve Y)

**QUE NO HAGA:**
- ❌ Opinar ("esto probablemente sea bug")
- ❌ Asumir ("creo que")
- ❌ Confirmar por coincidencia ("coincido con Codex")
- ❌ Ejecutar scripts en producción
- ❌ Crear datos

**Formato de reporte:**
```
EVIDENCIA FRÍA:
- Archivo: [ruta exacta]
- Línea: [número]
- Código: [código literal]
- Resultado: [qué pasó]
- Traceback: [si aplica]

CONTRADICCIÓN ENCONTRADA:
[Si encontraste que algo reportado no coincide con evidencia]

CLASIFICACIÓN: [CONFIRMADO/PROBABLE/PENDIENTE/FALSO_POSITIVO/LEGACY/DEUDA]
RECOMENDACIÓN: [Concreta: qué revise Codex]
```

---

### 3️⃣ Claude = Segundo Filtro, No Confirmador

**VALIDAR:**
- ✅ ¿La evidencia prueba realmente el hallazgo?
- ✅ ¿El hallazgo viene de script legacy/deprecado?
- ✅ ¿Usa datos ficticios o inexistentes?
- ✅ ¿La ruta está activa en urls.py?
- ✅ ¿Hay reproducción real o solo código?

**RECLASIFICAR SIN DUDAR:**
- ❌ "CONFIRMADO" que viene de auditor sin permisos → **FALSO_POSITIVO**
- ❌ "CONFIRMADO" basado en script deprecated → **LEGACY_NO_ACTIVO**
- ❌ "CONFIRMADO" con paciente inexistente → **PENDIENTE_VALIDAR**
- ❌ "CONFIRMADO" sin reproducción real → **PROBABLE**

**DEVOLVER A CASCADA SI:**
- Falta evidencia mínima
- Viene de script o ruta no identificada
- No se puede verificar en código

**ENTREGAR A CODEX SOLO SI:**
- Tienes evidencia técnica sólida
- Está bien clasificado
- Tiene recomendación concreta

---

### 4️⃣ Codex = Decisor + Implementador

**CODEX RECIBE SOLO:**
- Hallazgos validados por Claude
- Con evidencia suficiente
- Clasificados correctamente
- Con recomendación concreta

**CODEX DECIDE:**
1. ¿Se corrige o se documenta?
2. ¿Qué arquitectura/patrón aplica?
3. ¿Test unitario cómo se ve?
4. ¿Migración si aplica?
5. ¿Retro-compatibilidad?

**CODEX ENTREGA:**
- Código fix
- Test que valida fix
- Commit message claro
- Deploy seguro

---

## 🔴 REGLAS DE BLOQUEO

**NADA BLOQUEA FASE 2 SI:**

❌ Viene de auditoría deprecated:
```
Ejemplo: auditoria_lab_full.py está deprecated a propósito.
No bloquea aunque esté roto.
Clasificación: DEUDA_HERRAMIENTA
```

❌ Usa endpoint legacy:
```
Ejemplo: auditor llama /farmacia/pdv/?accion=buscar_producto
Endpoint real: /farmacia/api/buscar-producto-pdv/
Clasificación: FALSO_POSITIVO
```

❌ Usa paciente inexistente:
```
Ejemplo: "expediente de paciente 24 da loop"
Si paciente 24 no existe o no pertenece a empresa.
Clasificación: PENDIENTE_VALIDAR
Necesita: validar con paciente real PRISLAB
```

❌ Ruta no activa en urls.py:
```
Ejemplo: "encontré endpoint rotor en consultorio"
Si consultorio/urls.py no tiene esa ruta.
Clasificación: LEGACY_NO_ACTIVO
```

❌ Sin reproducción o evidencia suficiente:
```
Ejemplo: "el dashboard parece lento"
Sin traceback, sin test, sin reproducción.
Clasificación: PENDIENTE_VALIDAR
```

---

## ✅ HALLAZGOS ACTUALES - ESTADO FINAL

### 🔴 P2: DIRECTOR ANALIZADORES

**Clasificación:** ✅ **CONFIRMADO ALTO**

**Evidencia:**
- Archivo: `laboratorio/models.py` líneas 30-94
- Clase: `Equipo` SIN campo `empresa`
- Archivo: `core/views/director.py` línea 316
- Código: `Equipo.objects.filter(empresa=empresa)` ← FieldError

**Fix correcto (NO automático):**
```python
# OPCIÓN RECOMENDADA: Quitar solamente filtro empresa
# NO hacer migración todavía sin decisión arquitectónica

# ANTES (línea 316):
equipo_qs = Equipo.objects.filter(empresa=empresa)

# DESPUÉS:
equipo_qs = Equipo.objects.filter(activo=True)
# Mantener filtros válidos si los hay
```

**NO hacer:**
- ❌ `Equipo.objects.all()` (sin filtro seguridad)
- ❌ Migración `empresa` sin decisión de negocio
- ❌ Cambios automáticos

**Test requerido:**
```python
def test_director_analizadores_sin_fielderror(self):
    """Director puede acceder a /director/analizadores/ sin FieldError"""
    response = self.client.get('/director/analizadores/')
    self.assertEqual(response.status_code, 200)  # No 500
```

**Timeline:** ~1h (fix + test + deploy)

**Bloquea Fase 2:** 🔴 **SÍ**

---

### ⚠️ H3: MÉDICO LOOP

**Clasificación:** ⚠️ **PROBABLE (no loop infinito)**

**Evidencia:**
- NO es loop infinito (cache evita en línea 182)
- Sentinel auto-fix falla porque no puede dar rol MEDICO a DIRECTOR
- Resultado: 403 permanente, no loop

**Problema real:**
- ¿DIRECTOR debería ver expedientes?
- SI → cambiar línea 71 expediente_clinico
- NO → Sentinel no debería intentar auto-fix fallido

**Validación requerida ANTES de fix:**
```
USUARIO: jonathan o admin (usuario real PRISLAB)
PACIENTE: Uno real, existente, perteneciente a PRISLAB
RUTA: /medico/expediente/<id_real>/
RESULTADO ESPERADO: 
  - Si DIRECTOR debería ver: Status 200
  - Si DIRECTOR no debería: Status 403 (pero SIN redirect loop)
```

**Comandos de validación (Cascada):**
```bash
# 1. Confirmar que paciente existe
python manage.py shell
>>> from core.models import Paciente
>>> p = Paciente.objects.filter(empresa__nombre='PRISLAB').first()
>>> print(f"Paciente: {p.id} {p.nombre}")

# 2. Acceder como jonathan/admin a expediente
# (Requiere usuario real - NO ficcional)
```

**Fix concreto (si se reproduce):**
```python
# Opción A: Si DIRECTOR SÍ debe ver
puede_ver_historial = request.user.rol in ['MEDICO', 'DIRECTOR', 'ADMIN'] or request.user.is_superuser

# Opción B: Si DIRECTOR no debe ver
# Sentinel solo auto-fix para bugs técnicos (DB, 500), no permisos de negocio
```

**Timeline:** ~30min validación + decisión director + 1h fix

**Bloquea Fase 2:** 🔴 **SÍ (hasta validar)**

---

### ✅ H1: FARMACIA 301

**Clasificación:** ✅ **FALSO_POSITIVO**

**Evidencia:**
- Auditor llama: `/farmacia/pdv/?accion=buscar_producto` (endpoint legacy)
- Endpoint real: `/farmacia/api/buscar-producto-pdv/?termino=...`
- pdv_farmacia devuelve 200 JSON (código correcto)
- Status 301 es porque auditor no tiene empresa/permisos

**Acción:**
- ❌ NO corregir código productivo
- ✅ Actualizar script auditoría para usar endpoint real
- ✅ Marcar como LEGACY_NO_ACTIVO

**Bloquea Fase 2:** ❌ **NO**

---

### 🟡 H2: AUDITORÍA LAB DEPRECATED

**Clasificación:** 🟡 **DEUDA_HERRAMIENTA**

**Evidencia:**
- Comando intencionalmente deprecated (línea 104-108)
- Laboratorio funciona con LIMS v7.5
- Solo herramienta de auditoría está desactualizada

**Acción:**
- ❌ NO arreglar comando deprecated
- ✅ Crear `auditoria_lab_lims_v75.py` nueva
- ✅ Validar endpoints LIMS actuales

**Bloquea Fase 2:** ❌ **NO**

---

## 📊 SÍNTESIS EJECUTIVA

| Hallazgo | Clasificación | Bloquea | Acción |
|----------|---------------|---------|--------|
| **P2** | CONFIRMADO ALTO | 🔴 SÍ | Quitar filtro empresa + test |
| **H3** | PROBABLE | 🔴 SÍ | Validar con datos reales PRISLAB |
| **H1** | FALSO_POSITIVO | ❌ NO | Ignorar, actualizar auditor |
| **H2** | DEUDA_HERRAMIENTA | ❌ NO | Crear auditoría LIMS v7.5 |

---

## 🔄 PRÓXIMOS PASOS (ORDEN ESTRICTO)

### **AHORA - Codex**
1. ✅ Implementar P2 fix (quitar filtro empresa)
2. ✅ Agregar test `test_director_analizadores_sin_fielderror`
3. ✅ Deploy seguro
4. ✅ Commit message claro

### **POST-P2 - Cascada + Claude**
1. ✅ Cascada valida H3 con usuario real jonathan
2. ✅ Cascada busca paciente real en PRISLAB
3. ✅ Cascada intenta `/medico/expediente/<id_real>/`
4. ✅ Cascada captura: respuesta, redirects, traceback
5. ✅ Claude valida evidencia
6. ✅ Si reproduce → enviar a Codex
7. ✅ Si NO reproduce → FALSO_POSITIVO, fin

### **POST-H3 - Claude**
1. ✅ Re-ejecutar Fase 1 completa
2. ✅ Validar P2 resuelto
3. ✅ Validar H3 estado
4. ✅ Reportar final

### **DECISIÓN - Director**
1. ✅ Revisar P2 + H3
2. ✅ Autorizar Fase 2 SI todo OK
3. ✅ O indicar correcciones si hay nueva evidencia

---

## 🎯 CRITERIO PARA FASE 2

**FASE 2 AUTORIZADA SI:**
- ✅ P2 está corregido y testeado
- ✅ H3 está validado (confirmado o descartado)
- ✅ H1 está descartado como falso positivo
- ✅ H2 está documentado como deuda técnica

**FASE 2 BLOQUEADA SI:**
- 🔴 P2 no está arreglado
- 🔴 H3 se reproduce sin solución

---

## 📝 FORMATO DE REPORTE FINAL

Todo reporte debe terminar con:

```markdown
## ESTADO FINAL

**Hallazgos confirmados:** [lista]
**Hallazgos probables:** [lista]
**Hallazgos pendientes:** [lista]
**Falsos positivos:** [lista]
**Deuda técnica:** [lista]

## ACCIONES PROPUESTAS

1. [Acción concreta]
2. [Acción concreta]
3. [Acción concreta]

## DECISIONES DEL DIRECTOR REQUERIDAS

- [ ] ¿DIRECTOR debería ver expedientes?
- [ ] ¿Equipo es multi-tenant o global?
- [ ] Autorizar Fase 2 SI/CUANDO?
```

---

**Versión:** 2.0 Ejecutiva y Operativa  
**Estado:** 🟢 APROBADO Y EN VIGOR  
**Próximo hito:** Codex implementa P2  
