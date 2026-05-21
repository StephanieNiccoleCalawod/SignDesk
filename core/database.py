"""
database.py - SignDesk Database Connection (Core)
Connects to a local SQLite database file perfectly aligned with offline requirements.

Encryption migration (v2)
--------------------------
Sensitive columns are encrypted at rest:

  users table
  ──────────────────────────────────────────────────────────────────────────
  username      TEXT UNIQUE  →  now stores HMAC-SHA256 hash for fast lookups
  email         TEXT UNIQUE  →  now stores HMAC-SHA256 hash for fast lookups
  username_enc  TEXT         →  Fernet ciphertext (decrypted for display only)
  email_enc     TEXT         →  Fernet ciphertext (decrypted for display only)

  otp_tokens table
  ──────────────────────────────────────────────────────────────────────────
  email         TEXT         →  now stores HMAC-SHA256 hash (lookup only)

  gesture_history table
  ──────────────────────────────────────────────────────────────────────────
  translated_text      TEXT  →  cleared after migration (NULL)
  translated_text_enc  TEXT  →  Fernet ciphertext (decrypted for display only)

All migrations are idempotent — safe to run on every startup.
"""

import sqlite3
import os
from contextlib import contextmanager

# ──────────────────────────────────────────────────────────────
# CONNECTION SETTINGS
# ──────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "signdesk.db")


@contextmanager
def get_connection():
    """
    Context manager that yields a live SQLite connection.
    Enables foreign key enforcement via PRAGMA.
    Auto-commits on clean exit, auto-rollbacks on exception.
    Always closes the connection in the finally block.
    """
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# SCHEMA CREATION
# ──────────────────────────────────────────────────────────────

def _create_users_table(cursor):
    """Creates the users table if it does not exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            username            TEXT UNIQUE NOT NULL,
            email               TEXT UNIQUE NOT NULL,
            password_hash       TEXT NOT NULL,
            email_verified      INTEGER DEFAULT 0,
            verification_code   TEXT NULL,
            verification_expiry TIMESTAMP NULL
        )
    """)


def _create_otp_tokens_table(cursor):
    """Creates the OTP tokens table for the password reset flow."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_tokens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT    NOT NULL,
            otp_code   TEXT    NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            is_used    INTEGER DEFAULT 0
        )
    """)


# ──────────────────────────────────────────────────────────────
# ENCRYPTION MIGRATION HELPERS
# ──────────────────────────────────────────────────────────────

def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _is_hash(value: str) -> bool:
    """Return True if *value* looks like an HMAC-SHA256 hex digest (already migrated)."""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def _migrate_users_encryption(conn):
    """
    Add username_enc / email_enc columns and encrypt all existing plaintext rows.

    After migration:
      users.username     = HMAC hash  (WHERE clause / UNIQUE)
      users.email        = HMAC hash  (WHERE clause / UNIQUE)
      users.username_enc = Fernet ciphertext
      users.email_enc    = Fernet ciphertext
    """
    from core.crypto import encrypt, hmac_hash

    cursor = conn.cursor()

    # Add encrypted display columns if absent
    for col in ("username_enc", "email_enc"):
        if not _column_exists(cursor, "users", col):
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT ''")

    # Add display-name column (account_backend uses this)
    if not _column_exists(cursor, "users", "name"):
        cursor.execute("ALTER TABLE users ADD COLUMN name TEXT DEFAULT ''")

    conn.commit()

    # Migrate rows whose username_enc is empty (not yet encrypted)
    cursor.execute(
        "SELECT id, username, email, name FROM users "
        "WHERE username_enc IS NULL OR username_enc = ''"
    )
    rows = cursor.fetchall()

    for row in rows:
        uid         = row["id"]
        raw_user    = row["username"]
        raw_email   = row["email"]
        display_name = row["name"] or ""

        # Already migrated on a previous run — skip
        if _is_hash(raw_user):
            continue

        # Seed display name from plaintext username before we lose it
        if not display_name:
            display_name = raw_user

        cursor.execute(
            """
            UPDATE users
               SET username     = ?,
                   email        = ?,
                   username_enc = ?,
                   email_enc    = ?,
                   name         = ?
             WHERE id = ?
            """,
            (
                hmac_hash(raw_user),
                hmac_hash(raw_email, normalize=True),
                encrypt(raw_user),
                encrypt(raw_email),
                display_name,
                uid,
            ),
        )

    conn.commit()


def _migrate_otp_tokens_encryption(conn):
    """
    Replace plaintext emails in otp_tokens with HMAC hashes.
    No display column needed — the email is only used for WHERE lookups.
    """
    from core.crypto import hmac_hash

    cursor = conn.cursor()
    cursor.execute("SELECT id, email FROM otp_tokens")
    for row in cursor.fetchall():
        if not _is_hash(row["email"]):
            cursor.execute(
                "UPDATE otp_tokens SET email = ? WHERE id = ?",
                (hmac_hash(row["email"], normalize=True), row["id"]),
            )
    conn.commit()


def _migrate_gesture_history_encryption(conn):
    """
    Add translated_text_enc and encrypt any existing plaintext rows.

    After migration:
      gesture_history.translated_text     = NULL
      gesture_history.translated_text_enc = Fernet ciphertext
    """
    from core.crypto import encrypt

    cursor = conn.cursor()

    if not _column_exists(cursor, "gesture_history", "translated_text_enc"):
        cursor.execute(
            "ALTER TABLE gesture_history ADD COLUMN translated_text_enc TEXT DEFAULT ''"
        )
        conn.commit()

    cursor.execute(
        """
        SELECT id, translated_text
          FROM gesture_history
         WHERE translated_text IS NOT NULL
           AND translated_text != ''
           AND (translated_text_enc IS NULL OR translated_text_enc = '')
        """
    )
    for row in cursor.fetchall():
        cursor.execute(
            """
            UPDATE gesture_history
               SET translated_text_enc = ?,
                   translated_text     = NULL
             WHERE id = ?
            """,
            (encrypt(row["translated_text"]), row["id"]),
        )
    conn.commit()


# ──────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ──────────────────────────────────────────────────────────────

def update_database_schema():
    """
    Ensure all tables exist, then run encryption migrations on any
    unprotected rows.  Safe to call on every startup.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            _create_users_table(cursor)
            _create_otp_tokens_table(cursor)

        # Initialize audit log table
        from core.audit_log import init_audit_log
        init_audit_log()

        with get_connection() as conn:
            _migrate_users_encryption(conn)

        with get_connection() as conn:
            _migrate_otp_tokens_encryption(conn)

        # gesture_history is created by the gesture_history backend — only
        # migrate it if the table already exists.
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='gesture_history'"
            )
            if cursor.fetchone():
                _migrate_gesture_history_encryption(conn)

    except Exception as e:
        print(f"Schema/Migration Error: {e}")


# ──────────────────────────────────────────────────────────────
# TEST
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        with get_connection() as conn:
            print(f"Connected to SQLite Database successfully at: {DB_PATH}")
        update_database_schema()
        print("Schema and encryption migration complete.")
    except Exception as e:
        print(f"Connection failed: {e}")
