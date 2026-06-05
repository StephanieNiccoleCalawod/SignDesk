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

Each entry stores: timestamp, event type, actor (encrypted), and detail.

Actor encryption
────────────────
  actor      TEXT  →  HMAC-SHA256 hash of the actor identifier (for lookups)
  actor_enc  TEXT  →  Fernet ciphertext of the actor identifier (for display)

Callers pass a pseudonymised actor (str(user_id) or hmac_hash(…)).
The value is HMAC-hashed for deterministic lookups and Fernet-encrypted
for future display/export.  No plaintext usernames or email addresses
are ever written to the audit_log.
"""

from datetime import datetime
from core.database import get_connection
from core.crypto import encrypt, decrypt, hmac_hash


# ── Schema ────────────────────────────────────────────────────────────────────

def init_audit_log():
    """
    Create the audit_log table if it does not exist.
    Adds the actor_enc column and migrates existing rows.
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
                    actor_enc TEXT    NOT NULL DEFAULT '',
                    detail    TEXT    NOT NULL DEFAULT ''
                )
            """)

            # Migration: add actor_enc if table existed before this change
            cursor = conn.execute("PRAGMA table_info(audit_log)")
            cols = [row[1] for row in cursor.fetchall()]
            if "actor_enc" not in cols:
                conn.execute(
                    "ALTER TABLE audit_log ADD COLUMN actor_enc TEXT NOT NULL DEFAULT ''"
                )

        # Encrypt any existing plaintext actor values
        _migrate_actor_encryption()
    except Exception as e:
        print(f"[audit] Failed to create audit_log table: {e}")


# ── Migration ─────────────────────────────────────────────────────────────────

def _migrate_actor_encryption():
    """
    Encrypt any audit_log rows whose actor_enc is still empty.
    The existing actor value is HMAC-hashed for lookups; the original
    value is Fernet-encrypted into actor_enc.
    """
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, actor
                  FROM audit_log
                 WHERE actor != ''
                   AND (actor_enc IS NULL OR actor_enc = '')
                """
            )
            rows = cursor.fetchall()
            for row in rows:
                raw_actor = row["actor"]
                conn.execute(
                    """
                    UPDATE audit_log
                       SET actor     = ?,
                           actor_enc = ?
                     WHERE id = ?
                    """,
                    (hmac_hash(raw_actor), encrypt(raw_actor), row["id"]),
                )
    except Exception:
        pass  # Non-fatal — migration will retry next startup


# ── Public API ────────────────────────────────────────────────────────────────

def log_event(event: str, actor: str = "", detail: str = ""):
    """
    Write a single audit entry.

    Args:
        event:  Event type constant (e.g. "LOGIN_SUCCESS").
        actor:  Pseudonymised identifier — either str(user_id) for
                post-auth events or hmac_hash(username/email) for
                pre-auth events.  NEVER pass a plaintext username or
                email address.
        detail: Optional human-readable context string.
    """
    try:
        ts = datetime.now().isoformat(timespec="seconds")
        actor_hashed = hmac_hash(actor) if actor else ""
        actor_encrypted = encrypt(actor) if actor else ""
        print(f"[audit] Writing event: {event}")
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO audit_log (timestamp, event, actor, actor_enc, detail) "
                "VALUES (?, ?, ?, ?, ?)",
                (ts, event, actor_hashed, actor_encrypted, detail),
            )
        print(f"[audit] ✓ Event written successfully")
    except Exception as e:
        # Audit logging must never crash the application
        print(f"[audit] ✗ Failed to write event {event}: {e}")


# ── Query helpers (for future admin UI / export) ──────────────────────────────

def get_recent_events(limit: int = 100) -> list[dict]:
    """Return the most recent audit events as a list of dicts.
    Decrypts actor_enc transparently so callers receive the original actor value."""
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, event, actor, actor_enc, detail "
                "FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                enc = d.pop("actor_enc", "") or ""
                d["actor"] = decrypt(enc) if enc else d["actor"]
                results.append(d)
            return results
    except Exception:
        return []


def get_events_for_user(actor: str, limit: int = 50) -> list[dict]:
    """Return audit events for a specific actor (user_id or HMAC hash).
    The caller passes the raw actor value; it is HMAC-hashed internally
    for the WHERE lookup.  Results decrypt actor_enc for display."""
    try:
        actor_hashed = hmac_hash(actor) if actor else ""
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, event, actor, actor_enc, detail "
                "FROM audit_log WHERE actor = ? ORDER BY id DESC LIMIT ?",
                (actor_hashed, limit),
            )
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                enc = d.pop("actor_enc", "") or ""
                d["actor"] = decrypt(enc) if enc else d["actor"]
                results.append(d)
            return results
    except Exception:
        return []
