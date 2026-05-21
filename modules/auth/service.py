"""
service.py - Authentication Logic
Handles user login and registration with SQLite and bcrypt.
Includes email verification support for account creation.

Encryption layer (v2)
---------------------
• All DB lookups on username/email use hmac_hash() — never plaintext.
• New rows store hmac_hash in the indexed column + Fernet ciphertext in _enc column.
• Passwords continue to use bcrypt (unchanged).
"""

import bcrypt
from core.database import get_connection
from core.crypto import encrypt, hmac_hash
from core.audit_log import log_event
from core.validators import (
    validate_email,
    validate_username,
    validate_password,
    validate_registration,
    sanitize_input,
    sanitize_username,
    registration_limiter,
)


# ──────────────────────────────────────────────────────────────
# DUPLICATE CHECKS
# ──────────────────────────────────────────────────────────────

def check_duplicate_username(username: str) -> tuple[bool, str]:
    """
    Returns (True, "error") if username already exists.
    Returns (False, "") if username is available.
    Lookup is performed via HMAC hash — no plaintext stored in WHERE clause.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (hmac_hash(username),)
            )
            exists = cursor.fetchone() is not None

        if exists:
            return True, "This username already exists. Please choose another username."
        return False, ""

    except Exception as e:
        print(f"[auth] check_duplicate_username error: {e}")
        return True, "An unexpected error occurred. Please try again."


def check_duplicate_email(email: str) -> tuple[bool, str]:
    """
    Returns (True, "error") if email already exists.
    Returns (False, "") if email is available.
    Lookup uses HMAC hash with normalization (email is case-insensitive).
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM users WHERE email = ?",
                (hmac_hash(email, normalize=True),)
            )
            exists = cursor.fetchone() is not None

        if exists:
            return True, "An account with this email already exists."
        return False, ""

    except Exception as e:
        print(f"[auth] check_duplicate_email error: {e}")
        return True, "An unexpected error occurred. Please try again."


# ──────────────────────────────────────────────────────────────
# AUTH FUNCTIONS
# ──────────────────────────────────────────────────────────────

def login_user(username: str, password: str) -> tuple[bool, str]:
    """
    Validates user credentials against the database.
    Returns (True, "Login successful") or (False, "error message").
    Username lookup via HMAC hash — plaintext never touches the DB query.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT password_hash, email_verified
                FROM   users
                WHERE  username = ?
                """,
                (hmac_hash(username),)
            )

            row = cursor.fetchone()

        if row is None:
            log_event("LOGIN_FAILED", username, "User not found")
            return False, "Incorrect username or password. Please try again."

        stored_hash    = row[0].encode("utf-8")
        email_verified = row[1]

        if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            log_event("LOGIN_FAILED", username, "Incorrect password")
            return False, "Incorrect username or password. Please try again."

        if email_verified == False:
            log_event("LOGIN_FAILED", username, "Email not verified")
            return False, "Please verify your email address to log in."

        log_event("LOGIN_SUCCESS", username)
        return True, "Login successful."

    except Exception as e:
        print(f"[auth] login_user error: {e}")
        log_event("LOGIN_FAILED", username, "Internal error")
        return False, "An unexpected error occurred. Please try again."


