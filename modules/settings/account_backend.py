"""
SignDesk — Account Settings Backend
Adapted to work with the existing project database (core/database.py).
Auth: bcrypt hashed passwords (same as existing auth system).

Encryption layer (v2)
---------------------
• get_user / get_user_by_username  decrypt username_enc / email_enc for display.
• update_email                     writes new HMAC hash + new Fernet ciphertext.
• All WHERE lookups on username/email use hmac_hash() — never plaintext.
"""

import bcrypt
import re
from core.database import get_connection
from core.crypto import encrypt, decrypt, hmac_hash
from core.audit_log import log_event


# ── Schema migration ─────────────────────────────────────────────────────────

def init_account_db():
    """
    Ensure the users table has all required columns.
    The main encryption migration lives in core/database.update_database_schema();
    this function is kept for legacy callers and just triggers that pipeline.
    Safe to call on every startup.
    """
    try:
        from core.database import update_database_schema
        update_database_schema()
    except Exception as e:
        print(f"[account_backend] migration warning: {e}")


# ── Validation helpers ───────────────────────────────────────────────────────

def validate_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email.strip()))


def validate_password(password: str) -> tuple:
    """Returns (is_valid, error_message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    return True, ""


# ── Auth helpers ─────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Internal: decrypt a raw DB row into a clean dict ─────────────────────────

def _decrypt_user_row(row) -> dict:
    """
    Convert a sqlite3.Row from the users table into a plain dict,
    decrypting username_enc and email_enc for display.
    Falls back gracefully if the _enc columns are absent (pre-migration).
    """
    d = dict(row)

    # Decrypt username
    enc_user = d.get("username_enc", "") or ""
    d["username"] = decrypt(enc_user) if enc_user else d.get("username", "")

    # Decrypt email
    enc_email = d.get("email_enc", "") or ""
    d["email"] = decrypt(enc_email) if enc_email else d.get("email", "")

    # Fallback display name
    if not d.get("name"):
        d["name"] = d["username"]

    # Remove raw ciphertext fields — callers only need the decrypted values
    d.pop("username_enc", None)
    d.pop("email_enc", None)

    return d


# ── User lookup ──────────────────────────────────────────────────────────────

def get_user(user_id: int) -> dict | None:
    """Fetch user by ID and return decrypted fields."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, username_enc, name, email, email_enc "
            "FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    return _decrypt_user_row(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    """
    Fetch user by username (used after the existing login flow).
    Lookup via HMAC hash; returns decrypted display fields.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, username_enc, name, email, email_enc "
            "FROM users WHERE username = ?",
            (hmac_hash(username),),
        ).fetchone()

    return _decrypt_user_row(row) if row else None


# ── Account CRUD ─────────────────────────────────────────────────────────────

def update_display_name(user_id: int, new_name: str) -> tuple:
    """
    Update the user's display name.
    Display name is stored as plaintext (not sensitive — it's what the user
    chooses to show publicly inside the app).
    Returns (success, message).
    """
    new_name = new_name.strip()
    if not new_name:
        return False, "Display name cannot be empty."

    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET name = ? WHERE id = ?",
            (new_name, user_id),
        )
    return True, "Display name updated."


def update_email(user_id: int, new_email: str, current_password: str) -> tuple:
    """
    Update the user's email address.
    Requires current password for verification.
    Writes both HMAC hash (for lookup) and Fernet ciphertext (for display).
    Returns (success, message).
    """
    new_email = new_email.strip().lower()

    if not validate_email(new_email):
        return False, "Please enter a valid email address."

    new_email_hash = hmac_hash(new_email, normalize=True)
    new_email_enc  = encrypt(new_email)

    with get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash, email_enc FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if not row:
            return False, "User not found."
        if not verify_password(current_password, row["password_hash"]):
            log_event("EMAIL_CHANGE_FAILED", str(user_id), "Incorrect password")
            return False, "Incorrect password."

        # Decrypt the current stored email to compare
        current_email = decrypt(row["email_enc"] or "")
        if new_email == current_email.strip().lower():
            return False, "This is already your current email."

        # Check the new hash isn't already taken by another account
        exists = conn.execute(
            "SELECT id FROM users WHERE email = ? AND id != ?",
            (new_email_hash, user_id),
        ).fetchone()
        if exists:
            return False, "That email is already in use."

        conn.execute(
            "UPDATE users SET email = ?, email_enc = ? WHERE id = ?",
            (new_email_hash, new_email_enc, user_id),
        )
    log_event("EMAIL_CHANGE_SUCCESS", str(user_id), "Email updated")
    return True, "Email updated."


def update_password(
    user_id: int,
    current_password: str,
    new_password: str,
    confirm_password: str,
    dry_run: bool = False
) -> tuple:
    """
    Change the user's password.
    If dry_run=True, validates all inputs but does NOT write to the database.
    Returns (success, message).
    """
    if new_password != confirm_password:
        return False, "New passwords do not match."

    valid, msg = validate_password(new_password)
    if not valid:
        return False, msg

    with get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if not row:
            return False, "User not found."
        if not verify_password(current_password, row["password_hash"]):
            log_event("PASSWORD_CHANGE_FAILED", str(user_id), "Incorrect current password")
            return False, "Current password is incorrect."
        if verify_password(new_password, row["password_hash"]):
            return False, "New password must differ from your current one."

        if dry_run:
            return True, "Validation passed."

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), user_id),
        )
    log_event("PASSWORD_CHANGE_SUCCESS", str(user_id), "Password changed via settings")
    return True, "Password changed."


# ── Session ──────────────────────────────────────────────────────────────────

class Session:
    """
    Lightweight in-memory session.
    Use load_by_username() after the existing login flow completes.
    All user fields (username, email) are decrypted before being stored
    in memory — the session always holds plaintext for the UI.
    """

    def __init__(self):
        self._user: dict | None = None

    def load_by_username(self, username: str) -> bool:
        """Populate session from DB using username (plaintext input)."""
        self._user = get_user_by_username(username)
        return self._user is not None

    def logout(self):
        self._user = None

    @property
    def is_logged_in(self) -> bool:
        return self._user is not None

    @property
    def user_id(self) -> int | None:
        return self._user["id"] if self._user else None

    @property
    def user(self) -> dict | None:
        return self._user

    def refresh(self):
        """Re-fetch and re-decrypt user data from DB (call after any update)."""
        if self._user:
            self._user = get_user(self._user["id"])
