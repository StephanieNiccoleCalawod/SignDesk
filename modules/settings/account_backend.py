"""
SignDesk — Account Settings Backend
Adapted to work with the existing project database (core/database.py).
Auth: bcrypt hashed passwords (same as existing auth system).

Dependency: pip install bcrypt
"""

import bcrypt
import re
from core.database import get_connection


# ── Schema migration ────────────────────────────────────────────────────────────

def init_account_db():
    """
    Add a 'name' (display name) column to the existing users table if missing.
    Safe to run on every startup.
    """
    try:
        conn = get_connection()
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [col["name"] for col in cursor.fetchall()]

        if "name" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN name TEXT DEFAULT ''")
            # Seed display name from username for existing users
            conn.execute(
                "UPDATE users SET name = username WHERE name = '' OR name IS NULL"
            )
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[account_backend] migration warning: {e}")


# ── Validation helpers ──────────────────────────────────────────────────────────

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


# ── Auth helpers ────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── User lookup ─────────────────────────────────────────────────────────────────

def get_user(user_id: int) -> dict | None:
    """Fetch user by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, name, email FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if row:
        d = dict(row)
        # Fallback: if name is empty, use username
        if not d.get("name"):
            d["name"] = d.get("username", "")
        return d
    return None


def get_user_by_username(username: str) -> dict | None:
    """Fetch user by username (used after existing login flow)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, name, email FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()

    if row:
        d = dict(row)
        if not d.get("name"):
            d["name"] = d.get("username", "")
        return d
    return None


# ── Account CRUD ────────────────────────────────────────────────────────────────

def update_display_name(user_id: int, new_name: str) -> tuple:
    """
    Update the user's display name.
    Returns (success, message).
    """
    new_name = new_name.strip()
    if not new_name:
        return False, "Display name cannot be empty."

    conn = get_connection()
    conn.execute(
        "UPDATE users SET name = ? WHERE id = ?",
        (new_name, user_id),
    )
    conn.commit()
    conn.close()
    return True, "Display name updated."


def update_email(user_id: int, new_email: str, current_password: str) -> tuple:
    """
    Update the user's email address.
    Requires current password for verification.
    Returns (success, message).
    """
    new_email = new_email.strip().lower()

    if not validate_email(new_email):
        return False, "Please enter a valid email address."

    conn = get_connection()
    row = conn.execute(
        "SELECT password_hash, email FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    if not row:
        conn.close()
        return False, "User not found."
    if not verify_password(current_password, row["password_hash"]):
        conn.close()
        return False, "Incorrect password."
    if new_email == row["email"]:
        conn.close()
        return False, "This is already your current email."

    # Check not taken by another account
    exists = conn.execute(
        "SELECT id FROM users WHERE email = ? AND id != ?",
        (new_email, user_id),
    ).fetchone()
    if exists:
        conn.close()
        return False, "That email is already in use."

    conn.execute(
        "UPDATE users SET email = ? WHERE id = ?",
        (new_email, user_id),
    )
    conn.commit()
    conn.close()
    return True, "Email updated."


def update_password(
    user_id: int,
    current_password: str,
    new_password: str,
    confirm_password: str
) -> tuple:
    """
    Change the user's password.
    Returns (success, message).
    """
    if new_password != confirm_password:
        return False, "New passwords do not match."

    valid, msg = validate_password(new_password)
    if not valid:
        return False, msg

    conn = get_connection()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    if not row:
        conn.close()
        return False, "User not found."
    if not verify_password(current_password, row["password_hash"]):
        conn.close()
        return False, "Current password is incorrect."
    if verify_password(new_password, row["password_hash"]):
        conn.close()
        return False, "New password must differ from your current one."

    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(new_password), user_id),
    )
    conn.commit()
    conn.close()
    return True, "Password changed."


# ── Session ─────────────────────────────────────────────────────────────────────

class Session:
    """
    Lightweight in-memory session.
    Use load_by_username() after the existing login flow completes.
    """

    def __init__(self):
        self._user: dict | None = None

    def load_by_username(self, username: str) -> bool:
        """Populate session from the existing DB using username."""
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
        """Re-fetch user data from DB (call after any update)."""
        if self._user:
            self._user = get_user(self._user["id"])
