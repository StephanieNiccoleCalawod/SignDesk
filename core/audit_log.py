"""
core/audit_log.py — Security Audit Logging for SignDesk

Records security-relevant events to a dedicated `audit_log` table in SQLite
for forensic analysis and accountability.

Tracked events:
  LOGIN_SUCCESS, LOGIN_FAILED, REGISTER_SUCCESS, REGISTER_FAILED,
  EMAIL_VERIFY_SUCCESS, EMAIL_VERIFY_FAILED, OTP_VERIFY_SUCCESS,
  OTP_VERIFY_FAILED, PASSWORD_RESET_SUCCESS, PASSWORD_RESET_FAILED,
  PASSWORD_CHANGE_SUCCESS, PASSWORD_CHANGE_FAILED,
  EMAIL_CHANGE_SUCCESS, EMAIL_CHANGE_FAILED, LOGOUT

Each entry stores: timestamp, event type, actor (username), and detail.
"""

from datetime import datetime
from core.database import get_connection


# ── Schema ────────────────────────────────────────────────────────────────────

def init_audit_log():
    """
    Create the audit_log table if it does not exist.
    Called once on application startup from update_database_schema().
    """
    try:
        with get_connection() as conn:
            # Check if the table exists but is missing the 'actor' column
            cursor = conn.execute("PRAGMA table_info(audit_log)")
            columns = [row[1] for row in cursor.fetchall()]

            if columns and "actor" not in columns:
                # Old schema — drop and recreate
                conn.execute("DROP TABLE audit_log")
                print("[audit] Recreated audit_log table with updated schema.")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT    NOT NULL,
                    event     TEXT    NOT NULL,
                    actor     TEXT    NOT NULL DEFAULT '',
                    detail    TEXT    NOT NULL DEFAULT ''
                )
            """)
    except Exception as e:
        print(f"[audit] Failed to create audit_log table: {e}")


# ── Public API ────────────────────────────────────────────────────────────────

def log_event(event: str, actor: str = "", detail: str = ""):
    """
    Write a single audit entry.

    Args:
        event:  Event type constant (e.g. "LOGIN_SUCCESS").
        actor:  The username or identifier performing the action.
                Pass "" for anonymous/pre-auth events.
        detail: Optional human-readable context string.
    """
    try:
        ts = datetime.now().isoformat(timespec="seconds")
        print(f"[audit] Writing event: {event} | actor={actor} | detail={detail}")
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO audit_log (timestamp, event, actor, detail) "
                "VALUES (?, ?, ?, ?)",
                (ts, event, actor, detail),
            )
        print(f"[audit] ✓ Event written successfully")
    except Exception as e:
        # Audit logging must never crash the application
        print(f"[audit] ✗ Failed to write event {event}: {e}")


# ── Query helpers (for future admin UI / export) ──────────────────────────────

def get_recent_events(limit: int = 100) -> list[dict]:
    """Return the most recent audit events as a list of dicts."""
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, event, actor, detail "
                "FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []


def get_events_for_user(actor: str, limit: int = 50) -> list[dict]:
    """Return audit events for a specific user."""
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, event, actor, detail "
                "FROM audit_log WHERE actor = ? ORDER BY id DESC LIMIT ?",
                (actor, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
