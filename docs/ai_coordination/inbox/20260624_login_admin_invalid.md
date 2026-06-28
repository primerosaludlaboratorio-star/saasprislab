# Login Revalidation - Admin Credential Invalid

Fecha: 2026-06-24

## Evidencia

- `GET /home/` responde `302` hacia `/login/`
- `admin` existe y está activo
- `admin` no tiene TOTP activo
- el flag `2FA_OBLIGATORIO_ACTIVO` está en `False` para su empresa
- `authenticate(username='admin', password='[redacted]')` devuelve `False`

## Veredicto

- El fallo de la última corrida no es 2FA.
- Tampoco parece ser un 500 directo de `/home/`.
- El problema reproducido es que la credencial `admin` ya no autentica con esa contraseña en la base actual.

## Lectura operativa

- El runner no está roto por sí mismo.
- La credencial usada para la revalidacion debe actualizarse o volver a sincronizarse antes de repetir la corrida humana.
