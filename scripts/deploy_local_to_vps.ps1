[CmdletBinding()]
param(
    [string]$HostName = "216.238.89.243",
    [string]$User = "prislab",
    [string]$KeyPath = "$HOME\.ssh\id_ed25519",
    [string]$AppDir = "/opt/prislab/app",
    [string]$Domain = "https://prislab.labcorecloud.com",
    [switch]$SkipHealthCheck
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
$revision = (& git -C $repoRoot rev-parse HEAD).Trim()
$archive = Join-Path ([IO.Path]::GetTempPath()) "prislab-$revision.tar.gz"
$remoteArchive = "/tmp/prislab-$revision.tar.gz"
$target = "$User@$HostName"
$sshOptions = @("-i", $KeyPath, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=15")

if (-not (Test-Path -LiteralPath $KeyPath)) { throw "SSH key not found: $KeyPath" }
if (-not (Get-Command tar.exe -ErrorAction SilentlyContinue)) { throw "tar.exe is required" }
if (-not (Get-Command scp.exe -ErrorAction SilentlyContinue)) { throw "scp.exe is required" }
if (-not (Get-Command ssh.exe -ErrorAction SilentlyContinue)) { throw "ssh.exe is required" }

Write-Host "Preflight SSH: $target"
& ssh.exe @sshOptions $target "test -d '$AppDir' && id -u && echo SSH_OK"
if ($LASTEXITCODE -ne 0) { throw "SSH preflight failed" }

if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
Write-Host "Creating local artifact $revision"
& tar.exe -czf $archive `
    --exclude=.git `
    --exclude=.env `
    --exclude=.env.* `
    --exclude=.venv `
    --exclude=media `
    --exclude=staticfiles `
    --exclude=logs `
    --exclude=__pycache__ `
    --exclude=.pytest_cache `
    --exclude=node_modules `
    -C $repoRoot .
if ($LASTEXITCODE -ne 0) { throw "Could not create deployment artifact" }

Write-Host "Uploading artifact without GitHub"
& scp.exe @sshOptions $archive "${target}:$remoteArchive"
if ($LASTEXITCODE -ne 0) { throw "Artifact upload failed" }

$remoteScript = @'
set -euo pipefail
APP_DIR='__APP_DIR__'
ARCHIVE='__ARCHIVE__'
REVISION='__REVISION__'
RELEASE_DIR="/opt/prislab/releases/$REVISION"
mkdir -p "$RELEASE_DIR"
tar -xzf "$ARCHIVE" -C "$RELEASE_DIR"
rsync -a --delete \
  --exclude='.git/' --exclude='.env' --exclude='.venv' --exclude='media/' \
  --exclude='staticfiles/' --exclude='logs/' \
  "$RELEASE_DIR/" "$APP_DIR/"
printf '%s\n' "$REVISION" > "$APP_DIR/DEPLOYED_REVISION"
chown -R prislab:prislab "$APP_DIR"
cd "$APP_DIR"
sudo -u prislab .venv/bin/python scripts/run_manage_with_env.py migrate --noinput
sudo -u prislab .venv/bin/python scripts/run_manage_with_env.py collectstatic --noinput
systemctl restart prislab-gunicorn
systemctl restart prislab-celery
systemctl restart prislab-celerybeat
systemctl reload nginx
systemctl is-active prislab-gunicorn
systemctl is-active prislab-celery
systemctl is-active prislab-celerybeat
rm -f "$ARCHIVE"
echo "DEPLOYED_REVISION=$(cat "$APP_DIR/DEPLOYED_REVISION")"
'@
$remoteScript = $remoteScript.Replace("__APP_DIR__", $AppDir)
$remoteScript = $remoteScript.Replace("__ARCHIVE__", $remoteArchive)
$remoteScript = $remoteScript.Replace("__REVISION__", $revision)

Write-Host "Applying artifact on VPS"
& ssh.exe @sshOptions $target $remoteScript
if ($LASTEXITCODE -ne 0) { throw "Remote deployment failed" }

if (-not $SkipHealthCheck) {
    Write-Host "Checking $Domain/health/"
    $response = Invoke-WebRequest -UseBasicParsing -Uri "$Domain/health/" -TimeoutSec 30
    if ($response.StatusCode -ne 200) { throw "Health check failed: $($response.StatusCode)" }
}

Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
Write-Host "Local-to-VPS deployment completed: $revision"
