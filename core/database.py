"""
database.py - SignDesk Database Connection (Core)
Connects to a local SQLite database file perfectly aligned with offline requirements.
"""

import sqlite3
import os
from contextlib import contextmanager

# ──────────────────────────────────────────────────────────────
# CONNECTION SETTINGS
# ──────────────────────────────────────────────────────────────

# Create the database in the root of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "signdesk.db")

@contextmanager
def get_connection():
    """
    Context manager that yields a live SQLite connection.
    • Enables foreign key enforcement via PRAGMA.
    • Auto-commits on clean exit, auto-rollbacks on exception.
    • Always closes the connection in the finally block.

    Usage:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
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
# SCHEMA MIGRATION / INITIALIZATION
# ──────────────────────────────────────────────────────────────

def _create_users_table(cursor):
    """Creates the users table if it does not exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email_verified INTEGER DEFAULT 0,
            verification_code TEXT NULL,
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


def update_database_schema():
    """
    Ensures the SQLite database has all required tables and columns.
    Safe to run on every startup.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            _create_users_table(cursor)
            _create_otp_tokens_table(cursor)
    except Exception as e:
        print(f"Schema Error: {e}")

# ──────────────────────────────────────────────────────────────
# TEST
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        with get_connection() as conn:
            print(f"Connected to SQLite Database successfully at: {DB_PATH}")
        update_database_schema()
    except Exception as e:
        print(f"Connection failed: {e}")
