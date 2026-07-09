# ADR 0004: Colaboración secuencial entre editores AI

**Estado:** Aceptado  
**Fecha:** 2026-07-09

## Contexto

Dos editores AI (Cascade y Antigravity) trabajan en el mismo repositorio. El riesgo de conflictos de merge y sobreescritura es alto si ambos modifican el mismo conjunto de archivos en paralelo.

## Decisión

Usar un modelo secuencial:
1. Editor 1 (Cascade) entrega Fase 1 (infra/CI/CD/monitoreo).
2. Editor 2 (Antigravity) entrega Fase 2 (migración funcional P0).
3. Editor 1 entrega Fase 3 (security/SDLC).
4. Editor 2 entrega Fase 4 (governance/performance).
5. Editor 1 integra todo en Fase 5.

Cada fase termina con PR a `release/v1.0-local`, revisado por Editor 1.

## Consecuencias

- Reduce conflictos de merge drásticamente.
- Editor 1 controla la calidad e integración final.
- Menor velocidad aparente que trabajo paralelo, pero mayor predictibilidad.
- Requiere que el Product Owner valide handoffs entre fases.

## Alternativas consideradas

- Trabajo paralelo con ownership de archivos: más rápido pero con más riesgo de conflictos.
- Trabajo totalmente independiente: imposible en un monolito Django.
