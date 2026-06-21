param(
    [int]$Interval = 3
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Write-Host "PRISLAB AI Coordination Hub" -ForegroundColor Cyan
Write-Host "Proyecto: $Root"
Write-Host "Drop folders:"
Write-Host "  docs\ai_coordination\drop\claude"
Write-Host "  docs\ai_coordination\drop\cascada"
Write-Host "  docs\ai_coordination\drop\codex"
Write-Host ""

& $Python scripts\ai_coordination_hub.py watch --interval $Interval
