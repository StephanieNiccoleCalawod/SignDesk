

import bcrypt
from datetime import datetime, timedelta

from core.database import get_connection
from core.email_service import generate_otp
from core.crypto import hmac_hash
from core.audit_log import log_event


# ──────────────────────────────────────────────────────────────
# OTP EXPIRY
# ──────────────────────────────────────────────────────────────

PASSWORD_RESET_OTP_EXPIRY_MINUTES = 5


def _get_reset_otp_expiry() -> datetime:
    return datetime.now() + timedelta(minutes=PASSWORD_RESET_OTP_EXPIRY_MINUTES)


# ──────────────────────────────────────────────────────────────
# EMAIL CHECK
# ──────────────────────────────────────────────────────────────

def check_email_exists(email: str) -> tuple[bool, str]:
    """
    Checks if a user account exists for the given email.
    Lookup via HMAC hash — plaintext never reaches the DB query.
    Returns (True, "") if found, (False, "error message") if not.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM users WHERE email = ?",
                (hmac_hash(email, normalize=True),)
            )
            row = cursor.fetchone()

        if row is None:
            return False, "No account found with this email address."
        return True, ""

    except Exception as e:
        print(f"[otp] check_email_exists error: {e}")
        return False, "An unexpected error occurred. Please try again."


# ──────────────────────────────────────────────────────────────
# OTP CREATION
# ──────────────────────────────────────────────────────────────

def create_otp(email: str) -> str:
    """
    Generates a secure 6-digit OTP, invalidates any previous tokens
    for this email, and inserts a new token into otp_tokens.
    The email is stored as its HMAC hash.
    Returns the OTP code string.
    """
    otp_code   = generate_otp()
    expiry     = _get_reset_otp_expiry()
    email_hash = hmac_hash(email, normalize=True)

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE otp_tokens SET is_used = 1 WHERE email = ? AND is_used = 0",
            (email_hash,)
        )

        cursor.execute(
            "INSERT INTO otp_tokens (email, otp_code, expires_at, is_used) "
            "VALUES (?, ?, ?, 0)",
            (email_hash, otp_code, expiry)
        )

    return otp_code


# ──────────────────────────────────────────────────────────────
# OTP VERIFICATION
# ──────────────────────────────────────────────────────────────

def verify_otp(email: str, code: str) -> tuple[bool, str]:
    """
    Verifies the OTP code against the most recent unused, unexpired token.
    Returns (True, "Verified") on success, (False, "reason") on failure.
    Does NOT mark the token as used — that happens in update_password().
    """
    try:
        email_hash = hmac_hash(email, normalize=True)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, otp_code, expires_at
                  FROM otp_tokens
                 WHERE email = ? AND is_used = 0
                 ORDER BY id DESC
                 LIMIT 1
                """,
                (email_hash,)
            )
            row = cursor.fetchone()

        if row is None:
            return False, "No active verification code found. Please request a new one."

        token_id, stored_code, expires_at = row

        if datetime.now() > expires_at:
            return False, "Verification code has expired. Please request a new one."

        if stored_code != code:
            log_event("OTP_VERIFY_FAILED", email_hash, "Incorrect code")
            return False, "Incorrect verification code."

        log_event("OTP_VERIFY_SUCCESS", email_hash)
        return True, "Verified"

    except Exception as e:
        print(f"[otp] verify_otp error: {e}")
        log_event("OTP_VERIFY_FAILED", hmac_hash(email, normalize=True), "Internal error")
        return False, "An unexpected error occurred. Please try again."


# ──────────────────────────────────────────────────────────────
# OTP INVALIDATION
# ──────────────────────────────────────────────────────────────

def invalidate_otp(email: str):
    """Marks all OTP tokens for this email as used."""
    try:
        email_hash = hmac_hash(email, normalize=True)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE otp_tokens SET is_used = 1 WHERE email = ?",
                (email_hash,)
            )
    except Exception as e:
        print(f"OTP invalidation error: {e}")


# ──────────────────────────────────────────────────────────────
# PASSWORD UPDATE
# ──────────────────────────────────────────────────────────────

def update_password(email: str, new_password: str) -> tuple[bool, str]:
    """
    Hashes the new password with bcrypt, updates users.password_hash,
    and invalidates all OTP tokens for this email.
    Returns (True, "success") or (False, "error message").
    """
    try:
        email_hash = hmac_hash(email, normalize=True)

        password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE users SET password_hash = ?, email_verified = 1 WHERE email = ?",
                (password_hash, email_hash)
            )

            if cursor.rowcount == 0:
                return False, "Account not found."

            cursor.execute(
                "SELECT password_hash FROM users WHERE email = ?", (email_hash,)
            )
            verify_row = cursor.fetchone()
            if verify_row is None or verify_row[0] != password_hash:
                return False, "Password update failed — verification read mismatch."

        invalidate_otp(email)
        log_event("PASSWORD_RESET_SUCCESS", email_hash, "Password reset via OTP")
        return True, "Password updated successfully."

    except Exception as e:
        print(f"[otp] update_password error: {e}")
        log_event("PASSWORD_RESET_FAILED", hmac_hash(email, normalize=True), "Internal error")
        return False, "An unexpected error occurred. Please try again."
