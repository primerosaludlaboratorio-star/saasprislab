#!/usr/bin/env bash
# =============================================================================
# PRISLAB SaaS — Post-Fix Validation Script
# Usage: bash audit_fixes/validate_fixes.sh /path/to/PRISLAB_SaaS-master
# =============================================================================
set -euo pipefail

TARGET="${1:-$(pwd)}"
PASS=0
FAIL=0

check() {
  local desc="$1"; local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    echo "  ✓ PASS: $desc"
    PASS=$((PASS+1))
  else
    echo "  ✗ FAIL: $desc"
    FAIL=$((FAIL+1))
  fi
}

echo ""
echo "=== PRISLAB Audit Validation ==="
echo "Target: $TARGET"
echo ""

# ─── Fix 1: Dockerfile ───────────────────────────────────────────────────────
echo "[Fix 1] Dockerfile entrypoint"
check "No cloudrun_web_entrypoint.sh reference" \
  "! grep -q 'cloudrun_web_entrypoint' '$TARGET/Dockerfile'"
check "web_entrypoint.sh in RUN sed" \
  "grep -q 'web_entrypoint.sh' '$TARGET/Dockerfile'"
check "CMD uses web_entrypoint.sh" \
  "grep -q 'CMD.*web_entrypoint.sh' '$TARGET/Dockerfile'"

# ─── Fix 2: requirements.txt ─────────────────────────────────────────────────
echo "[Fix 2] requirements.txt"
check "Only one numpy entry" \
  "[ \$(grep -c '^numpy>=' '$TARGET/requirements.txt') -eq 1 ]"
check "Keeps numpy>=1.26.4" \
  "grep -q 'numpy>=1.26.4' '$TARGET/requirements.txt'"

# ─── Fix 3: CI workflow ──────────────────────────────────────────────────────
echo "[Fix 3] GitHub Actions CI"
check "Python 3.12 in CI" \
  "grep -q 'python-version: \"3.12\"' '$TARGET/.github/workflows/main.yml'"
check "No python 3.11 in CI" \
  "! grep -q 'python-version: \"3.11\"' '$TARGET/.github/workflows/main.yml'"
check "Migration check step in CI" \
  "grep -q 'migrate --check' '$TARGET/.github/workflows/main.yml'"

# ─── Fix 4: database.py ──────────────────────────────────────────────────────
echo "[Fix 4] database.py connection age"
check "No '0 if IS_PRODUCTION' pattern" \
  "! grep -q '0 if IS_PRODUCTION else 60' '$TARGET/config/settings/database.py'"
check "DB_CONN_MAX_AGE default is 60" \
  "grep -q \"_env_int('DB_CONN_MAX_AGE', 60)\" '$TARGET/config/settings/database.py'"

# ─── Fix 5: cache.py ─────────────────────────────────────────────────────────
echo "[Fix 5] cache.py session engine"
check "Redis cache session engine present" \
  "grep -q 'backends.cache' '$TARGET/config/settings/cache.py'"
check "SESSION_CACHE_ALIAS set" \
  "grep -q 'SESSION_CACHE_ALIAS' '$TARGET/config/settings/cache.py'"
check "DB fallback session engine present" \
  "grep -q 'backends.db' '$TARGET/config/settings/cache.py'"

# ─── Fix 6: nginx conf ───────────────────────────────────────────────────────
echo "[Fix 6] nginx/conf.d/prislab.conf"
check "X-Forwarded-For uses proxy_add" \
  "grep -q 'proxy_add_x_forwarded_for' '$TARGET/nginx/conf.d/prislab.conf'"
check "No remote_addr in X-Forwarded-For" \
  "! grep -q 'X-Forwarded-For \\\$remote_addr' '$TARGET/nginx/conf.d/prislab.conf'"
check "HSTS max-age=31536000" \
  "grep -q 'max-age=31536000' '$TARGET/nginx/conf.d/prislab.conf'"
check "No HSTS max-age=63072000" \
  "! grep -q 'max-age=63072000' '$TARGET/nginx/conf.d/prislab.conf'"
check "Content-Security-Policy header" \
  "grep -q 'Content-Security-Policy' '$TARGET/nginx/conf.d/prislab.conf'"

# ─── Fix 7: nginx Docker conf ────────────────────────────────────────────────
echo "[Fix 7] nginx/conf.d/prislab.docker.conf"
check "prislab.docker.conf exists" \
  "[ -f '$TARGET/nginx/conf.d/prislab.docker.conf' ]"
check "Docker conf uses app:8000" \
  "grep -q 'server app:8000' '$TARGET/nginx/conf.d/prislab.docker.conf'"
check "Docker conf has no 127.0.0.1:8000" \
  "! grep -q '127.0.0.1:8000' '$TARGET/nginx/conf.d/prislab.docker.conf'"

# ─── Fix 8: rotate_secrets.sh ────────────────────────────────────────────────
echo "[Fix 8] scripts/rotate_secrets.sh"
check "rotate_secrets.sh exists" \
  "[ -f '$TARGET/scripts/rotate_secrets.sh' ]"

echo ""
echo "══════════════════════════════════════"
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "══════════════════════════════════════"
[ "$FAIL" -eq 0 ] && echo "  ALL CHECKS PASSED ✓" || echo "  SOME CHECKS FAILED — review output above"
echo ""
exit "$FAIL"