def register_user(username: str, email: str, password: str) -> tuple[bool, str, str]:
    """
    Legacy: Creates a new user account as unverified.
    NOTE: Use the in-memory OTP flow + create_verified_user() instead.
    Kept for backwards compatibility only.
    """
    import random
    import string
    from datetime import datetime
    from core.email_service import get_otp_expiry
    try:
        username_hash = hmac_hash(username)
        email_hash    = hmac_hash(email, normalize=True)

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM users WHERE username = ?", (username_hash,))
            if cursor.fetchone():
                return False, "This username already exists.", ""

            cursor.execute("SELECT 1 FROM users WHERE email = ?", (email_hash,))
            if cursor.fetchone():
                return False, "An account with this email already exists.", ""

            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")

            verification_code = ''.join(random.choices(string.digits, k=6))
            expiry_time = get_otp_expiry()

            cursor.execute(
                """
                INSERT INTO users
                    (username, email, username_enc, email_enc,
                     name, password_hash, email_verified, verification_code, verification_expiry)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    username_hash,
                    email_hash,
                    encrypt(username),
                    encrypt(email),
                    username,           # seed display name from plaintext
                    password_hash,
                    verification_code,
                    expiry_time,
                )
            )

        return True, "Account created tentatively.", verification_code

    except Exception as e:
        print(f"[auth] register_user error: {e}")
        return False, "An unexpected error occurred. Please try again.", ""


def create_verified_user(username: str, email: str, password: str) -> tuple[bool, str]:
    """
    Creates a fully verified user account.
    Called ONLY after OTP verification succeeds (in-memory check).
    Returns: (Success, Message)
    """
    try:
        username_hash = hmac_hash(username)
        email_hash    = hmac_hash(email, normalize=True)

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM users WHERE username = ?", (username_hash,))
            if cursor.fetchone():
                return False, "This username already exists. Please go back and choose another."

            cursor.execute("SELECT 1 FROM users WHERE email = ?", (email_hash,))
            if cursor.fetchone():
                return False, "An account with this email already exists."

            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")

            cursor.execute(
                """
                INSERT INTO users
                    (username, email, username_enc, email_enc,
                     name, password_hash, email_verified)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    username_hash,
                    email_hash,
                    encrypt(username),
                    encrypt(email),
                    username,           # seed display name
                    password_hash,
                )
            )

        log_event("REGISTER_SUCCESS", username, "Account created (verified)")
        return True, "Account created successfully."

    except Exception as e:
        print(f"[auth] create_verified_user error: {e}")
        log_event("REGISTER_FAILED", username, "Internal error")
        return False, "An unexpected error occurred. Please try again."


def verify_user(email: str, entered_code: str) -> tuple[bool, str]:
    """
    Verifies the user's email against the database OTP.
    Email lookup via HMAC hash.
    """
    from datetime import datetime
    try:
        email_hash = hmac_hash(email, normalize=True)

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT verification_code, verification_expiry, email_verified "
                "FROM users WHERE email = ?",
                (email_hash,)
            )
            row = cursor.fetchone()

            if not row:
                return False, "Account error: User not found."

            stored_code, expiry, verified = row

            if verified == True:
                return False, "Account is already verified."

            if stored_code != entered_code:
                log_event("EMAIL_VERIFY_FAILED", email, "Incorrect code")
                return False, "Incorrect verification code."

            if expiry and datetime.now() > expiry:
                log_event("EMAIL_VERIFY_FAILED", email, "Code expired")
                return False, "Verification code has expired."

            cursor.execute(
                "UPDATE users SET email_verified = 1, "
                "verification_code = NULL, verification_expiry = NULL "
                "WHERE email = ?",
                (email_hash,)
            )

        log_event("EMAIL_VERIFY_SUCCESS", email)
        return True, "Email verified successfully."
    except Exception as e:
        print(f"[auth] verify_user error: {e}")
        log_event("EMAIL_VERIFY_FAILED", email, "Internal error")
        return False, "An unexpected error occurred. Please try again."


def resend_verification_code(email: str) -> tuple[bool, str, str]:
    """
    Generates a new code, updates DB, and returns it.
    Returns: (Success, Message, NewCode)
    """
    import random
    import string
    from core.email_service import get_otp_expiry
    try:
        email_hash = hmac_hash(email, normalize=True)

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT email_verified FROM users WHERE email = ?",
                (email_hash,)
            )
            row = cursor.fetchone()
            if not row:
                return False, "Account error: User not found.", ""

            if row[0] == True:
                return False, "Email is already verified.", ""

            new_code = ''.join(random.choices(string.digits, k=6))
            expiry   = get_otp_expiry()

            cursor.execute(
                "UPDATE users SET verification_code = ?, verification_expiry = ? "
                "WHERE email = ?",
                (new_code, expiry, email_hash)
            )

        return True, "New code generated.", new_code
    except Exception as e:
        print(f"[auth] resend_verification_code error: {e}")
        return False, "An unexpected error occurred. Please try again.", ""
