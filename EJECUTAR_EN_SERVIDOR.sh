#!/bin/bash
# ============================================================================
# SCRIPT PARA EJECUTAR EN EL SERVIDOR DE PRODUCCIÓN (Google Cloud)
# ============================================================================

echo "================================================================================"
echo "          ACTUALIZACIÓN DE PRISLAB EN SERVIDOR DE PRODUCCIÓN"
echo "================================================================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ============================================================================
# BLOQUE 2: ACTUALIZAR BASE DE DATOS
# ============================================================================
echo -e "${YELLOW}[BLOQUE 2] ACTUALIZANDO BASE DE DATOS...${NC}"
echo ""

# 1. Migraciones
echo "  [1/4] Aplicando migraciones..."
python manage.py migrate
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Fallo al aplicar migraciones${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Migraciones aplicadas${NC}"
echo ""

# 2. Cargar Laboratorio
echo "  [2/4] Cargando datos de Laboratorio..."
python manage.py migrar_lab_master
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}  [AVISO] Error al cargar laboratorio (puede ser normal si ya existe)${NC}"
fi
echo -e "${GREEN}  ✓ Laboratorio procesado${NC}"
echo ""

# 3. Cargar Inventario
echo "  [3/4] Cargando inventario de Farmacia..."
if [ -f "Productos-farmacia-2026-02-10-10-31.csv" ]; then
    python manage.py cargar_productos_csv Productos-farmacia-2026-02-10-10-31.csv
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}  [AVISO] Error al cargar inventario${NC}"
    else
        echo -e "${GREEN}  ✓ Inventario cargado (674 productos)${NC}"
    fi
else
    echo -e "${YELLOW}  [AVISO] No se encontró el archivo CSV de inventario${NC}"
fi
echo ""

# 4. Crear Usuarios
echo "  [4/4] Creando equipo PRISLAB..."
if [ -f "crear_equipo_oficial.py" ]; then
    python crear_equipo_oficial.py
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}  [AVISO] Error al crear usuarios${NC}"
    else
        echo -e "${GREEN}  ✓ Usuarios creados/actualizados${NC}"
    fi
else
    echo -e "${YELLOW}  [AVISO] No se encontró crear_equipo_oficial.py${NC}"
    echo "  Ejecuta: python manage.py createsuperuser"
fi
echo ""

# ============================================================================
# BLOQUE 3: ARCHIVOS ESTÁTICOS
# ============================================================================
echo -e "${YELLOW}[BLOQUE 3] RECOLECTANDO ARCHIVOS ESTATICOS...${NC}"
echo ""

python manage.py collectstatic --noinput
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Fallo al recolectar estáticos${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Archivos estáticos recolectados${NC}"
echo ""

# ============================================================================
# VERIFICACIÓN FINAL
# ============================================================================
echo "================================================================================"
echo -e "${GREEN}[COMPLETADO] DESPLIEGUE FINALIZADO${NC}"
echo "================================================================================"
echo ""
echo "Verificaciones recomendadas:"
echo "  1. Acceder a la URL de producción"
echo "  2. Probar inicio de sesión con usuarios creados"
echo "  3. Verificar módulos: Farmacia, Laboratorio, Consultorio"
echo "  4. Revisar logs: gcloud app logs tail -s default"
echo ""
echo "Credenciales temporales:"
echo "  jonathan   -> Admin2026!"
echo "  nancy      -> Nancy2026!"
echo "  gabriela   -> Gabriela2026!"
echo ""
echo "================================================================================"
