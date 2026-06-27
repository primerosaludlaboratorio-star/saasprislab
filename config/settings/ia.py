"""
config/settings/ia.py

Claves y parámetros de proveedores de IA, CFDI/Facturama y VAPID.
Depende de: base.py (IS_PRODUCTION, IS_SANDBOX, DEBUG ya definidos)
"""
import os

# ── Google / Gemini ───────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "").strip().replace('\r', '').replace('\n', '')
GOOGLE_GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "").strip().replace('\r', '').replace('\n', '')
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().replace('\r', '').replace('\n', '')
AI_PROVIDER = os.environ.get("AI_PROVIDER", "").strip().lower()

# Canonicalización: una sola clave puede alimentar Gemini.
# Orden de preferencia: GOOGLE_API_KEY -> GOOGLE_GEMINI_API_KEY -> GEMINI_API_KEY
if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = GOOGLE_GEMINI_API_KEY or GEMINI_API_KEY
if not GOOGLE_GEMINI_API_KEY:
    GOOGLE_GEMINI_API_KEY = GOOGLE_API_KEY
if not GEMINI_API_KEY:
    GEMINI_API_KEY = GOOGLE_API_KEY

# ── DeepSeek ──────────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip().replace('\r', '').replace('\n', '')
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()
DEEPSEEK_API_URL = os.environ.get(
    "DEEPSEEK_API_URL",
    "https://api.deepseek.com/v1/chat/completions",
).strip()

# ── PRISCI Webhooks ───────────────────────────────────────────────────────────
PRISCI_WEBHOOK_TOKEN = os.environ.get("PRISCI_WEBHOOK_TOKEN", "").strip()
PRISCI_WEBHOOK_VERIFY_TOKEN = os.environ.get("PRISCI_WEBHOOK_VERIFY_TOKEN", "").strip()

# ── PRIS Sentinel → GitHub Auto-Reporte ──────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # formato: owner/repo

# ── CFDI 4.0 — Facturama ─────────────────────────────────────────────────────
FACTURAMA_USER = os.environ.get('FACTURAMA_USER', '')
FACTURAMA_PASSWORD = os.environ.get('FACTURAMA_PASSWORD', '')
FACTURAMA_SANDBOX = os.environ.get('FACTURAMA_SANDBOX', 'True') == 'True'

# ── VAPID — Web Push Notifications ───────────────────────────────────────────
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_CLAIMS = {
    'sub': 'mailto:admin@prislab.com'
}
