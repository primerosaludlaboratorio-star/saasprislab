# Vultr Object Storage — Guía de configuración

**Estado:** Código listo y probado (`manage.py check` OK). NO activo en producción todavía — falta crear el bucket y cargar las credenciales en el `.env` del VPS.

Esta guía existe para que cualquiera (dueño, Codex, Claude) pueda retomar esta tarea sin tener que releer todo el código primero.

---

## 1. Qué ya existe en el código (no hay que programar nada)

| Pieza | Archivo |
|---|---|
| Lectura de variables de entorno `VULTR_*` y mapeo a `AWS_*` (django-storages) | [config/settings.py:386-438](config/settings.py#L386) |
| Backend de almacenamiento real, con aislamiento por tenant (`{empresa_slug}/...`) | [config/storage_backends.py — clase `TenantS3Storage`](config/storage_backends.py) |
| Backend por defecto si Vultr no está activo (buffer local + sync async a Drive) | `config.storage_backends.BufferLocalStorage` |
| Ejemplo de variables | [.env.example:34-42](.env.example#L34) |

**Prioridad de backends:** si `VULTR_OBJECT_STORAGE_ENABLED=True` Y las 4 variables obligatorias están completas → Vultr gana siempre, incluso sobre Google Drive directo (ver `config/settings.py:447-450`). Si falta alguna variable, el sistema NO truena: solo deja un warning en logs y sigue con `BufferLocalStorage` (archivo local, sin nube).

---

## 2. Pasos en el panel de Vultr (los hace el dueño, no un agente de IA)

1. Entrar a **Vultr → Almacenamiento de Objetos** (⚠️ NO "Container Registry", son cosas distintas y ya hubo confusión sobre esto antes).
2. Crear un bucket nuevo. Elegir la región más cercana al VPS de PRISLAB (revisar en qué región está el droplet/VPS actual de PRISLAB para que la latencia sea mínima — ideal que estén en la misma región).
3. Dentro del bucket, ir a la pestaña de **Claves de acceso S3 (Access Keys)** y generar una nueva clave. Vultr muestra el **Secret Key solo una vez** — copiarlo de inmediato a un lugar seguro.
4. Anotar estos 4 datos:
   - **Access Key ID**
   - **Secret Access Key**
   - **Nombre del bucket**
   - **Endpoint de la región** (tiene la forma `https://<region>.vultrobjects.com`, ej. `ewr1` = Newark, `atl2` = Atlanta, `sjc1` = San José, `lax1` = Los Ángeles — depende de qué región eligió Vultr al crear el bucket, está visible en el panel).

---

## 3. Variables a agregar en el `.env` de producción del VPS

Ruta típica: `/opt/prislab/.env` (ajustar según el layout real confirmado en memoria del proyecto).

```bash
VULTR_OBJECT_STORAGE_ENABLED=True
VULTR_S3_ACCESS_KEY_ID=<access_key_id>
VULTR_S3_SECRET_ACCESS_KEY=<secret_access_key>
VULTR_S3_ENDPOINT_URL=https://<region>.vultrobjects.com
VULTR_S3_BUCKET_NAME=<nombre_del_bucket>

# Opcionales:
VULTR_S3_CUSTOM_DOMAIN=               # solo si se configura un CDN/dominio propio sobre el bucket
VULTR_S3_QUERYSTRING_AUTH=True        # True = URLs firmadas con expiración (recomendado para datos clínicos)
VULTR_S3_FILE_OVERWRITE=False         # evita que un archivo nuevo pise uno viejo con el mismo nombre
VULTR_S3_DEFAULT_ACL=                 # dejar vacío salvo necesidad específica de ACL pública
```

Después de editar el `.env`, reiniciar el proceso Django/Gunicorn y los workers de Celery (los archivos en background también usan este storage).

---

## 4. Cómo confirmar que quedó activo

1. Revisar logs del proceso al iniciar — debe aparecer:
   ```
   [STORAGE] Vultr Object Storage activo como backend default (<bucket> / <endpoint>)
   ```
   Si en cambio aparece `Vultr Object Storage habilitado pero incompleto. Faltan variables: ...` — falta alguna de las 4 variables obligatorias.

2. Subir un archivo de prueba desde el sistema (ej. una foto de evidencia en Contabilidad Personal, o un resultado de laboratorio) y confirmar en el panel de Vultr que el objeto aparece en el bucket bajo la carpeta del slug de la empresa correspondiente.

---

## 5. Migración de archivos existentes (Drive → Vultr)

**No existe todavía** un script de migración masiva de los archivos que ya están en Google Drive hacia Vultr. Si se decide migrar el histórico (no solo los archivos nuevos), hay que escribir un comando de management que:
1. Recorra los modelos con campos `FileField`/`ImageField` que usan `get_google_drive_storage`.
2. Descargue cada archivo de Drive.
3. Lo suba a Vultr usando `TenantS3Storage`.
4. Actualice la referencia en el campo del modelo.

Esto es trabajo pendiente, no bloqueante: el sistema puede operar con Drive para el histórico y Vultr para todo lo nuevo, y migrar después con calma.

---

## 6. Resumen de qué falta para cerrar esta tarea

- [ ] Dueño crea el bucket en Vultr y genera las claves de acceso S3 (paso manual, no delegable a un agente de IA).
- [ ] Dueño comparte las 4 variables obligatorias.
- [ ] Agente (Claude/Codex) agrega las variables al `.env` de producción y reinicia servicios.
- [ ] Verificar logs + subir archivo de prueba.
- [ ] (Opcional, no bloqueante) Escribir script de migración del histórico de Drive.
