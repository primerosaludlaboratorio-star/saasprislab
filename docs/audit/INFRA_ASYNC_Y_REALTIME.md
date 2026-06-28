# INFRA_ASYNC_Y_REALTIME — Tareas en background y canales en tiempo real

**Objetivo:** Documentar funciones de ejecución que **no** aparecen en `urlpatterns` HTTP estándar.

---

## 1. Celery (`config/celery.py`, `config/__init__.py`)

| Nombre registrado | Función Python | Cola | Rol |
| :--- | :--- | :--- | :--- |
| `core.tasks.storage_tasks.sincronizar_archivo_drive` | `sincronizar_archivo_drive` en `core/tasks/storage_tasks.py` | `drive_sync` | Sube archivo desde buffer local a Google Drive; reintentos con backoff |
| `core.tasks.storage_tasks.resinc_buffer_pendiente` | `resinc_buffer_pendiente` en `core/tasks/storage_tasks.py` | `drive_sync` | Reencola archivos antiguos en buffer (red de seguridad) |
| — | `debug_task` en `config/celery.py` (`@app.task`) | default | Depuración / request dump |

**Autodescubrimiento:** `app.autodiscover_tasks()` registra tareas `@shared_task` en apps instaladas.

**Configuración:** `CELERY_BROKER_URL` deriva de `REDIS_URL` o `memory://` (`config/settings.py`). Worker sugerido en comentarios de `celery.py`.

**Fallback:** `config/storage_backends.py` puede subir en hilo daemon si Celery no está disponible.

---

## 2. WebSocket / ASGI (`config/asgi.py`, `core/routing.py`)

| Ruta WS | Consumer | Módulo |
| :--- | :--- | :--- |
| `ws/voice/walkie/<room_name>/` | `WalkieTalkieConsumer` | `core/consumers.py` |
| `ws/voice/commands/` | `VoiceCommandConsumer` | `core/consumers.py` |

**Pila:** `ProtocolTypeRouter` — HTTP vía `get_asgi_application()`, WebSocket vía `AllowedHostsOriginValidator` + `AuthMiddlewareStack` + `URLRouter(websocket_urlpatterns)`.

---

## 3. Punto de entrada WSGI

| Archivo | Callable | Uso |
| :--- | :--- | :--- |
| `config/wsgi.py` | `application` | Gunicorn en Docker / despliegue HTTP tradicional |
