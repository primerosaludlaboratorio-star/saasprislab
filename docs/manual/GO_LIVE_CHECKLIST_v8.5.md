# Runbook de despliegue: PRISLAB v8.5 (go-live)

Este documento detalla los pasos para desplegar la versión 8.5 (refactor de capa de servicios, LIMS y arquitectura multi-tenant) en producción.

## Fase 1: Pre-despliegue (local)

- [ ] Verificar que la rama de release (`release/v8.5-fase3-contratos-api`) tiene todos los tests en verde (`python manage.py test`).
- [ ] Limpiar archivos temporales de QA locales (`htmlcov/`, `.coverage`).

  En Windows (PowerShell):

  ```powershell
  Remove-Item -Recurse -Force htmlcov -ErrorAction SilentlyContinue
  Remove-Item -Force .coverage -ErrorAction SilentlyContinue
  ```

  En Unix:

  ```bash
  rm -rf htmlcov
  rm -f .coverage
  ```

- [ ] Fusionar código hacia la rama principal:

  ```bash
  git checkout master
  git merge release/v8.5-fase3-contratos-api
  git push origin master
  ```

## Fase 2: Despliegue (servidor / cloud)

- [ ] **Aviso operativo:** notificar a sucursales una ventana de mantenimiento de 5–10 minutos.
- [ ] **Descarga de código:** `git pull origin master` (si el despliegue es sobre VM con repo en disco).
- [ ] **Migraciones (crítico):** aplicar migraciones, incluido el parche multi-tenant de reglas de negocio (`reglas_negocio`).

  ```bash
  python manage.py migrate
  ```

- [ ] **Estáticos:** recolectar estáticos para el frontend y el panel de administración.

  ```bash
  python manage.py collectstatic --noinput
  ```

- [ ] **Reinicio del servicio:**
  - Si es **VM:** `sudo systemctl restart <tu-servicio>` (sustituir por el nombre real del unit).
  - Si es **Cloud Run:** `gcloud run deploy <tu-servicio> --source .` (o el flujo CI/CD que usen).

## Fase 3: Smoke tests (pruebas de humo en vivo)

Con el sistema arriba, entrar con cuenta de administrador (o la que corresponda):

- [ ] **Módulo PDV (farmacia):** cobrar un producto y confirmar que el stock se descuenta correctamente.
- [ ] **Módulo LIMS (triple llave):** capturar resultados para un paciente.
  - **Prueba de rechazo:** intentar validar con orden con saldo pendiente (debe responder error, p. ej. `TRIPLE_LLAVE` / reglas de negocio).
  - **Prueba de éxito:** validar con orden pagada y comprobar que el flujo completa y el estado refleja resultados listos / validado según su pantalla.
- [ ] **Módulo LIMS (pánico):** introducir un valor crítico (p. ej. glucosa en rango de pánico) y verificar alerta o flujo de escudo clínico según configuración.

## Fase 4: Rollback (emergencia)

Si el smoke test falla de forma grave:

1. Revertir el merge o el commit problemático en Git, por ejemplo:

   ```bash
   git revert -m 1 HEAD
   git push origin master
   ```

2. Repetir la **Fase 2** (deploy) con el árbol revertido.
3. Analizar logs (p. ej. correlación con `X-Request-ID` si aplica) con el equipo de desarrollo.

---

*Última actualización: checklist v8.5 — alineado a rama `release/v8.5-fase3-contratos-api` y rama principal `master`.*
