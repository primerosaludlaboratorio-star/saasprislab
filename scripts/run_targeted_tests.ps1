[CmdletBinding()]
param(
    [string[]]$TestLabel = @('iot')
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $python = 'python'
}

# Evita el coste y la fragilidad de reconstruir todas las migraciones en cada
# corrida local; la base de pruebas sigue siendo aislada por Django.
$env:PRISLAB_TEST_NO_MIGRATIONS = '1'
Push-Location $repoRoot
try {
    & $python manage.py test @TestLabel --keepdb --verbosity 1
    if ($LASTEXITCODE -ne 0) {
        throw "La suite dirigida fallo con codigo $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
