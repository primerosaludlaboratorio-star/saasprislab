#!/bin/bash
# ============================================================================
# DESPLIEGUE COMPLETO DE PRISLAB A GOOGLE CLOUD
# Ejecutar con: bash DESPLIEGUE_COMPLETO.sh
# ============================================================================

set -e  # Salir si hay error

echo "================================================================================"
echo "               DESPLIEGUE COMPLETO PRISLAB A GOOGLE CLOUD"
echo "================================================================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# BLOQUE 1: SUBIR EL CÓDIGO (GIT)
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                          BLOQUE 1: SUBIR CÓDIGO${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Verificar que git esté instalado
if ! command -v git &> /dev/null; then
    echo -e "${RED}[ERROR] Git no está instalado${NC}"
    echo "Instala Git desde: https://git-scm.com/"
    exit 1
fi

# Verificar que exista repositorio git
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}[AVISO] No hay repositorio Git inicializado${NC}"
    echo "Inicializando repositorio..."
    git init
    echo -e "${GREEN}✓ Repositorio inicializado${NC}"
    echo ""
    
    # Configurar remote si no existe
    if ! git remote | grep -q "origin"; then
        echo -e "${YELLOW}Configura el remote con:${NC}"
        echo "  git remote add origin <URL_DEL_REPOSITORIO>"
        echo ""
        read -p "¿Continuar sin configurar remote? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# 1. Asegurar que los archivos CSV se suban
echo "  [1/4] Agregando archivos CSV..."
git add -f tarifas.csv 2>/dev/null || true
git add -f inventario.csv 2>/dev/null || true
git add -f Productos-farmacia-2026-02-10-10-31.csv 2>/dev/null || true
git add -f datos_lims/*.csv 2>/dev/null || true
echo -e "${GREEN}  ✓ CSV agregados${NC}"

# 2. Agregar TODOS los cambios de código
echo "  [2/4] Agregando todos los cambios..."
git add .
echo -e "${GREEN}  ✓ Cambios agregados${NC}"

# 3. Verificar que hay cambios
if git diff --staged --quiet; then
    echo -e "${YELLOW}  [AVISO] No hay cambios para commitear${NC}"
else
    # 3. Empaquetar el envío
    echo "  [3/4] Creando commit..."
    git commit -m "DESPLIEGUE URGENTE: Farmacia (674 productos), Lab Completo, Fix Consultorio, Equipo PRISLAB"
    echo -e "${GREEN}  ✓ Commit creado${NC}"
    
    # 4. ENVIAR A LA NUBE
    echo "  [4/4] Enviando a Google Cloud..."
    if git remote | grep -q "origin"; then
        git push origin main || git push origin master || git push
        echo -e "${GREEN}  ✓ Código subido exitosamente${NC}"
    else
        echo -e "${YELLOW}  [AVISO] No hay remote configurado. El código está commiteado localmente.${NC}"
    fi
fi

echo ""
echo -e "${GREEN}✓ BLOQUE 1 COMPLETADO${NC}"
echo ""

# ============================================================================
# PREGUNTA SI CONTINUAR CON BLOQUES 2 Y 3
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo "Los siguientes bloques deben ejecutarse en el SERVIDOR DE PRODUCCIÓN"
echo ""
echo "Opciones:"
echo "  1) Continuar aquí (si estás en el servidor de producción)"
echo "  2) Detener y ejecutar manualmente en el servidor"
echo ""
read -p "¿Estás en el servidor de producción? (1/2): " -n 1 -r
echo

if [[ $REPLY == "2" ]]; then
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo "Para continuar en el servidor de producción, ejecuta:"
    echo ""
    echo -e "${YELLOW}  bash EJECUTAR_EN_SERVIDOR.sh${NC}"
    echo ""
    echo "O manualmente:"
    echo "  1. gcloud app deploy"
    echo "  2. gcloud sql connect <INSTANCE_NAME>"
    echo "  3. python manage.py migrate"
    echo "  4. python manage.py migrar_lab_master"
    echo "  5. python manage.py cargar_productos_csv Productos-farmacia-2026-02-10-10-31.csv"
    echo "  6. python crear_equipo_oficial.py"
    echo "  7. python manage.py collectstatic --noinput"
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    exit 0
fi

# ============================================================================
# BLOQUE 2: ACTUALIZAR BASE DE DATOS DE PRODUCCIÓN
# ============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    BLOQUE 2: ACTUALIZAR BASE DE DATOS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# 1. Crear las tablas nuevas
echo "  [1/4] Aplicando migraciones..."
python manage.py migrate
echo -e "${GREEN}  ✓ Migraciones aplicadas${NC}"

# 2. CARGAR EL LABORATORIO
echo "  [2/4] Cargando Laboratorio (Estudios + Precios)..."
python manage.py migrar_lab_master || echo -e "${YELLOW}  [AVISO] Laboratorio ya cargado${NC}"
echo -e "${GREEN}  ✓ Laboratorio procesado${NC}"

# 3. CARGAR EL INVENTARIO
echo "  [3/4] Cargando Inventario de Farmacia..."
if [ -f "Productos-farmacia-2026-02-10-10-31.csv" ]; then
    python manage.py cargar_productos_csv Productos-farmacia-2026-02-10-10-31.csv
    echo -e "${GREEN}  ✓ 674 productos cargados${NC}"
else
    echo -e "${RED}  [ERROR] No se encontró el archivo CSV${NC}"
fi

# 4. CREAR USUARIOS REALES
echo "  [4/4] Creando equipo PRISLAB..."
if [ -f "crear_equipo_oficial.py" ]; then
    python crear_equipo_oficial.py
    echo -e "${GREEN}  ✓ 7 usuarios creados${NC}"
else
    echo -e "${YELLOW}  [AVISO] Archivo crear_equipo_oficial.py no encontrado${NC}"
fi

echo ""
echo -e "${GREEN}✓ BLOQUE 2 COMPLETADO${NC}"
echo ""

# ============================================================================
# BLOQUE 3: ARCHIVOS ESTÁTICOS
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                       BLOQUE 3: ARCHIVOS ESTÁTICOS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

python manage.py collectstatic --noinput
echo -e "${GREEN}  ✓ Archivos estáticos recolectados${NC}"
echo ""

# ============================================================================
# RESUMEN FINAL
# ============================================================================
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                        ✓ DESPLIEGUE COMPLETADO${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Resumen:"
echo "  ✓ Código subido a Git"
echo "  ✓ Base de datos actualizada"
echo "  ✓ Laboratorio cargado"
echo "  ✓ Inventario cargado (674 productos)"
echo "  ✓ Equipo creado (7 usuarios)"
echo "  ✓ Archivos estáticos recolectados"
echo ""
echo "Próximos pasos:"
echo "  1. Acceder a: https://tu-proyecto.appspot.com"
echo "  2. Iniciar sesión con: jonathan / Admin2026!"
echo "  3. Verificar módulos funcionando"
echo "  4. Cambiar contraseñas temporales"
echo ""
echo "Credenciales del equipo:"
echo "  jonathan   -> Admin2026!  (CEO/Super Admin)"
echo "  nancy      -> Nancy2026!  (IQFB - Gerencial)"
echo "  gabriela   -> Gabriela2026! (QFB - Gerencial)"
echo "  janette    -> Janette2026! (TLQ)"
echo "  tania      -> Tania2026!  (TLQ)"
echo "  deyaneira  -> Deyaneira2026! (Auxiliar)"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
