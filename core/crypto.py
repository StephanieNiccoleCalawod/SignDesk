"""
core/crypto.py — Encryption & Hashing Utilities for SignDesk

Strategy
--------
• Fernet (AES-128-CBC + HMAC-SHA256) for reversible field storage.
  Used for: username_enc, email_enc, translated_text_enc.
  Decrypted only when displaying data to the user.

• HMAC-SHA256 for deterministic indexed lookups.
  Replaces plaintext in the `username` and `email` DB columns so that
  WHERE clauses, UNIQUE constraints, and duplicate checks all work
  without ever touching plaintext at rest.

Key file: signdesk_secrets.json  (auto-generated on first run).
          NEVER commit this file to version control.
"""

import os
import json
import hmac
import hashlib
import base64
from cryptography.fernet import Fernet

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS_PATH = os.path.join(_BASE_DIR, "signdesk_secrets.json")


# ── Key management ─────────────────────────────────────────────────────────────

def _load_or_create_secrets() -> dict:
    """
    Load secrets from disk.  If the file is missing or corrupt, generate
    fresh keys and persist them with restricted file permissions (0o600).
    """
    if os.path.exists(SECRETS_PATH):
        try:
            with open(SECRETS_PATH, "r") as f:
                data = json.load(f)
            if "fernet_key" in data and "hmac_secret" in data:
                return data
        except Exception:
            pass

    # First run — generate cryptographically-random keys
    secrets = {
        "fernet_key": Fernet.generate_key().decode(),
        "hmac_secret": base64.b64encode(os.urandom(32)).decode(),
    }
    try:
        with open(SECRETS_PATH, "w") as f:
            json.dump(secrets, f, indent=2)
        os.chmod(SECRETS_PATH, 0o600)  # owner read/write only (no-op on Windows)
    except Exception as e:
        print(f"[crypto] Warning: could not persist secrets — {e}")

    return secrets


_secrets = _load_or_create_secrets()
_fernet = Fernet(_secrets["fernet_key"].encode())
_hmac_secret: bytes = base64.b64decode(_secrets["hmac_secret"])


# ── Public API ─────────────────────────────────────────────────────────────────

def encrypt(value: str) -> str:
    """
    Encrypt *value* with Fernet and return a URL-safe base64 ciphertext string.
    Returns "" for empty / None input (stored as-is, not as a blank token).
    """
    if not value:
        return ""
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(value: str) -> str:
    """
    Decrypt a Fernet ciphertext produced by ``encrypt()``.
    Returns the original plaintext string.

    Graceful fallback: if *value* cannot be decrypted (e.g. a legacy row
    that predates encryption), the raw value is returned unchanged so
    that the application never crashes on old data.
    """
    if not value:
        return ""
    try:
        return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except Exception:
        return value  # legacy / already-plaintext row — return as-is


def hmac_hash(value: str, *, normalize: bool = False) -> str:
    """
    Produce a deterministic HMAC-SHA256 hex digest of *value*.

    The same plaintext always maps to the same 64-character hex string,
    making it safe for:
      • UNIQUE constraints on the `username` / `email` columns
      • WHERE-clause lookups  (``WHERE username = hmac_hash(input)``)
      • Duplicate-existence checks

    Args:
        value:     Input string.
        normalize: If True, strip whitespace and lowercase before hashing.
                   Always pass ``normalize=True`` for email addresses because
                   email is case-insensitive by spec.
    """
    if not value:
        return ""
    text = value.strip().lower() if normalize else value
    return hmac.new(_hmac_secret, text.encode("utf-8"), hashlib.sha256).hexdigest()
