# Inventario Unificado Reconciliado - PRISLAB

Fecha: 2026-06-24

Este documento unifica dos lecturas distintas del repo para que ninguna IA invente un punto de partida:

- **Claude** produjo un inventario estructural profundo por introspeccion de Django + AST.
- **Cascada** produjo un inventario ejecutable real del arbol activo, con clasificacion operativa.

No son documentos que compitan entre si. Se complementan.

---

## 1. Que cubre cada inventario

### 1.1 Inventario estructural de Claude

Cobertura:

- apps, modelos, clases y funciones
- superficie URL y APIs
- comandos de gestion y runners
- tests visibles por recorrido estructural
- marcadores de legado

Uso correcto:

- responder "que existe"
- dimensionar el tamanio del sistema
- localizar superficies aun no auditadas semantica o funcionalmente

Limite:

- no es la verdad operativa del runner real
- puede incluir estimaciones estructurales amplias
- no sustituye una ejecucion real ni un diff sobre el arbol actual

### 1.2 Inventario ejecutable de Cascada

Cobertura:

- arbol real presente en el checkout activo
- tests reales clasificados por ubicacion
- management commands reales clasificados por riesgo
- runners JS reales
- artefactos reales de `human:ui`

Uso correcto:

- responder "que puedo ejecutar hoy"
- decidir seguridad de seeds, destructivos, runners y hallazgos
- clasificar evidencia fresca

Limite:

- no reemplaza el mapa estructural de todo el sistema
- no debe usarse para decir que algo no existe si solo no esta en el subset ejecutable

---

## 2. Canon operativo actual

### Fuente de verdad para coordinacion multi-IA

1. `AI_COORDINATION_STATUS.md`
2. `INDICE_CANONICO_TOTAL.md`
3. `PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md`
4. `INVENTARIO_REAL_REPO.md`
5. Este documento de reconciliacion

### Fuente de verdad para ejecucion humana

- `tools/run_human_ui_audit.mjs`
- `run_human_ui_audit.bat`

### Fuente de verdad para evidencia valida

- `auditoria_ui_20260623_194820/report.md`
- `auditoria_ui_20260623_212952/report.md`
- sus respectivos `report.json` y capturas

---

## 3. Regla de alineacion

- Si un artefacto solo aparece en Claude, debe ser tratado como **inventario estructural pendiente de persistir**.
- Si un artefacto solo aparece en Cascada, debe ser tratado como **inventario ejecutable vigente**.
- Si un artefacto no aparece en `INDICE_CANONICO_TOTAL.md`, no es canon de coordinacion.
- Si un artefacto no aparece en `INVENTARIO_REAL_REPO.md`, no debe asumirse como parte del corte ejecutable actual.

---

## 4. Decision por tipo de pregunta

### Pregunta: "Que existe en el sistema?"

Responder con:

- `INVENTARIO_REAL_REPO.md`
- mas la lectura estructural de Claude si ya fue persistida

### Pregunta: "Que se puede ejecutar hoy?"

Responder con:

- `INVENTARIO_REAL_REPO.md`
- `PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md`
- `tools/run_human_ui_audit.mjs`

### Pregunta: "Que falta por documentar?"

Responder con:

- legacy / ruido todavia marcado como `D`
- inventario estructural pendiente de persistir
- artefactos de runner pendientes de versionar en ubicacion compartida

---

## 5. Estado actual resumido

### Ya alineado

- Existe un runner canonicamente definido para verificacion humana.
- Existe un inventario ejecutable real del repo.
- Existe una separacion clara entre canon operativo y ruido historico.

### Todavia pendiente

- Persistir la salida real del runner humano en una ubicacion compartida.
- Consolidar la lectura estructural de Claude en un documento persistido, si se decide.
- Clasificar o eliminar completamente el legacy documental restante.

---

## 6. Regla final

Ninguna IA debe volver a auditar "de memoria".
Primero se lee este documento, luego el indice canonico, luego el inventario correcto para la pregunta.
