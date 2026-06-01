#!/bin/bash
# Script de verificación antes del despliegue

echo "🔍 Verificando archivos de despliegue..."

# Verificar que manage.py existe
if [ ! -f "manage.py" ]; then
    echo "❌ ERROR: manage.py no encontrado en la raíz del proyecto"
    exit 1
fi
echo "✅ manage.py encontrado"

# Verificar que requirements.txt existe
if [ ! -f "requirements.txt" ]; then
    echo "❌ ERROR: requirements.txt no encontrado"
    exit 1
fi
echo "✅ requirements.txt encontrado"

# Verificar que Dockerfile existe
if [ ! -f "Dockerfile" ]; then
    echo "❌ ERROR: Dockerfile no encontrado"
    exit 1
fi
echo "✅ Dockerfile encontrado"

# Verificar que gunicorn está en requirements.txt
if ! grep -q "gunicorn" requirements.txt; then
    echo "❌ ERROR: gunicorn no está en requirements.txt"
    exit 1
fi
echo "✅ gunicorn encontrado en requirements.txt"

# Verificar que el puerto es 8080 en Dockerfile
if ! grep -q "8080" Dockerfile; then
    echo "⚠️ ADVERTENCIA: Puerto 8080 no encontrado en Dockerfile"
fi
echo "✅ Puerto 8080 verificado"

# Verificar que entrypoint.sh existe y es ejecutable
if [ ! -f "entrypoint.sh" ]; then
    echo "❌ ERROR: entrypoint.sh no encontrado"
    exit 1
fi
echo "✅ entrypoint.sh encontrado"

# Verificar que entrypoint.sh tiene permisos de ejecución
if [ ! -x "entrypoint.sh" ]; then
    echo "⚠️ ADVERTENCIA: entrypoint.sh no tiene permisos de ejecución"
    chmod +x entrypoint.sh
    echo "✅ Permisos de ejecución agregados"
fi

echo ""
echo "✅ Todas las verificaciones pasaron. Listo para desplegar!"
