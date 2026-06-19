# Academia / Diplomados

Módulo Django integrado para cursos y reproducción de video con Bunny Stream.

## Rutas principales

- `/academia/` listado de cursos accesibles
- `/academia/cursos/<slug>/` detalle y reproductor del curso
- `/academia/api/videos/<id>/reproducir/` obtiene el embed firmado
- `/academia/api/videos/<id>/heartbeat/` registra avance de visualización
- `/academia/accesos/otorgar/` otorga acceso a un curso

## Variables de entorno

- `BUNNY_LIBRARY_ID`
- `BUNNY_STREAM_API_KEY`
- `BUNNY_EMBED_SECURITY_KEY`
- `BUNNY_PLAYER_BASE_URL`
- `ACADEMIA_EMPRESAS_PERMITIDAS`

## Flujo de carga

1. Sube los videos a Bunny Stream.
2. Crea el curso en Django.
3. Registra los videos en orden dentro del curso.
4. Otorga accesos a usuarios o empresas.

Por defecto el módulo solo queda habilitado para `PRISLAB`. Si más adelante otro laboratorio contrata la academia, agrega su nombre, slug o ID a `ACADEMIA_EMPRESAS_PERMITIDAS`.

## Sincronización masiva

Usa el comando:

```bash
python manage.py sincronizar_academia_bunny <carpeta> --empresa-id=1 --curso-titulo="Diplomado"
```

Ese comando crea el curso, sube los videos y deja un mapeo JSON con los GUID de Bunny.
