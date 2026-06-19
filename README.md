# 🏥 PRISLAB SaaS v5.0 — LabCoreCloud

**Sistema de Gestión Integral para Clínicas, Laboratorios y Farmacias**

🌐 **Producción:** [https://prislab.labcorecloud.com](https://prislab.labcorecloud.com)

![Estado](https://img.shields.io/badge/Estado-Producción-success)
![Versión](https://img.shields.io/badge/Versión-5.0-blue)
![Django](https://img.shields.io/badge/Django-5.0-green)
![Python](https://img.shields.io/badge/Python-3.14-blue)
![VPS](https://img.shields.io/badge/Deploy-Vultr_VPS-blue)
![SSL](https://img.shields.io/badge/SSL-Let's_Encrypt-green)

---

## 📋 Índice

- [Características Principales](#características-principales)
- [Módulos del Sistema](#módulos-del-sistema)
- [Tecnologías](#tecnologías)
- [Instalación Local](#instalación-local)
- [Despliegue en Producción](#despliegue-en-producción)
- [Credenciales de Acceso](#credenciales-de-acceso)
- [Documentación](#documentación)
- [Equipo](#equipo)

---

## ✨ Características Principales

### 🎯 Multi-Tenant
- Sistema preparado para gestionar múltiples empresas/sucursales
- Identidad dinámica (logo, colores, branding por empresa)
- Aislamiento total de datos entre empresas

### 🤖 Inteligencia Artificial Integrada
- **Google Gemini 1.5 Pro** para:
  - Transcripción de voz a texto (consultas médicas)
  - OCR (Optical Character Recognition)
  - Asistente médico inteligente
  - Generación de contenido educativo

### 💊 Control Farmacéutico ERP
- **Kardex Inmutable** con trazabilidad forense
- **Costo Promedio Ponderado** automático
- **Libro de Control COFEPRIS** (NOM-072-SSA1-2012)
- Control de antibióticos con receta médica
- Sistema de devoluciones

### 🔬 Laboratorio Clínico (LIMS)
- **554 Estudios Clínicos** cargados
- **494 Parámetros** vinculados
- **17 Paquetes/Perfiles** pre-configurados
- Rangos de normalidad por edad/sexo
- Generación de resultados automáticos

### 🏥 Consultorio Médico
- **"Gemelo Digital"** - Vista previa en tiempo real
- Expediente clínico electrónico
- Recetas médicas en PDF
- Certificados médicos
- Historia clínica SOAP

### 📊 Dashboard Director
- Métricas en tiempo real
- Análisis financiero
- Control de inventarios
- Reportes personalizables

---

## 🧩 Módulos del Sistema

| # | Módulo | Estado | Descripción |
|---|--------|--------|-------------|
| 1 | **Consultorio** | ✅ | Consultas, recetas, expediente clínico |
| 2 | **Laboratorio** | ✅ | LIMS completo, resultados, órdenes |
| 3 | **Farmacia** | ✅ | PDV, inventario, control COFEPRIS |
| 4 | **Recepción** | ✅ | Registro de pacientes, agendamiento |
| 5 | **Enfermería** | ✅ | Triage, signos vitales |
| 6 | **Pacientes** | ✅ | Portal del paciente, historial 360° |
| 7 | **Marketing** | 🟡 | Campañas, cupones QR, WhatsApp |
| 8 | **Contabilidad** | ✅ | Facturación CFDI 4.0 |
| 9 | **Finanzas** | ✅ | Cajas segregadas (Lab + Farmacia) |
| 10 | **Bienestar** | ✅ | Diario emocional, recursos |
| 11 | **Logística** | ✅ | Transferencias, rutas |
| 12 | **Seguridad** | ✅ | 2FA, auditoría, sesiones |
| 13 | **IA/Chat** | 🟡 | Asistente PRIS, chatbot |
| 14 | **IoT** | ✅ | Kiosco de auto-verificación |
| 15 | **Director** | ✅ | Panel ejecutivo, KPIs |
| 16 | **RRHH** | 🔄 | En desarrollo |
| 17 | **Comunicación** | ✅ | Mensajería interna |
| 18 | **Cotización** | ✅ | Cotizador rápido |
| 19 | **Catálogos** | ✅ | Gestión de catálogos maestros |
| 20 | **Capacitación** | ✅ | Manual integrado, RAG Academy |

**Leyenda:** ✅ Completado | 🟡 Funcional (pendiente API Key) | 🔄 En desarrollo

---

## 🛠️ Tecnologías

### Backend
- **Django 5.0.6** - Framework web
- **Python 3.14** - Lenguaje principal en producción
- **PostgreSQL 18** - Base de datos en la VPS actual
- **Gunicorn** - Servidor WSGI
- **Redis** - Caché y mensajería

### Frontend
- **Bootstrap 5** - Framework CSS
- **JavaScript Vanilla** - Sin frameworks pesados
- **Chart.js** - Gráficas interactivas
- **Font Awesome 6** - Iconografía

### APIs y Servicios
- **Google Gemini** - Inteligencia Artificial
- **Google Drive API** - Respaldo y almacenamiento de archivos clínicos

### PDF y Reportes
- **ReportLab** - Generación de PDFs
- **WeasyPrint** - PDFs desde HTML
- **Pillow** - Procesamiento de imágenes

---

## 🚀 Instalación Local

### Requisitos Previos
- Python 3.11+
- PostgreSQL 14+ (o SQLite para desarrollo)
- Git

### Pasos

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/PRISLAB_SaaS.git
cd PRISLAB_SaaS
```

2. **Crear entorno virtual**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
Crea un archivo `.env` en la raíz:
```bash
DEBUG=True
SECRET_KEY=tu-secret-key-aqui
GOOGLE_API_KEY=tu-api-key-de-gemini

# Base de datos (opcional, usa SQLite por defecto)
# DB_NAME=prislab_v5
# DB_USER=postgres
# DB_PASSWORD=tu-password
# DB_HOST=localhost
# DB_PORT=5432
```

5. **Ejecutar migraciones**
```bash
python manage.py migrate
```

6. **Cargar datos iniciales**
```bash
# Catálogo de laboratorio
python manage.py migrar_lab_completo

# Inventario de farmacia
python cargar_excel_robusto.py

# Tarifas
python cargar_tarifas.py
```

7. **Crear superusuario**
```bash
python manage.py createsuperuser
# O usar el script automático:
python crear_superusuario_admin.py
```

8. **Iniciar servidor**
```bash
python manage.py runserver
```

9. **Acceder al sistema**
```
http://localhost:8000
```

---

## 🌐 Despliegue en Producción

### Opción Única: VPS Vultr + Nginx + Gunicorn + PostgreSQL

**Documentación canónica:** Ver [DEPLOY.md](DEPLOY.md)

Flujo recomendado:
1. Preparar la VPS con Ubuntu, `ufw`, `nginx`, `postgresql` y `certbot`
2. Clonar el repositorio en `/opt/prislab/app`
3. Copiar `.env.production.example` a `/opt/prislab/app/.env` y completar secretos
4. Ejecutar `sudo bash /opt/prislab/app/scripts/deploy_vps.sh`
5. Cuando hagas una actualización, ejecutar `sudo bash /opt/prislab/app/scripts/aplicar_fixes_produccion.sh`
6. Si necesitas subdominios futuros, ejecutar `/opt/prislab/app/scripts/activar_wildcard_ssl.sh` con un token de Cloudflare válido

**Wildcard SSL activo**
- Certificado actual: `labcorecloud-wildcard`
- Cubre `labcorecloud.com` y `*.labcorecloud.com`
- Renovación de prueba: `sudo certbot renew --dry-run && sudo systemctl reload nginx`

**Servicios que sí se conservan del ecosistema Google:**
- Google Gemini
- Google Drive API

**Nota de operación:** la plataforma principal está diseñada para operar en `https://prislab.labcorecloud.com`; el wildcard `*.labcorecloud.com` queda como el paso opcional de ampliación.

---

## 🔐 Credenciales de Acceso

### Superusuario (Admin)
```
Usuario: admin
Contraseña: PrislabV5_2026
```

### Equipo Prislab (7 usuarios)
| Usuario | Nombre | Rol | Contraseña |
|---------|--------|-----|------------|
| jonathan | Jonathan Alonso | CEO/Super Admin | Prislab2024$ |
| nancy | Nancy | Gerente General | Prislab2024$ |
| gabriela | Gabriela | Q.C. Laboratorio | Prislab2024$ |
| janette | Janette | Recepcionista | Prislab2024$ |
| tania | Tania | Recepcionista | Prislab2024$ |
| deyaneira | Deyaneira | Auxiliar Lab | Prislab2024$ |
| brizia.nolasco | Brizia Nolasco | Médico | Prislab2024$ |

---

## 📚 Documentación

La carpeta raíz contiene **257 archivos de documentación** en Markdown:

### Documentos Clave

- **`SISTEMA_COMPLETO_LISTO.md`** - Estado actual del sistema
- **`MANUAL_COMPLETO_PRISLAB_V5.md`** - Manual de usuario completo
- **`PLAN_MAESTRO_NUCLEO_PRIS_VALLE_2030.md`** - Visión y roadmap
- **`ARQUITECTURA_BLINDAJE_FARMACEUTICO_ERP.md`** - Arquitectura técnica
- **`BITACORA_MASTER_ESTADO_SISTEMA.md`** - Historial de cambios
- **`RESUMEN_EJECUTIVO_HOY.md`** - Estado al día de hoy

### Por Categoría

- **Auditorías:** `AUDITORIA_*.md` (31 documentos)
- **Reportes:** `REPORTE_*.md` (41 documentos)
- **Bloques:** `BLOQUE*.md` (implementaciones completadas)
- **Planes:** `PLAN_*.md` (roadmaps y estrategias)

---

## 👥 Equipo

**Creado por:** Jonathan Alonso Samos Sánchez  
**Con ayuda de:** Cursor AI + Google Gemini  
**Fecha de inicio:** Enero 2026  
**Última actualización:** 10 de Febrero 2026

### Equipo PRISLAB
- **Jonathan** - CEO / Super Admin
- **Nancy** - Gerente General
- **Gabriela** - Q.C. Laboratorio
- **Janette** - Recepción
- **Tania** - Recepción
- **Deyaneira** - Auxiliar Lab
- **Brizia Nolasco** - Médico

---

## 📊 Estadísticas del Sistema

- **Líneas de código:** ~50,000+
- **Modelos Django:** 150+
- **Vistas:** 200+
- **Templates HTML:** 300+
- **Archivos JavaScript:** 50+
- **Documentación:** 257 archivos MD
- **Productos farmacia:** 674
- **Estudios laboratorio:** 554
- **Usuarios activos:** 7

---

## 🗺️ Roadmap (PRIS-VALLE 2030)

### Fase 1: La Cara ✅
- [x] UI/UX unificada
- [x] PWA instalable
- [x] Identidad dinámica

### Fase 2: El Motor ✅
- [x] VPS Vultr
- [x] PostgreSQL
- [x] Nginx + Gunicorn

### Fase 3: El Cerebro Dual ✅
- [x] PRIS (Prislab - ejecutivo)
- [x] LIA (Valle - familiar)
- [x] Function calling

### Fase 4: Crecimiento 🔄
- [x] Academy (RAG)
- [x] Roleplay
- [ ] Campañas éticas completas

### Fase 5: Operaciones 🔄
- [ ] Geolocalización avanzada
- [ ] Facturación 4.0 completa
- [ ] Logística optimizada

---

## 📄 Licencia

Propietario - Todos los derechos reservados © 2026 PRISLAB

---

## 🆘 Soporte

Para soporte técnico, consulta la documentación o contacta al equipo de desarrollo.

---

**PRISLAB SaaS v5.0 - Sistema de Gestión Médica de Clase Mundial** 🏥💊🔬

*"Tecnología al servicio de la salud"*
