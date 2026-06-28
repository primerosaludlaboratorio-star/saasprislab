# Plan de Reparto Modular - PRISLAB

Fecha: 2026-06-24

Este documento define el orden exacto de trabajo para evitar choques entre Claude y Cascada.
La idea es que ambos trabajen el mismo proyecto, pero en un orden distinto, con entregables propios,
y luego se crucen para que Codex cierre al final.

---

## 1. Reglas del reparto

- Claude y Cascada trabajan **el mismo tipo de objetivo**: refactorizacion y alineacion al canon oficial.
- No trabajan el mismo modulo al mismo tiempo.
- Cada uno avanza solo cuando termina el modulo anterior de su propia secuencia.
- Cuando ambos terminan un modulo, se cruzan reportes antes de pasar al siguiente bloque.
- Codex no improvisa: solo integra lo que ambos validaron o lo que el usuario autoriza.
- Si hay contradiccion, no se cierra sola.

---

## 2. Orden de trabajo de Claude

### Secuencia de Claude

1. **Core**
2. **Farmacia**
3. **Laboratorio**
4. **Consultorio**
5. **IA**
6. **Tests**

### Lo que hace en cada modulo

- revisa el codigo real contra el canon vigente
- identifica funciones, vistas, servicios, tests y comandos del modulo
- aplica refactorizacion o correccion si tiene evidencia suficiente
- documenta cambios con rutas absolutas y lineas exactas
- deja listo el reporte maestro del modulo

### Lo que no hace

- no se salta modulos
- no reaudita desde memoria
- no mezcla legacy documental con codigo vivo
- no cierra cambios sin evidencia

### Entregable

- `docs/ai_coordination/outbox/REPORTE_CLAUDE_[MODULO]_2026-06-24.md`

---

## 3. Orden de trabajo de Cascada

### Secuencia de Cascada

1. **Tests**
2. **Consultorio**
3. **Farmacia**
4. **IA**

### Lo que hace en cada modulo

- revisa evidencia real, hallazgos y cambios ya hechos
- encuentra contradicciones, huecos o deuda que Claude no vio
- clasifica si algo queda como confirmado, probable, pendiente o ruido
- documenta legacy, placeholders, reportes viejos y ruido documental
- deja listo el reporte maestro del modulo

### Lo que no hace

- no repite el trabajo de Claude
- no reaudita desde memoria
- no toma core ni laboratorio salvo como referencia de contradiccion
- no mezcla evidencia humana con ruido historico

### Entregable

- `docs/ai_coordination/outbox/REPORTE_CASCADA_[MODULO]_2026-06-24.md`

---

## 4. Puntos de cruce

### Claude revisa a Cascada en:

- Tests
- Consultorio
- Farmacia
- IA

### Cascada revisa a Claude en:

- Core
- Farmacia
- Laboratorio
- Consultorio
- IA
- Tests

### Regla del cruce

- Si coinciden, se marca alineado.
- Si no coinciden, se marca contradiccion.
- Codex solo integra cuando ya hay cruce.

---

## 5. Orden operativo exacto para el usuario

### Ronda 1

- Claude: Core
- Cascada: Tests

### Ronda 2

- Claude: Farmacia
- Cascada: Consultorio

### Ronda 3

- Claude: Laboratorio
- Cascada: Farmacia

### Ronda 4

- Claude: Consultorio
- Cascada: IA

### Ronda 5

- Claude: IA
- Cascada: cruza lo que le toque contra Claude

### Ronda 6

- Claude: Tests
- Cascada: cruza el cierre final de la secuencia

### Cierre

- Codex integra codigo, docs y regresiones
- El usuario autoriza la promoción al canon

---

## 6. Formato mínimo de cada reporte

Cada reporte debe incluir:

- modulo
- archivos revisados
- funciones / vistas / servicios revisados
- evidencia
- cambios aplicados
- riesgos
- cerrado
- pendiente
- siguiente modulo sugerido

---

## 7. Regla final

No se avanza al siguiente modulo hasta que:

- el agente termine el modulo actual,
- entregue su reporte,
- y el otro agente lo revise o quede listo para cruce.

