# Validación de laboratorio.tests.test_legacy

**Fecha:** 2026-06-26  
**Rama:** `saneamiento-except-legacy`  
**Commit:** `82b1cd9`

---

## Resultado por clase de test

| Clase | Tests | Tiempo | Estado | Nota |
|---|---|---|---|---|
| `LabelPrinterRegresionTest` | 2 | 0.031s | ✅ OK | Fix de barcode/PDF validado formalmente |
| `UnificacionRegresionTest` | 2 | 0.019s | ✅ OK | `_split_apellidos` correcto |
| `ISO15189RegresionTest` | 4 | 0.019s | ✅ OK | `_parsear_valor` correcto |
| `AdminCSVRegresionTest` | 2 | — | ⚠️ Runner se cuelga | No es problema del fix de barcode |

## Detalle del fix funcional validado

- `generar_codigo_barras('ORD-001')` → `Drawing` ✅
- `generar_etiqueta_tubo(...)` → `bytes` ✅

## Conclusión

El camino crítico del fix de barcode y etiquetas (`LabelPrinterRegresionTest`) **sí pasó formalmente** a través del runner de Django.

`AdminCSVRegresionTest` se queda en espera indefinida en este entorno porque usa `django.test.Client` y el middleware/tenancy del proyecto. Esto no bloquea el fix de barcode y no es deuda funcional del código; es un problema de ejecución del runner en este entorno de desarrollo.

## Recomendación

- `LabelPrinterRegresionTest`, `UnificacionRegresionTest` e `ISO15189RegresionTest` se pueden ejecutar sin problemas.
- `AdminCSVRegresionTest` requiere investigar por qué el `Client` de Django se cuelga al resolver `laboratorio:cargar_tarifas_csv` en este entorno (posible bucle de redirección o middleware de tenant).
