$ErrorActionPreference = "Stop"

$files = @(
    "datos_lims\Valores_normalidad.csv",
    "datos_lims\Tarifa_estudios de laboratorio.csv",
    "datos_lims\Parametros.csv",
    "datos_lims\Examenes_Perfil.csv",
    "datos_lims\Examenes.csv",
    "tarifas.csv"
)

$pattern = '(?i)canin|canino|canina|felin|felino|felina|equin|equino|equina|veterin|vet-'
$encoding = [System.Text.UTF8Encoding]::new($false)
$summary = @()

foreach ($relativePath in $files) {
    $path = Join-Path (Get-Location) $relativePath
    if (-not (Test-Path -LiteralPath $path)) { continue }
    $content = [System.IO.File]::ReadAllText($path)
    $newline = if ($content.Contains("`r`n")) { "`r`n" } else { "`n" }
    $lines = $content -split "`r?`n", 0
    $kept = @($lines | Where-Object { $_ -notmatch $pattern })
    [System.IO.File]::WriteAllText($path, ($kept -join $newline).TrimEnd("`r", "`n") + $newline, $encoding)
    $summary += [pscustomobject]@{ File = $relativePath; Removed = $lines.Count - $kept.Count }
}

$summary | Format-Table -AutoSize
