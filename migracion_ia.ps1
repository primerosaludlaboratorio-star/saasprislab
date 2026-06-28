# SCRIPT DE MIGRACIÃ“N: google-generativeai -> google-genai
# PRISLAB V5.0 - 2 de Febrero 2026

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  MIGRACION DE MOTOR IA: GOOGLE-GENAI v1.0+  " -ForegroundColor White
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# 1. VERIFICAR CAMBIO EN REQUIREMENTS.TXT
Write-Host "[1/4] Verificando requirements.txt..." -ForegroundColor Yellow
$reqContent = Get-Content requirements.txt -Raw
if ($reqContent -match 'google-genai') {
    Write-Host "  [OK] google-genai detectado en requirements.txt" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] google-genai NO encontrado" -ForegroundColor Red
}

# 2. LISTAR ARCHIVOS QUE USAN GEMINI
Write-Host ""
Write-Host "[2/4] Identificando archivos con Gemini..." -ForegroundColor Yellow
$archivos = @(
    "core/services/ai_medico.py",
    "ia/views.py",
    "consultorio/views.py",
    "core/services/ai_medico_backup.py"
)

foreach ($archivo in $archivos) {
    if (Test-Path $archivo) {
        $matches = Select-String -Path $archivo -Pattern "genai\." -AllMatches
        Write-Host "  - $archivo : $($matches.Count) referencias" -ForegroundColor White
    }
}

# 3. RESUMEN
Write-Host ""
Write-Host "[3/4] Resumen de cambios necesarios:" -ForegroundColor Yellow
Write-Host "  - Reemplazar: import google.generativeai as genai" -ForegroundColor White
Write-Host "    Por: from google import genai" -ForegroundColor Green
Write-Host "  - Reemplazar: genai.configure(api_key=...)" -ForegroundColor White
Write-Host "    Por: client = genai.Client(api_key=...)" -ForegroundColor Green
Write-Host "  - Reemplazar: genai.GenerativeModel('...')" -ForegroundColor White
Write-Host "    Por: client.models.generate_content(model='...')" -ForegroundColor Green

# 4. SIGUIENTE PASO
Write-Host ""
Write-Host "[4/4] Proximo paso:" -ForegroundColor Yellow
Write-Host "  Aplicar refactorizacion manual a cada archivo" -ForegroundColor White
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan

