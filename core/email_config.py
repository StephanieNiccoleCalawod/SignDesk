"""
email_config.py - Email Sending Configuration

╔══════════════════════════════════════════════════════════════╗
║  SETUP INSTRUCTIONS                                          ║
║                                                              ║
║  1. Go to https://myaccount.google.com/apppasswords          ║
║  2. Generate a new App Password for "Mail"                   ║
║  3. Copy the 16-character password                           ║
║  4. Paste it below as SMTP_APP_PASSWORD                      ║
║  5. Set SMTP_EMAIL to your Gmail address                     ║
║                                                              ║
║  NOTE: You must have 2-Step Verification enabled on your     ║
║  Google account to generate App Passwords.                   ║
╚══════════════════════════════════════════════════════════════╝
"""

# ──────────────────────────────────────────────────────────────
# GMAIL SMTP CREDENTIALS — Fill in your details below
# ──────────────────────────────────────────────────────────────

SMTP_EMAIL        = "your-email@gmail.com"         # Your Gmail address
SMTP_APP_PASSWORD = "xxxx xxxx xxxx xxxx"           # 16-char App Password from Google

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
