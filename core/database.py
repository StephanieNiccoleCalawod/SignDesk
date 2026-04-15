"""
database.py - SignDesk Database Connection (Core)
Connects to a local SQLite database file perfectly aligned with offline requirements.
"""

import sqlite3
import os

# ──────────────────────────────────────────────────────────────
# CONNECTION SETTINGS
# ──────────────────────────────────────────────────────────────

# Create the database in the root of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "signdesk.db")

def get_connection():
    """
    Returns a live connection to the local SQLite database.
    Creates the file automatically if it doesn't exist.
    """
    # PARSE_DECLTYPES ensures DATETIME columns map correctly to Python datetime objects
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    # Enable name-based access to columns (similar to pyodbc rows)
    conn.row_factory = sqlite3.Row
    return conn

# ──────────────────────────────────────────────────────────────
# SCHEMA MIGRATION / INITIALIZATION
# ──────────────────────────────────────────────────────────────

def update_database_schema():
    """
    Ensures the SQLite database has all required tables and columns.
    Safe to run on every startup.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Create the users table
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

        # OTP tokens table for password reset flow
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otp_tokens (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT    NOT NULL,
                otp_code   TEXT    NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                is_used    INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Schema Error: {e}")

# ──────────────────────────────────────────────────────────────
# TEST
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        conn = get_connection()
        print(f"Connected to SQLite Database successfully at: {DB_PATH}")
        conn.close()
        update_database_schema()
    except Exception as e:
        print(f"Connection failed: {e}")
