# 🏥 PRISLAB SaaS V5 — Plataforma Clínica Integral

**PRISLAB** es un SaaS clínico multi-tenant diseñado para laboratorios, farmacias y consultorios. Unifica operaciones de **LIMS (Laboratorio)**, **PDV Farmacia**, **Inventario**, **Facturación CFDI 4.0**, **Nómina**, **CRM**, **Bienestar NOM-035** y un **Asistente IA** conversacional.

---

## 🧠 Stack Tecnológico

| Capa | Tecnología |
|---|---|
| **Backend** | Django 5.0.6 + Python 3.11+ |
| **API** | Django Ninja (OpenAPI) |
| **Base de Datos** | PostgreSQL 15+ |
| **Cache / Colas** | Redis + Celery + Channels |
| **Frontend** | Django Templates + PWA + WebSockets |
| **Storage** | Local (WhiteNoise) + Google Drive / S3 (Vultr) |
| **IA** | DeepSeek, Gemini, RAG (ChromaDB) |
| **Seguridad** | 2FA (pyotp), Fernet, HSTS, CSP, OWASP Top 10 |
| **Notificaciones** | Web Push (VAPID), Email, Telegram |
| **Contenedores** | Docker + docker-compose |

---

## 📦 Módulos del Sistema

| Módulo | App | Descripción |
|---|---|---|
| 🏥 **Laboratorio (LIMS)** | `laboratorio/` | Órdenes, estudios, resultados, etiquetas, HL7 |
| 💊 **Farmacia / PDV** | `farmacia/` | Ventas, kardex, compras, corte de caja, devoluciones |
| 📦 **Inventario** | `inventario/` | Stock, lotes, mermas, alertas de caducidad |
| 👥 **Pacientes** | `pacientes/` | Expediente clínico, portal del paciente |
| 🔐 **Seguridad** | `seguridad/` | 2FA, sesiones, auditoría de accesos |
| 💰 **Contabilidad** | `contabilidad/` | CFDI 4.0 (Facturama), reportes fiscales |
| 🧠 **IA** | `ia/` + `core/views/ia*` | Chat, OCR, voz, RAG, PRIS-Jarvis |
| 📊 **Nómina** | `core/views/nomina.py` | Periodos, recibos, cálculo |
| 🤝 **CRM** | `core/views/crm.py` | Prospectos, kanban, seguimiento |
| 🧘 **Bienestar** | `core/views/bienestar*` | NOM-035, diario emocional, alertas RRHH |
| 🎓 **Academia** | `academia/` | Diplomados, capacitación, RAG |
| 🛡️ **Sentinel** | `core/views/sentinel*` | Monitoreo, telemetría, GitHub, push |
| 📈 **Dashboard Director** | `core/views/director*` | KPI, coaching, biblioteca, calidad |

---

## ⚙️ Requisitos

- **Python** 3.11 o superior
- **PostgreSQL** 15 o superior
- **Redis** 7+ (opcional, fallback a memoria)
- **Node.js** 18+ (solo para tooling E2E)

---

## 🚀 Setup Local

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd PRISLAB_SaaS-master

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores (DB, APIs, etc.)

# 5. Base de datos
createdb prislab_v5
python manage.py migrate

# 6. Crear superusuario
python manage.py createsuperuser

# 7. Iniciar servidor
python manage.py runserver
```

---

## 🔐 Variables de Entorno (`.env`)

| Variable | Obligatoria | Descripción |
|---|---|---|
| `SECRET_KEY` | ✅ | Clave secreta de Django |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | ✅ | Conexión PostgreSQL |
| `DEEPSEEK_API_KEY` | ⚠️ | Para módulo IA (DeepSeek) |
| `GEMINI_API_KEY` | ⚠️ | Para módulo IA (Gemini) |
| `FACTURAMA_USER`, `FACTURAMA_PASSWORD` | ⚠️ | Facturación CFDI 4.0 |
| `FERNET_KEY` | ✅ en prod | Cifrado de campos sensibles |
| `LAB_VALIDATION_PIN` | ✅ en prod | PIN de validación (mín. 8 chars) |
| `REDIS_URL` | ⚠️ | Cache/colas (fallback a memoria) |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | ⚠️ | Notificaciones email |
| `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY` | ⚠️ | Web Push notifications |

> **⚠️ Seguridad**: Nunca commitees el archivo `.env` real. Usa `.env.example` como plantilla.

---

## 🧪 Tests

```bash
# Ejecutar todos los tests
python manage.py test core.tests laboratorio.tests farmacia.tests

# Tests específicos
python manage.py test core.tests.test_auditoria_segura_global

# Con cobertura
coverage run manage.py test
coverage report
```

---

## 🐳 Docker (Producción)

```bash
docker-compose up -d
```

---

## 📁 Arquitectura de Carpetas

```
PRISLAB_SaaS-master/
├── config/              # Configuración Django (settings, urls, asgi, wsgi)
├── core/                # Módulo central (views, models, tasks, tests)
│   ├── views/           # Vistas organizadas por dominio
│   ├── models/          # Modelos compartidos
│   ├── tests/           # 80+ tests unitarios
│   └── management/      # Comandos personalizados
├── laboratorio/         # Módulo LIMS
├── farmacia/            # Módulo Farmacia / PDV
├── inventario/          # Módulo Inventario
├── pacientes/           # Módulo Pacientes
├── seguridad/           # Módulo Seguridad (2FA)
├── contabilidad/        # Módulo Contabilidad (CFDI)
├── academia/            # Módulo Academia
├── ia/                  # Módulo IA
├── lims/                # Integración LIMS
├── middleware_local/    # Middleware para dispositivos locales
├── static/              # Archivos estáticos
├── templates/           # Templates globales
└── docs/                # Documentación y auditorías
```

---

## 📜 Licencia

Uso interno — PRISLAB. Todos los derechos reservados.
