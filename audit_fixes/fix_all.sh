#!/usr/bin/env bash
# =============================================================================
# PRISLAB SaaS — Master Fix Script (all P0/P1 audit findings)
# Run from any location:  bash audit_fixes/fix_all.sh /path/to/PRISLAB_SaaS-master
# =============================================================================
set -euo pipefail

TARGET="${1:-$(pwd)}"
echo "=== PRISLAB Audit Fix Script ==="
echo "Target: $TARGET"
echo ""

# ─── Fix 1: Dockerfile — cloudrun_web_entrypoint.sh → web_entrypoint.sh ──────
echo "[Fix 1] Dockerfile entrypoint path..."
DOCKERFILE="$TARGET/Dockerfile"
if grep -q "cloudrun_web_entrypoint.sh" "$DOCKERFILE"; then
  sed -i 's|scripts/cloudrun_web_entrypoint\.sh|scripts/web_entrypoint.sh|g' "$DOCKERFILE"
  echo "  ✓ Fixed: cloudrun_web_entrypoint.sh → web_entrypoint.sh"
else
  echo "  ✓ Already fixed or not present"
fi

# ─── Fix 2: requirements.txt — remove duplicate numpy ─────────────────────────
echo "[Fix 2] Remove duplicate numpy from requirements.txt..."
REQ="$TARGET/requirements.txt"
if grep -c "^numpy>=" "$REQ" | grep -q "2"; then
  grep -v "^numpy>=1\.26\.0$" "$REQ" > "$REQ.tmp" && mv "$REQ.tmp" "$REQ"
  echo "  ✓ Removed numpy>=1.26.0 (kept numpy>=1.26.4)"
else
  echo "  ✓ No duplicate numpy found"
fi

# ─── Fix 3: CI — Python 3.11 → 3.12 + migration check ───────────────────────
echo "[Fix 3] GitHub Actions — Python version + migration check..."
CI="$TARGET/.github/workflows/main.yml"
if grep -q '"3.11"' "$CI"; then
  sed -i 's/python-version: "3\.11"/python-version: "3.12"/' "$CI"
  sed -i 's/Set up Python 3\.11/Set up Python 3.12/' "$CI"
  echo "  ✓ Updated Python version to 3.12"
else
  echo "  ✓ Python version already 3.12"
fi
if ! grep -q "migrate --check" "$CI"; then
  sed -i '/- name: Django system check/{
n
n
a\
\      - name: Migration check\
        run: python manage.py migrate --check --no-input\
}' "$CI"
  echo "  ✓ Added migration check step"
else
  echo "  ✓ Migration check already present"
fi

# ─── Fix 4: database.py — DB_CONN_MAX_AGE default ────────────────────────────
echo "[Fix 4] database.py — persistent connection default..."
DB_SETTINGS="$TARGET/config/settings/database.py"
if grep -q "0 if IS_PRODUCTION else 60" "$DB_SETTINGS"; then
  sed -i "s/_env_int('DB_CONN_MAX_AGE', 0 if IS_PRODUCTION else 60)/_env_int('DB_CONN_MAX_AGE', 60)  # 60s persistent connections/" "$DB_SETTINGS"
  echo "  ✓ Fixed DB_CONN_MAX_AGE default to 60"
else
  echo "  ✓ Already fixed"
fi

# ─── Fix 5: cache.py — Redis-backed sessions ─────────────────────────────────
echo "[Fix 5] cache.py — Redis session engine..."
CACHE_SETTINGS="$TARGET/config/settings/cache.py"
if grep -q "SESSION_ENGINE = 'django.contrib.sessions.backends.db'" "$CACHE_SETTINGS" && \
   ! grep -q "SESSION_ENGINE = 'django.contrib.sessions.backends.cache'" "$CACHE_SETTINGS"; then
  python3 - <<'PYEOF'
import sys
f = sys.argv[1]
with open(f, 'r') as fh:
    src = fh.read()
old = "    _cache_logger.info('[CACHE] Backend Redis activo (ubicación omitida en logs por seguridad)')\nelse:\n"
new = "    _cache_logger.info('[CACHE] Backend Redis activo (ubicación omitida en logs por seguridad)')\n    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'\n    SESSION_CACHE_ALIAS = 'default'\nelse:\n"
src2 = src.replace(old, new)
old2 = "    _cache_logger.info('[CACHE] LocMem (desarrollo)')\n\n# ── SESIONES ──────────────────────────────────────────────────────────────────\nSESSION_ENGINE = 'django.contrib.sessions.backends.db'\n"
new2 = "    _cache_logger.info('[CACHE] LocMem (desarrollo)')\n    SESSION_ENGINE = 'django.contrib.sessions.backends.db'\n\n# ── SESIONES ──────────────────────────────────────────────────────────────────\n"
src2 = src2.replace(old2, new2)
with open(f, 'w') as fh:
    fh.write(src2)
print('  ✓ Fixed Redis session engine')
PYEOF
  python3 - "$CACHE_SETTINGS"
else
  echo "  ✓ Already fixed"
fi

# ─── Fix 6: nginx conf — X-Forwarded-For, CSP, HSTS ─────────────────────────
echo "[Fix 6] nginx/conf.d/prislab.conf — headers..."
NGINX="$TARGET/nginx/conf.d/prislab.conf"
sed -i 's/proxy_set_header X-Forwarded-For \$remote_addr;/proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;/' "$NGINX"
sed -i 's/max-age=63072000/max-age=31536000/' "$NGINX"
if ! grep -q "Content-Security-Policy" "$NGINX"; then
  sed -i '/add_header Referrer-Policy/a\    add_header Content-Security-Policy "default-src '"'"'self'"'"'; script-src '"'"'self'"'"' '"'"'unsafe-inline'"'"'; style-src '"'"'self'"'"' '"'"'unsafe-inline'"'"'; img-src '"'"'self'"'"' data: blob:; font-src '"'"'self'"'"'; connect-src '"'"'self'"'"' wss:; frame-ancestors '"'"'none'"'"';" always;' "$NGINX"
fi
echo "  ✓ Fixed X-Forwarded-For, HSTS max-age, added CSP"

# ─── Fix 7: nginx Docker override conf ───────────────────────────────────────
echo "[Fix 7] Create nginx/conf.d/prislab.docker.conf..."
DOCKER_NGINX="$TARGET/nginx/conf.d/prislab.docker.conf"
if [ ! -f "$DOCKER_NGINX" ]; then
  sed 's/server 127\.0\.0\.1:8000;/server app:8000;/g;s/ 216\.[0-9.]*//g' "$NGINX" > "$DOCKER_NGINX"
  sed -i '1i # Docker Compose override — upstream uses app:8000 (service name)\n# Mount this file instead of prislab.conf in docker-compose.yml\n' "$DOCKER_NGINX"
  echo "  ✓ Created prislab.docker.conf"
else
  echo "  ✓ Already exists"
fi

# ─── Fix 8: rotate_secrets.sh ────────────────────────────────────────────────
echo "[Fix 8] Ensure scripts/rotate_secrets.sh exists..."
if [ -f "$TARGET/scripts/rotate_secrets.sh" ]; then
  echo "  ✓ rotate_secrets.sh already present"
else
  cp "$(dirname "$0")/rotate_secrets.sh" "$TARGET/scripts/rotate_secrets.sh"
  chmod +x "$TARGET/scripts/rotate_secrets.sh"
  echo "  ✓ Copied rotate_secrets.sh"
fi

echo ""
echo "=== All fixes applied. Run validate_fixes.sh to verify. ==="
