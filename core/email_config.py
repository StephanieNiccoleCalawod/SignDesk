"""
email_config.py - Email Sending Configuration

SMTP credentials are loaded from signdesk_secrets.json at runtime.
This avoids hardcoding sensitive passwords in source code.

╔══════════════════════════════════════════════════════════════╗
║  SETUP INSTRUCTIONS                                          ║
║                                                              ║
║  1. Go to https://myaccount.google.com/apppasswords          ║
║  2. Generate a new App Password for "Mail"                   ║
║  3. Copy the 16-character password                           ║
║  4. Open signdesk_secrets.json and set:                      ║
║       "smtp_email": "your_email@gmail.com"                   ║
║       "smtp_app_password": "xxxx xxxx xxxx xxxx"             ║
║                                                              ║
║  NOTE: You must have 2-Step Verification enabled on your     ║
║  Google account to generate App Passwords.                   ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json

# ──────────────────────────────────────────────────────────────
# LOAD SMTP CREDENTIALS FROM SECRETS FILE
# ──────────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SECRETS_PATH = os.path.join(_BASE_DIR, "signdesk_secrets.json")


def _load_smtp_from_secrets() -> dict:
    """
    Load SMTP credentials from signdesk_secrets.json.
    Returns a dict with smtp_email and smtp_app_password keys.
    """
    try:
        if os.path.exists(_SECRETS_PATH):
            with open(_SECRETS_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


_secrets = _load_smtp_from_secrets()

SMTP_EMAIL        = _secrets.get("smtp_email", "")
SMTP_APP_PASSWORD = _secrets.get("smtp_app_password", "")

# ──────────────────────────────────────────────────────────────
# SMTP SERVER SETTINGS (Gmail defaults — no need to change)
# ──────────────────────────────────────────────────────────────

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# ──────────────────────────────────────────────────────────────
# OTP SETTINGS
# ──────────────────────────────────────────────────────────────

OTP_LENGTH          = 6         # Number of digits in the verification code
OTP_EXPIRY_MINUTES  = 5         # How long the code is valid (minutes)
OTP_RESEND_COOLDOWN = 60        # Seconds between resend attempts
OTP_MAX_RESENDS     = 5         # Maximum number of resend attempts
OTP_MAX_VERIFY_ATTEMPTS = 5     # Max wrong OTP entries before lockout
