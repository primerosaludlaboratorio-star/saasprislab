# Script para ejecutar migraciones en Cloud SQL desde local
# Requiere: Cloud SQL Proxy instalado y configurado

Write-Host "🔧 Ejecutando migraciones en Cloud SQL..." -ForegroundColor Cyan

# Variables de entorno de Cloud SQL
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "5432"
$env:DB_NAME = "prislab_db"
$env:DB_USER = "postgres"
$env:DB_PASSWORD = "Prislab2026!"
$env:SECRET_KEY = "AytJ3jR2NMJAlb_WmcrNOzxfQGUhhbsbd618nk-J92MS2SAQTyWB92cY8jEUBHsao0Y"
$env:DEBUG = "False"

Write-Host "📋 Variables de entorno configuradas" -ForegroundColor Green

# Ejecutar migraciones
Write-Host "🚀 Ejecutando: python manage.py migrate --noinput" -ForegroundColor Yellow
python manage.py migrate --noinput

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Migraciones completadas exitosamente" -ForegroundColor Green
} else {
    Write-Host "❌ ERROR: Las migraciones fallaron" -ForegroundColor Red
    exit 1
}
