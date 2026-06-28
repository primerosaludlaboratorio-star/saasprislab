#!/usr/bin/env bash
# =============================================================================
# PRISLAB — Post-Fix Validation Suite (21 checks)
# Usage: bash audit_fixes/validate_fixes.sh /path/to/prislab/repo
# =============================================================================
set -euo pipefail

REPO="${1:-$(pwd)}"
PASS=0; FAIL=0

check() {
  local desc="$1"; local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    echo "  ✅ $desc"
    PASS=$((PASS+1))
  else
    echo "  ❌ FAIL: $desc"
    FAIL=$((FAIL+1))
  fi
}

echo ""
echo "============================================================"
echo "  PRISLAB Validate Fixes — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "  Repo: $REPO"
echo "============================================================"
echo ""

# --- P0-1: Dockerfile entrypoint ---
echo "[P0-1] Dockerfile entrypoint"
check "Dockerfile uses web_entrypoint.sh (not cloudrun)" \
  "grep -q 'web_entrypoint.sh' '$REPO/Dockerfile'"
check "Dockerfile does NOT reference cloudrun_web_entrypoint" \
  "! grep -q 'cloudrun_web_entrypoint' '$REPO/Dockerfile'"

# --- P0-2: Nginx Docker conf ---
echo "[P0-2] Nginx Docker Compose conf"
check "prislab.docker.conf exists" \
  "test -f '$REPO/nginx/conf.d/prislab.docker.conf'"
check "prislab.docker.conf uses app:8000" \
  "grep -q 'server app:8000' '$REPO/nginx/conf.d/prislab.docker.conf'"
check "prislab.docker.conf has NO hardcoded IP" \
  "! grep -q '216.238.89.243' '$REPO/nginx/conf.d/prislab.docker.conf'"

# --- P1-2: CI Python version ---
echo "[P1-2] CI Python version"
check "CI uses Python 3.12" \
  "grep -q 'python-version: \"3.12\"' '$REPO/.github/workflows/main.yml'"
check "CI has migration check step" \
  "grep -q 'migrate --check' '$REPO/.github/workflows/main.yml'"

# --- P1-3: Redis sessions ---
echo "[P1-3] Redis sessions"
check "cache.py uses cache session backend when Redis present" \
  "grep -q 'backends.cache' '$REPO/config/settings/cache.py'"
check "cache.py SESSION_CACHE_ALIAS defined" \
  "grep -q 'SESSION_CACHE_ALIAS' '$REPO/config/settings/cache.py'"

# --- P1-4: DB connection pooling ---
echo "[P1-4] DB connection pooling"
check "database.py DB_CONN_MAX_AGE default is 60" \
  "grep -q \"_env_int('DB_CONN_MAX_AGE', 60)\" '$REPO/config/settings/database.py'"

# --- P1-5: nginx X-Forwarded-For ---
echo "[P1-5] nginx X-Forwarded-For"
check "prislab.conf uses proxy_add_x_forwarded_for" \
  "grep -q 'proxy_add_x_forwarded_for' '$REPO/nginx/conf.d/prislab.conf'"
check "docker conf uses proxy_add_x_forwarded_for" \
  "grep -q 'proxy_add_x_forwarded_for' '$REPO/nginx/conf.d/prislab.docker.conf'"

# --- P1-6: CSP header ---
echo "[P1-6] Content-Security-Policy"
check "prislab.conf has CSP header" \
  "grep -q 'Content-Security-Policy' '$REPO/nginx/conf.d/prislab.conf'"
check "docker conf has CSP header" \
  "grep -q 'Content-Security-Policy' '$REPO/nginx/conf.d/prislab.docker.conf'"

# --- P1-7: HSTS consistency ---
echo "[P1-7] HSTS"
check "prislab.conf HSTS is 31536000 (1 year)" \
  "grep -q 'max-age=31536000' '$REPO/nginx/conf.d/prislab.conf'"
check "prislab.conf does NOT have 63072000 (2 years)" \
  "! grep -q 'max-age=63072000' '$REPO/nginx/conf.d/prislab.conf'"

# --- P1-9: numpy dedup ---
echo "[P1-9] requirements.txt numpy"
check "requirements.txt has only one numpy entry" \
  "test \$(grep -c '^numpy' '$REPO/requirements.txt') -eq 1"

# --- Secrets rotation script ---
echo "[Tools] Secrets rotation"
check "rotate_secrets.sh exists" \
  "test -f '$REPO/scripts/rotate_secrets.sh'"
check "rotate_secrets.sh is executable or at least has content" \
  "test -s '$REPO/scripts/rotate_secrets.sh'"

echo ""
echo "============================================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "============================================================"
echo ""

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
