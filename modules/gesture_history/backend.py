"""
modules/gesture_history/backend.py
SQLite implementation for logging ASL gestures and managing history settings.

Encryption layer (v2)
---------------------
gesture_history.translated_text_enc stores a Fernet ciphertext.
gesture_history.translated_text is cleared (NULL) after migration.
All writes encrypt the value; all reads decrypt it transparently.

FIX: init_history_db() now syncs the DB 'logging_enabled' setting from
     config (privacy.gesture_history_log) so that the Settings toggle and
     the DB are always in agreement on startup.

DATA ISOLATION: All user-scoped functions require a user_id parameter.
     The gesture_history table includes a user_id column with a foreign key
     to users(id). All SELECT, INSERT, DELETE queries are scoped by user_id.
"""

from datetime import datetime
from core.database import get_connection
from core.crypto import encrypt, decrypt


def init_history_db() -> tuple[bool, str]:
    """
    Creates gesture_history and gesture_history_settings tables.
    Seeds default settings if missing, then syncs logging_enabled from config.
    Runs the translated_text encryption migration on any existing rows.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gesture_history (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id             INTEGER,
                    gesture             TEXT NOT NULL,
                    translated_text     TEXT,
                    translated_text_enc TEXT DEFAULT '',
                    confidence          REAL,
                    logged_at           TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gesture_history_settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # ── Migrations ────────────────────────────────────────────────
            cursor.execute("PRAGMA table_info(gesture_history)")
            columns = [col[1] for col in cursor.fetchall()]

            if "user_id" not in columns:
                cursor.execute(
                    "ALTER TABLE gesture_history ADD COLUMN user_id INTEGER REFERENCES users(id)"
                )
                cursor.execute("DELETE FROM gesture_history WHERE user_id IS NULL")

            if "translated_text_enc" not in columns:
                cursor.execute(
                    "ALTER TABLE gesture_history ADD COLUMN translated_text_enc TEXT DEFAULT ''"
                )

            # Seed default settings
            defaults = {
                "logging_enabled":     "0",
                "include_confidence":  "1",
                "include_translation": "1",
            }
            for k, v in defaults.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO gesture_history_settings (key, value) VALUES (?, ?)",
                    (k, v),
                )

        # Encrypt any existing plaintext translated_text rows
        _migrate_translated_text_encryption()

        # Sync logging flag from config
        _sync_logging_flag_from_config()

        return True, "History database initialized successfully."
    except Exception as e:
        print(f"[history] init_history_db error: {e}")
        return False, "Failed to initialize history database. Please restart the application."


def _migrate_translated_text_encryption():
    """Encrypt any gesture_history rows whose translated_text is still plaintext."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, translated_text
                  FROM gesture_history
                 WHERE translated_text IS NOT NULL
                   AND translated_text != ''
                   AND (translated_text_enc IS NULL OR translated_text_enc = '')
                """
            )
            rows = cursor.fetchall()
            for row in rows:
                cursor.execute(
                    """
                    UPDATE gesture_history
                       SET translated_text_enc = ?,
                           translated_text     = NULL
                     WHERE id = ?
                    """,
                    (encrypt(row["translated_text"]), row["id"]),
                )
    except Exception:
        pass  # Non-fatal — migration will retry next startup


def _sync_logging_flag_from_config():
    """
    Reads privacy.gesture_history_log from config and writes the matching
    value into gesture_history_settings so the DB and config agree.
    Called once at startup from init_history_db().
    """
    try:
        from core.config import config
        enabled = config.get("privacy.gesture_history_log", False)
        set_setting("logging_enabled", "1" if enabled else "0")
    except Exception:
        pass  # config not available in test environments


def get_setting(key: str) -> str:
    """Returns the setting value or an empty string if not found."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM gesture_history_settings WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            return row["value"] if row else ""
    except Exception:
        return ""


def set_setting(key: str, value: str) -> None:
    """Inserts or replaces a setting value."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO gesture_history_settings (key, value) VALUES (?, ?)",
                (key, value)
            )
    except Exception:
        pass


def log_gesture(
    user_id: int, gesture: str, translated_text: str, confidence: float
) -> bool:
    """
    Logs a gesture for a specific user if logging_enabled is '1'.
    translated_text is stored encrypted in translated_text_enc;
    the plaintext translated_text column is left NULL.
    """
    if user_id is None:
        return False
    try:
        if get_setting("logging_enabled") != "1":
            return False

        final_translation = (
            translated_text if get_setting("include_translation") == "1" else None
        )
        final_confidence = (
            confidence if get_setting("include_confidence") == "1" else None
        )
        logged_at = datetime.now().isoformat(timespec="seconds")

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO gesture_history
                    (user_id, gesture, translated_text, translated_text_enc,
                     confidence, logged_at)
                VALUES (?, ?, NULL, ?, ?, ?)
                """,
                (
                    user_id,
                    gesture,
                    encrypt(final_translation) if final_translation is not None else "",
                    final_confidence,
                    logged_at,
                )
            )
        return True
    except Exception:
        return False


def get_history(user_id: int) -> list[dict]:
    """
    Returns gesture history records for a specific user, ordered by time.
    Decrypts translated_text_enc transparently so callers receive plaintext.
    """
    if user_id is None:
        return []
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM gesture_history WHERE user_id = ? ORDER BY logged_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()

        result = []
        for row in rows:
            d = dict(row)
            # Prefer the encrypted column; fall back to the legacy plaintext column
            enc = d.get("translated_text_enc") or ""
            plain = d.get("translated_text") or ""
            d["translated_text"] = decrypt(enc) if enc else plain
            result.append(d)

        return result
    except Exception:
        return []


def clear_history(user_id: int) -> tuple[bool, str]:
    """Clears gesture history records for a specific user only."""
    if user_id is None:
        return False, "No user session — cannot clear history."
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM gesture_history WHERE user_id = ?", (user_id,)
            )
        return True, "All gesture history records have been cleared successfully."
    except Exception as e:
        print(f"[history] clear_history error: {e}")
        return False, "Failed to clear history. Please try again."


def get_record_count(user_id: int) -> int:
    """Returns the total number of logged gestures for a specific user."""
    if user_id is None:
        return 0
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as count FROM gesture_history WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            return row["count"] if row else 0
    except Exception:
        return 0
