# Plan de cierre previo al E2E humano

**Proyecto:** PRISLAB SaaS
**Rama:** `release/v1.0-local`
**Ultimo codigo desplegado:** `a7b0804dd852ed5c3eadfc97d8fec681de8caf5c`
**Fecha de corte:** 2026-09-13

Este documento define lo que deben cerrar los editores de IA antes de iniciar
la certificacion manual en navegador. No autoriza cambios de contrasenas,
API keys, usuarios, datos productivos ni historial de evidencias.

## Cerrado con evidencia

- Despliegue por worktree limpio al VPS.
- Migracion `contabilidad.0014`: aplicada.
- `collectstatic`: completado.
- Gunicorn, Celery y Celery Beat: activos.
- Nginx valido y `/health/` HTTP 200.
- `/media/` no expone archivos inexistentes y responde 404.
- Helpers duplicados de mantenimiento y seguridad consolidados.
- `manage.py check` y `makemigrations --check`: correctos en el entorno local.
- Correcciones CAS-001 a CAS-009, webhook, Sentinel, PDF protegido e
  inmutabilidad de resultados LIMS: verificadas por pruebas dirigidas previas.

## Debe cerrarse antes del E2E humano

### P0. Runtime reproducible

- [ ] Ejecutar la suite con Python 3.12 real.
- [ ] Ejecutar la suite contra PostgreSQL de pruebas separado de producción.
- [ ] Obtener JUnit completo, sin truncar tracebacks ni convertir excepciones
      en avisos.
- [ ] Resultado requerido: cero fallos y cero errores; omisiones justificadas.

### P1. Calidad y cadena de suministro

- [ ] Ejecutar `pip-audit` contra `requirements.lock` sin bloqueo del runner.
- [ ] Confirmar que no queden vulnerabilidades sin excepción aprobada,
      caducidad y análisis de alcanzabilidad.
- [ ] Generar SBOM del mismo artefacto que se despliega.
- [ ] Ejecutar el workflow de quality gate y conservar la corrida del mismo SHA.
- [ ] Confirmar que el workflow de deploy solo pueda ejecutarse después del
      quality gate exitoso del mismo SHA.

### P1. Infraestructura

- [ ] Levantar y validar el stack Docker/Compose en staging, no en producción.
- [ ] Confirmar `PRISLAB_ENV=production`, TLS, cookies seguras y HSTS con las
      variables reales del entorno seguro.
- [ ] Corregir o aceptar formalmente el warning de sintaxis `listen ... http2`
      y conservar evidencia de `nginx -t`.
- [ ] Probar `limit_req` efectivo por location y los limites de subida por tipo
      de documento.
- [ ] Verificar que alias de static/media coincidan con los volúmenes reales.
- [ ] Ejecutar backup cifrado productivo en destino aislado y restore test,
      midiendo RPO/RTO sin tocar la base operativa.

### P1. Cobertura conductual automatizada

- [ ] Renderizar y parsear JavaScript embebido con contextos representativos.
- [ ] Ejecutar matriz automatizada de rutas por metodo HTTP, autenticacion,
      rol, tenant y respuesta esperada.
- [ ] Ejecutar pruebas de aislamiento simetricas para todos los modelos y vistas
      que expongan datos de negocio.
- [ ] Revisar los helpers/archivos legacy restantes y retirar solo codigo
      realmente muerto, conservando scripts documentales y evidencia autorizada.
- [ ] Reconciliar reportes historicos para que no contradigan el commit actual.

### P2. Higiene de release

- [ ] Separar artefactos de cobertura y pruebas temporales de codigo productivo.
- [ ] No incluir en el release archivos locales modificados sin revision.
- [ ] No incluir ni imprimir secretos; los scripts que los contienen permanecen
      fuera de remediacion hasta una decision especifica.
- [ ] Cascada debe auditar el SHA final despues de estos cierres.

## Fase final necesariamente humana

Solo cuando los puntos anteriores esten verdes:

- Flujo visual completo por modulo y por rol.
- Alta, edicion, cancelacion, devolucion, cobro parcial/total y corte de caja.
- Recepcion, toma, proceso, captura, validacion, PDF, entrega y maquila LIMS.
- Validacion de ortografia, claridad, navegacion, botones y mensajes visibles.
- Pruebas de falla de equipo, perdida de luz, controles no conformes y cambio
  de equipo, usando datos sinteticos y reversibles.

## Regla de cierre

Un punto solo se marca cerrado con comando, SHA, fecha, resultado y evidencia.
Un reporte que diga "sin hallazgos" sin ejecutar el control correspondiente se
clasifica como no verificado.
