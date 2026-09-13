[CmdletBinding()]
param(
    [string]$HostName = "216.238.89.243",
    [string]$User = "prislab",
    [string]$KeyPath = "$HOME\.ssh\id_ed25519",
    [string]$AppDir = "/opt/prislab/app",
    [string]$Domain = "https://prislab.labcorecloud.com",
    [string]$ExpectedRevision = "",
    [switch]$SkipHealthCheck
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
$revision = (& git -C $repoRoot rev-parse HEAD).Trim()
$status = @(& git -C $repoRoot status --porcelain)
if ($LASTEXITCODE -ne 0) { throw "Could not inspect Git working tree" }
if ($status.Count -gt 0) {
    throw "Deployment blocked: working tree is not clean. Commit the reviewed release before deploying."
}
if ($ExpectedRevision -and $ExpectedRevision -ne $revision) {
    throw "Deployment blocked: HEAD $revision does not match ExpectedRevision $ExpectedRevision."
}
$trackedRevision = (& git -C $repoRoot rev-parse --verify HEAD).Trim()
if ($trackedRevision -ne $revision -or $revision -notmatch '^[0-9a-f]{40}$') {
    throw "Deployment blocked: invalid release revision."
}
$archive = Join-Path ([IO.Path]::GetTempPath()) "prislab-$revision.tar.gz"
$remoteArchive = "/tmp/prislab-$revision.tar.gz"
$target = "$User@$HostName"
$sshOptions = @("-i", $KeyPath, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=15")

if (-not (Test-Path -LiteralPath $KeyPath)) { throw "SSH key not found: $KeyPath" }
if (-not (Get-Command scp.exe -ErrorAction SilentlyContinue)) { throw "scp.exe is required" }
if (-not (Get-Command ssh.exe -ErrorAction SilentlyContinue)) { throw "ssh.exe is required" }
foreach ($requiredFile in @(
    (Join-Path $repoRoot "nginx\conf.d\prislab.conf"),
    (Join-Path $repoRoot "nginx\conf.d\00-prislab-limits.conf")
)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required deployment file not found: $requiredFile"
    }
}

Write-Host "Preflight SSH: $target"
& ssh.exe @sshOptions $target "test -d '$AppDir' && id -u && echo SSH_OK"
if ($LASTEXITCODE -ne 0) { throw "SSH preflight failed" }

if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
Write-Host "Creating local artifact $revision"
& git -C $repoRoot archive --format=tar.gz --output=$archive $revision
if ($LASTEXITCODE -ne 0) { throw "Could not create deployment artifact" }

Write-Host "Uploading artifact without GitHub"
& scp.exe @sshOptions $archive "${target}:$remoteArchive"
if ($LASTEXITCODE -ne 0) { throw "Artifact upload failed" }

$remoteNginxConfig = "/tmp/prislab-nginx-$revision.conf"
$remoteNginxLimits = "/tmp/prislab-nginx-limits-$revision.conf"
Write-Host "Uploading managed Nginx configuration"
& scp.exe @sshOptions (Join-Path $repoRoot "nginx\conf.d\prislab.conf") "${target}:$remoteNginxConfig"
if ($LASTEXITCODE -ne 0) { throw "Nginx configuration upload failed" }
& scp.exe @sshOptions (Join-Path $repoRoot "nginx\conf.d\00-prislab-limits.conf") "${target}:$remoteNginxLimits"
if ($LASTEXITCODE -ne 0) { throw "Nginx rate-limit configuration upload failed" }

$remoteScript = @'
set -euo pipefail
APP_DIR='__APP_DIR__'
ARCHIVE='__ARCHIVE__'
REVISION='__REVISION__'
NGINX_CONFIG='__NGINX_CONFIG__'
NGINX_LIMITS='__NGINX_LIMITS__'
RELEASE_DIR="/opt/prislab/releases/$REVISION"
mkdir -p "$RELEASE_DIR"
tar -xzf "$ARCHIVE" -C "$RELEASE_DIR"
rsync -a --delete \
  --exclude='.git/' --exclude='.env' --exclude='.venv' --exclude='media/' \
  --exclude='staticfiles/' --exclude='logs/' \
  "$RELEASE_DIR/" "$APP_DIR/"
install -o root -g root -m 0644 "$NGINX_CONFIG" /etc/nginx/sites-enabled/prislab
install -o root -g root -m 0644 "$NGINX_LIMITS" /etc/nginx/conf.d/00-prislab-limits.conf
nginx -t
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
rm -f "$NGINX_CONFIG"
rm -f "$NGINX_LIMITS"
echo "DEPLOYED_REVISION=$(cat "$APP_DIR/DEPLOYED_REVISION")"
'@
$remoteScript = $remoteScript.Replace("__APP_DIR__", $AppDir)
$remoteScript = $remoteScript.Replace("__ARCHIVE__", $remoteArchive)
$remoteScript = $remoteScript.Replace("__REVISION__", $revision)
$remoteScript = $remoteScript.Replace("__NGINX_CONFIG__", $remoteNginxConfig)
$remoteScript = $remoteScript.Replace("__NGINX_LIMITS__", $remoteNginxLimits)
# OpenSSH on Linux must receive the heredoc with Unix line endings.
$remoteScript = $remoteScript -replace "`r`n", "`n"

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
