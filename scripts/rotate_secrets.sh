#!/usr/bin/env bash
# =============================================================================
# PRISLAB — Secret Rotation Script
# Usage: bash scripts/rotate_secrets.sh
# Requires: Python 3.12+ with cryptography package installed
# =============================================================================
set -euo pipefail

echo ""
echo "============================================================"
echo "  PRISLAB Secret Rotation — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "============================================================"
echo ""
echo "# Copy the values below into your .env / secret manager."
echo "# NEVER commit these values to git."
echo ""

# ── SECRET_KEY (Django) ───────────────────────────────────────────────────────
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
echo "SECRET_KEY=${SECRET_KEY}"

# ── FERNET_KEY ────────────────────────────────────────────────────────────────
FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "FERNET_KEY=${FERNET_KEY}"

# ── API Tokens (URL-safe base64, 64 chars = 48 random bytes) ─────────────────
gen_token() {
  python -c "import secrets; print(secrets.token_urlsafe(48))"
}

echo "PRISLAB_API_TOKEN=$(gen_token)"
echo "PRISLAB_FRONTEND_LOG_TOKEN=$(gen_token)"
echo "PRISLAB_KIOSCO_API_TOKEN=$(gen_token)"
echo "CRON_SECRET=$(gen_token)"
echo "PRISCI_WEBHOOK_TOKEN=$(gen_token)"
echo "PRISCI_WEBHOOK_VERIFY_TOKEN=$(gen_token)"
echo "HL7_API_KEY=$(gen_token)"

# ── VAPID Keys (Push Notifications) ──────────────────────────────────────────
echo ""
echo "# VAPID keys — run separately if py-vapid is installed:"
echo "# vapid --gen --applicationServerKey"
echo ""
echo "============================================================"
echo "  IMPORTANT: Rotate these values in ALL environments:"
echo "  1. Update your .env file (local dev)"
echo "  2. Update Cloud Run / Kubernetes secrets"
echo "  3. Update CI/CD secret variables"
echo "  4. Restart all services after rotation"
echo "============================================================"
