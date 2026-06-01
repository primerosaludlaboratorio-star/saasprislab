# 🚀 INSTRUCCIONES COMPLETAS DE DESPLIEGUE A PRODUCCIÓN

**Sistema:** PRISLAB SaaS v5.0  
**Destino:** Google Cloud Platform (App Engine)  
**Fecha:** 10 de Febrero de 2026

---

## 📋 REQUISITOS PREVIOS

Antes de iniciar el despliegue, asegúrate de tener:

### En tu máquina local:
- [x] Git instalado ([Descargar](https://git-scm.com/download/win))
- [x] Google Cloud SDK instalado ([Descargar](https://cloud.google.com/sdk/docs/install))
- [x] Cuenta de Google Cloud configurada
- [x] Repositorio Git configurado para tu proyecto

### Verificar instalaciones:
```bash
git --version
gcloud --version
python --version
```

---

## 🎯 TRES OPCIONES DE DESPLIEGUE

### OPCIÓN 1: Script Automático (Recomendado)
```bash
# Si tienes Git Bash o WSL
bash DESPLIEGUE_COMPLETO.sh
```

### OPCIÓN 2: Script por Bloques
```bash
# En Windows
DESPLEGAR_A_PRODUCCION.bat

# Luego en el servidor
bash EJECUTAR_EN_SERVIDOR.sh
```

### OPCIÓN 3: Comandos Manuales
Sigue los 3 bloques descritos abajo ↓

---

## ☁️ BLOQUE 1: SUBIR EL CÓDIGO

Este bloque empaqueta y envía todos los archivos al repositorio Git.

### Comandos:

```bash
# 1. Asegurar que los archivos CSV se suban
git add -f tarifas.csv
git add -f inventario.csv
git add -f Productos-farmacia-2026-02-10-10-31.csv
git add -f datos_legacy/*.csv

# 2. Agregar TODOS los cambios de código
git add .

# 3. Empaquetar el envío
git commit -m "DESPLIEGUE URGENTE: Farmacia (674 productos), Lab Completo, Fix Consultorio, Equipo PRISLAB"

# 4. ENVIAR A LA NUBE
git push origin main
# O si tu rama principal es master:
git push origin master
```

### ¿Qué pasa en este bloque?
- Se suben todos los archivos Python (views, models, templates)
- Se incluyen los CSV de inventario y laboratorio
- Se envían los scripts de migración
- Git activa el proceso de build en Google Cloud

### Verificación:
```bash
git status
# Debe decir: "nothing to commit, working tree clean"
```

---

## 📦 BLOQUE 2: ACTUALIZAR LA BASE DE DATOS

**IMPORTANTE:** Este bloque se ejecuta EN EL SERVIDOR DE PRODUCCIÓN.

### Opción A: Conectarse al Cloud SQL
```bash
# Conectar a la base de datos de producción
gcloud sql connect INSTANCE_NAME --user=root

# O usar Cloud Shell
gcloud cloud-shell ssh
```

### Opción B: Usar Cloud Shell directamente
1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Abre Cloud Shell (ícono >_ arriba a la derecha)
3. Clona el repositorio o conéctate a tu instancia

### Comandos:

```bash
# 1. Crear las tablas nuevas (Farmacia, Devoluciones, Chat)
python manage.py migrate

# 2. CARGAR EL LABORATORIO (Estudios + Precios FIFA)
python manage.py migrar_lab_master

# 3. CARGAR EL INVENTARIO (674 productos)
python manage.py cargar_productos_csv Productos-farmacia-2026-02-10-10-31.csv

# 4. CREAR USUARIOS REALES
python crear_equipo_oficial.py
```

### ¿Qué hace cada comando?

#### `migrate`
- Crea tablas: `farmacia_aperturacaja`, `farmacia_devolucionventa`, `core_voiceauditlog`, etc.
- Modifica campos existentes si es necesario
- Tiempo estimado: 30-60 segundos

#### `migrar_lab_master`
- Carga **Estudios** desde `datos_legacy/Examenes.csv`
- Carga **Parámetros** desde `datos_legacy/Parametros.csv`
- Carga **Paquetes** desde `datos_legacy/Paquetes.csv`
- Carga **Precios** desde `tarifas.csv`
- Carga **Rangos de Referencia** desde `datos_legacy/Valores_normalidad.csv`
- Tiempo estimado: 2-5 minutos

#### `cargar_productos_csv`
- Carga **674 productos** de farmacia
- Asigna precios, stocks, IVA
- Marca **87 antibióticos** para control COFEPRIS
- Tiempo estimado: 30 segundos

#### `crear_equipo_oficial`
- Crea **7 usuarios**:
  - jonathan (CEO/Super Admin)
  - nancy (IQFB - Gerencial)
  - gabriela (QFB - Gerencial)
  - janette (TLQ)
  - tania (TLQ)
  - deyaneira (Auxiliar)
  - brizia.nolasco (Doctora)
- Tiempo estimado: 5 segundos

### Verificación:
```bash
# Verificar productos cargados
python manage.py shell
>>> from core.models import Producto
>>> Producto.objects.count()
674

# Verificar usuarios
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> User.objects.filter(is_active=True).count()
7
```

---

## 🎨 BLOQUE 3: ARCHIVOS ESTÁTICOS

Este bloque recolecta todos los CSS, JavaScript, imágenes e íconos para que se vean correctamente en la web.

### Comando:

```bash
python manage.py collectstatic --noinput
```

### ¿Qué hace?
- Recolecta archivos de `/static` de todos los módulos
- Los copia a `/staticfiles` o al bucket de Google Cloud Storage
- Incluye: Bootstrap, Font Awesome, jQuery, CSS personalizados
- Tiempo estimado: 15-30 segundos

### Verificación:
```bash
# Debería mostrar algo como:
# 125 static files copied to '/staticfiles'
```

---

## ✅ VERIFICACIÓN FINAL

### 1. Acceder a la aplicación
```
https://tu-proyecto.appspot.com
```

### 2. Iniciar sesión
```
Usuario: jonathan
Contraseña: Admin2026!
```

### 3. Verificar módulos

#### Farmacia
- [ ] Ir a `/farmacia/dashboard/`
- [ ] Verificar que se vean 674 productos
- [ ] Probar búsqueda por código de barras
- [ ] Abrir caja (Apertura de Caja)
- [ ] Realizar venta de prueba
- [ ] Verificar Libro de Antibióticos

#### Laboratorio
- [ ] Ir a `/laboratorio/dashboard/`
- [ ] Verificar que se vean estudios disponibles
- [ ] Buscar un estudio específico
- [ ] Verificar precios cargados

#### Consultorio
- [ ] Ir a `/consultorio/dashboard/`
- [ ] Click en botón "NUEVO PACIENTE"
- [ ] Registrar paciente de prueba
- [ ] Verificar que se guardó correctamente

#### PRIS Comunicador
- [ ] Verificar botón flotante azul (esquina inferior derecha)
- [ ] Click para abrir chat
- [ ] Verificar que se ve el panel lateral

### 4. Revisar logs
```bash
# Ver logs en tiempo real
gcloud app logs tail -s default

# O en la consola web:
# https://console.cloud.google.com/logs
```

---

## 🔑 CREDENCIALES TEMPORALES

**IMPORTANTE:** Cambiar en el primer inicio de sesión

```
Super Admin:
  jonathan   → Admin2026!

Staff/Gerencial:
  nancy      → Nancy2026!
  gabriela   → Gabriela2026!

Técnicos:
  janette    → Janette2026!
  tania      → Tania2026!

Auxiliar:
  deyaneira  → Deyaneira2026!

Médico:
  brizia.nolasco → Brizia2026!
```

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### Error: "Git no reconocido"
**Causa:** Git no está instalado o no está en el PATH  
**Solución:**
1. Descargar Git: https://git-scm.com/download/win
2. Instalar con opción "Git from the command line"
3. Reiniciar terminal

### Error: "No remote configured"
**Causa:** El repositorio local no está vinculado a GitHub/GitLab  
**Solución:**
```bash
git remote add origin <URL_DEL_REPOSITORIO>
git push -u origin main
```

### Error: "Migration failed"
**Causa:** Puede haber un conflicto con la estructura existente  
**Solución:**
```bash
# Ver migraciones pendientes
python manage.py showmigrations

# Aplicar solo una app específica
python manage.py migrate farmacia
python manage.py migrate laboratorio
```

### Error: "File not found: Productos-farmacia..."
**Causa:** El archivo CSV no se subió correctamente  
**Solución:**
```bash
# Verificar que el archivo existe
ls -la *.csv

# Forzar agregado
git add -f Productos-farmacia-2026-02-10-10-31.csv
git commit --amend --no-edit
git push --force
```

### Error: "OperationalError: no such table"
**Causa:** Las migraciones no se aplicaron  
**Solución:**
```bash
python manage.py migrate --run-syncdb
```

### Error: "static files not loading"
**Causa:** collectstatic no se ejecutó o falló  
**Solución:**
```bash
# Limpiar y recolectar
python manage.py collectstatic --clear --noinput
python manage.py collectstatic --noinput

# Verificar configuración en settings.py
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
```

---

## 📊 RESUMEN DE LO QUE SE DESPLIEGA

### Código Python
- ✅ 3 módulos principales: Farmacia, Laboratorio, Consultorio
- ✅ 7 apps Django adicionales
- ✅ 150+ archivos Python
- ✅ 200+ templates HTML

### Base de Datos
- ✅ Estudios de laboratorio
- ✅ Parámetros clínicos
- ✅ Paquetes de estudios
- ✅ Precios actualizados
- ✅ 674 productos de farmacia
- ✅ 87 antibióticos controlados
- ✅ 7 usuarios del equipo

### Archivos Estáticos
- ✅ Bootstrap 5
- ✅ Font Awesome
- ✅ jQuery
- ✅ CSS personalizados
- ✅ Imágenes y logos

### Funcionalidades
- ✅ Sistema POS de Farmacia
- ✅ Control de Caja
- ✅ Devoluciones
- ✅ Libro de Control de Antibióticos (COFEPRIS)
- ✅ Registro de Pacientes
- ✅ Historia Clínica
- ✅ Procesamiento de Laboratorio
- ✅ PRIS Comunicador (Chat Interno)

---

## 🎉 ¡LISTO!

Una vez completados los 3 bloques, PRISLAB estará **completamente operativo en producción**.

### Próximos pasos:
1. Capacitar al equipo
2. Realizar pruebas operativas
3. Configurar impresoras
4. Establecer procedimientos
5. ¡Iniciar operaciones! 🚀

---

**Creado por:** Jonathan Alonso Samos Sánchez + Cursor + Gemini  
**Fecha:** 10 de Febrero de 2026  
**Sistema:** PRISLAB SaaS v5.0
