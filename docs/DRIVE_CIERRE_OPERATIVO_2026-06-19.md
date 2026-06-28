# Cierre Operativo Google Drive - 2026-06-19

## Estado real

PRISLAB ya tiene el codigo listo para trabajar con Google Drive mediante **Service Account**:

- `config/drive_credentials.py` resuelve credenciales desde:
  - `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`
  - `GOOGLE_APPLICATION_CREDENTIALS`
- `config/storage_backends.py` y `core/utils/google_drive.py` ya manejan:
  - fallback local seguro
  - errores `403` y `404`
  - compatibilidad con `Shared Drive`
  - bloqueo de permisos publicos `anyone-with-link`

## Hallazgo clave del JSON entregado

El archivo JSON entregado el `2026-06-19` corresponde a esta identidad:

- `project_id`: `prislab-v5-ai`
- `client_email`: `811785477499-compute@developer.gserviceaccount.com`

Eso significa que **no coincide** con las cuentas previamente compartidas en Drive:

- `prislab-drive@prislab-v5-ai.iam.gserviceaccount.com`
- `vertex-express@prislab-v5-ai.iam.gserviceaccount.com`

## Conclusion tecnica

El problema de Drive ya no esta en el codigo base. El punto pendiente es de **alineacion de identidad + arquitectura de Google Drive**:

1. Si se usara este JSON, la carpeta o Shared Drive debe compartirse exactamente con:
   - `811785477499-compute@developer.gserviceaccount.com`
2. Si se prefiere mantener el share actual, entonces se necesita el JSON de la cuenta de servicio que ya tiene acceso.
3. Si la carpeta sigue viviendo en `My Drive`, la escritura puede seguir fallando con:
   - `403 storageQuotaExceeded`
4. La solucion robusta para produccion es mover `PRISLAB_Media` a un **Shared Drive**.

## Recomendacion final

Para cerrar Drive correctamente:

1. Crear o usar un **Shared Drive**
2. Mover `PRISLAB_Media` ahi
3. Compartirlo con la cuenta de servicio cuyo JSON se instale en la VPS
4. Configurar en produccion:
   - `GOOGLE_APPLICATION_CREDENTIALS=/opt/prislab/credentials/google-drive.json`
   - `GOOGLE_DRIVE_FOLDER_ID=<ID real del folder o Shared Drive root/folder>`
5. Ejecutar validacion con:

```bash
python scripts/validar_drive_setup.py
```

## Nota operativa

Mientras eso no ocurra, PRISLAB puede seguir funcionando con el fallback local ya implementado, pero **Drive no debe marcarse como cerrado al 100%**.
