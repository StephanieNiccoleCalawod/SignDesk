"""
otp_manager.py - Password Reset OTP Lifecycle Manager
Handles OTP generation, storage, verification, invalidation, and password update
for the Forgot Password flow. Uses the otp_tokens table in SQLite.
"""

import bcrypt
from datetime import datetime, timedelta

from core.database import get_connection
from core.email_service import generate_otp


# ──────────────────────────────────────────────────────────────
# PASSWORD RESET OTP EXPIRY (10 minutes, independent of registration)
# ──────────────────────────────────────────────────────────────

PASSWORD_RESET_OTP_EXPIRY_MINUTES = 10


def _get_reset_otp_expiry() -> datetime:
    """Returns the expiry timestamp for a password-reset OTP (10 minutes)."""
    return datetime.now() + timedelta(minutes=PASSWORD_RESET_OTP_EXPIRY_MINUTES)


# ──────────────────────────────────────────────────────────────
# EMAIL CHECK
# ──────────────────────────────────────────────────────────────

def check_email_exists(email: str) -> tuple[bool, str]:
    """
    Checks if a user account exists for the given email.
    Does NOT require email_verified — the password reset OTP itself
    proves email ownership, so unverified accounts can reset too.
    Returns (True, "") if found, (False, "error message") if not.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM users WHERE email = ?", (email,)
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return False, "No account found with this email address."

        return True, ""

    except Exception as e:
        return False, f"Database error: {str(e)}"


# ──────────────────────────────────────────────────────────────
# OTP CREATION
# ──────────────────────────────────────────────────────────────

def create_otp(email: str) -> str:
    """
    Generates a secure 6-digit OTP, invalidates any previous tokens
    for this email, and inserts a new token into otp_tokens.
    Returns the OTP code string.
    """
    otp_code = generate_otp()
    expiry = _get_reset_otp_expiry()

    conn = get_connection()
    cursor = conn.cursor()

    # Invalidate all previous unused tokens for this email
    cursor.execute(
        "UPDATE otp_tokens SET is_used = 1 WHERE email = ? AND is_used = 0",
        (email,)
    )

    # Insert new token
    cursor.execute(
        "INSERT INTO otp_tokens (email, otp_code, expires_at, is_used) VALUES (?, ?, ?, 0)",
        (email, otp_code, expiry)
    )

    conn.commit()
    conn.close()

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
        conn = get_connection()
        cursor = conn.cursor()

        # Get the most recent unused token for this email
        cursor.execute(
            """
            SELECT id, otp_code, expires_at
            FROM   otp_tokens
            WHERE  email = ? AND is_used = 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (email,)
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return False, "No active verification code found. Please request a new one."

        token_id, stored_code, expires_at = row

        # Check expiry
        if datetime.now() > expires_at:
            return False, "Verification code has expired. Please request a new one."

        # Check code match
        if stored_code != code:
            return False, "Incorrect verification code."

        return True, "Verified"

    except Exception as e:
        return False, f"Database error: {str(e)}"


# ──────────────────────────────────────────────────────────────
# OTP INVALIDATION
# ──────────────────────────────────────────────────────────────

def invalidate_otp(email: str):
    """Marks all OTP tokens for this email as used."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE otp_tokens SET is_used = 1 WHERE email = ?",
            (email,)
        )
        conn.commit()
        conn.close()
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
    conn = None
    try:
        # Hash the new password
        password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        conn = get_connection()
        cursor = conn.cursor()

        # Update the password and auto-verify email (receiving OTP proves ownership)
        cursor.execute(
            "UPDATE users SET password_hash = ?, email_verified = 1 WHERE email = ?",
            (password_hash, email)
        )

        if cursor.rowcount == 0:
            return False, "Account not found."

        conn.commit()

        # Verify the write persisted (read back the hash)
        cursor.execute(
            "SELECT password_hash FROM users WHERE email = ?", (email,)
        )
        verify_row = cursor.fetchone()
        if verify_row is None or verify_row[0] != password_hash:
            return False, "Password update failed — verification read mismatch."

        conn.close()
        conn = None

        # Invalidate all OTP tokens for this email
        invalidate_otp(email)

        return True, "Password updated successfully."

    except Exception as e:
        return False, f"Database error: {str(e)}"

    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
