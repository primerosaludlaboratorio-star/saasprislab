#!/usr/bin/env bash
# =============================================================================
# PRISLAB SaaS — Secret Rotation Script
# Usage: bash audit_fixes/rotate_secrets.sh
# Requirements: Python 3.12+ with 'cryptography' package
# =============================================================================
set -euo pipefail

echo ""
echo "============================================================"
echo "  PRISLAB Secret Rotation — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "============================================================"
echo ""
echo "# ─── Paste the following into your .env / secret manager ───"
echo "# NEVER commit these values to git."
echo ""

# ── SECRET_KEY (Django) ───────────────────────────────────────────────────────
SECRET_KEY=$(python3 -c "
import django.conf
import django.utils.crypto
# Generate without needing a full Django setup
import secrets, string
chars = string.ascii_letters + string.digits + '!@#\$%^&*(-_=+)'
print(''.join(secrets.choice(chars) for _ in range(64)))
")
echo "SECRET_KEY=${SECRET_KEY}"

# ── FERNET_KEY ────────────────────────────────────────────────────────────────
FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "FERNET_KEY=${FERNET_KEY}"

# ── Token generator: URL-safe base64, 48 random bytes → 64 chars ─────────────
gen_token() {
  python3 -c "import secrets; print(secrets.token_urlsafe(48))"
}

echo "PRISLAB_API_TOKEN=$(gen_token)"
echo "PRISLAB_FRONTEND_LOG_TOKEN=$(gen_token)"
echo "PRISLAB_KIOSCO_API_TOKEN=$(gen_token)"
echo "CRON_SECRET=$(gen_token)"
echo "PRISCI_WEBHOOK_TOKEN=$(gen_token)"
echo "PRISCI_WEBHOOK_VERIFY_TOKEN=$(gen_token)"
echo "HL7_API_KEY=$(gen_token)"

# ── VAPID Keys (Web Push Notifications) ───────────────────────────────────────
echo ""
echo "# VAPID keys — regenerate with py-vapid if installed:"
echo "# pip install py-vapid && vapid --gen --applicationServerKey"
echo "# Then update VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY in .env"
echo ""

echo "# ─────────────────────────────────────────────────────────────"
echo "# ACTION REQUIRED after generating new secrets:"
echo "#  1. Update .env (local development)"
echo "#  2. Update Cloud Run secrets / Kubernetes secrets"
echo "#  3. Update GitHub Actions / CI secrets"
echo "#  4. Restart ALL services (web, celery worker, celery beat)"
echo "#  5. For FERNET_KEY rotation: run a one-time re-encryption task"
echo "#     if encrypted data exists in the database."
echo "# ─────────────────────────────────────────────────────────────"
