# Ground Truth - Superficie IA/LLM PRISLAB

Fecha: 2026-06-24

Este archivo resume hechos observados directamente en el codigo para que Cascada clasifique sobre evidencia real.

## Proveedor LLM real observado

- Gemini / Google: motor principal de negocio.
- DeepSeek: fallback secundario.
- Otros proveedores menores detectados en trazas de codigo: OpenAI, Cohere, Ollama, referencias GPT y una referencia aislada a Claude.

## Distribucion observada por referencia de codigo

- `gemini` en decenas de archivos del runtime.
- `google.generativeai` en multiples puntos de integracion.
- `deepseek` en un subconjunto menor como fallback.
- `openai`, `cohere`, `ollama`, `gpt-`, `claude`: apariciones aisladas o de bajo volumen, candidatas a legado / experimento / compatibilidad.

## Zonas reales de superficie IA

- `ia/` con endpoints propios.
- `core/agent/` con agente PRIS y tools operativas.
- `core/services/` con IA clinica, interpretacion, validador, OCR, voz.
- `core/views/pris_ia.py` y `core/views/ai_brain.py`.
- `core/utils/gemini_client.py`, `core/utils/deepseek_client.py`, `core/utils/rag_engine.py`, `core/utils/ia_resources.py`.

## Advertencia importante

`core/services/validador_ia.py` y `core/utils/ia_resources.py` no son IA de soporte pura:

- participan en flujos clinicos y de negocio reales,
- estan acoplados a validaciones del core,
- por lo tanto no deben clasificarse automaticamente como "solo soporte" o "legado".

## Uso correcto por Cascada

- Clasificar superficie IA/LLM en:
  - activa de negocio
  - soporte / operacion
  - tests y comandos
  - legado / ruido
- No mezclar la superficie IA con el core transaccional sin revisar acoplamientos reales.
- No reauditar desde memoria.

