# Human UI Audit - 2026-06-24

## Resultado

- Ejecutado con `npm run human:ui:cloud`
- Base URL: `https://prislab.labcorecloud.com`
- Usuario: `admin`
- Contraseña: `[redacted]`
- Resultado general: `OK`

## Flujos verificados

- Login: autenticado y redirigido a `/dashboard/`
- Root: sin `500`
- `/home/`: sin `500`
- Laboratorio: input de búsqueda aceptó texto
- Farmacia: búsqueda PDV aceptó texto

## WARNs observados

- Consultorio: no se detectó botón de acción de cita en la pantalla inicial
- Director: la página abrió, pero el runner no encontró una acción clave

## Hallazgos

- Ninguno

## Artefactos

- `auditoria_ui_20260624_021539/report.json`
- `auditoria_ui_20260624_021539/report.md`
- `auditoria_ui_20260624_021539/screenshots/`
