# ADR 0005: Secret scanning con gitleaks

**Estado:** Aceptado  
**Fecha:** 2026-07-09

## Contexto

El repositorio contiene múltiples APIs y tokens de terceros (DeepSeek, Gemini, Facturama, VAPID, etc.). Necesitamos evitar fugas de secretos en commits.

## Decisión

Usar `gitleaks` a través de `gitleaks/gitleaks-action@v2` en GitHub Actions. Se ejecuta en cada push y PR.

## Motivación

- Herramienta madura y ampliamente usada.
- No requiere mantener reglas propias (usa las reglas por defecto de gitleaks).
- Integración sencilla con GitHub Actions.

## Consecuencias

- Si se detecta un secreto, el workflow falla y bloquea el PR.
- Es posible que haya falsos positivos; se manejan con allowlisting en `.gitleaks.toml` si es necesario.
- Requiere configurar `GITLEAKS_LICENSE` para la acción oficial.

## Alternativas consideradas

- GitHub secret scanning nativo: requiere GitHub Advanced Security en repos privados.
- Detect-secrets: bueno pero menos maduro en CI.
- TruffleHog: más potente, pero más complejo de configurar.
