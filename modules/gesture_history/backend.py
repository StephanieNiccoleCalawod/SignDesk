"""
modules/gesture_history/backend.py
SQLite implementation for logging ASL gestures and managing history settings.

FIX: init_history_db() now syncs the DB 'logging_enabled' setting from
     config (privacy.gesture_history_log) so that the Settings toggle and
     the DB are always in agreement on startup.

DATA ISOLATION: All user-scoped functions require a user_id parameter.
     The gesture_history table includes a user_id column with a foreign key
     to users(id). All SELECT, INSERT, DELETE queries are scoped by user_id.
"""

from datetime import datetime
from core.database import get_connection

def init_history_db() -> tuple[bool, str]:
    """
    Creates gesture_history and gesture_history_settings tables.
    Seeds default settings if missing, then syncs logging_enabled from config.

    Includes a migration to add user_id column to existing tables.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gesture_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    gesture TEXT NOT NULL,
                    translated_text TEXT,
                    confidence REAL,
                    logged_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gesture_history_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # ── Migration: add user_id column if missing ──────────────────
            cursor.execute("PRAGMA table_info(gesture_history)")
            columns = [col[1] for col in cursor.fetchall()]
            if "user_id" not in columns:
                cursor.execute(
                    "ALTER TABLE gesture_history ADD COLUMN user_id INTEGER REFERENCES users(id)"
                )
                # Clear orphaned rows that have no ownership
                cursor.execute("DELETE FROM gesture_history WHERE user_id IS NULL")
            
            # Seed defaults if rows are completely absent
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

        # ── Sync DB flag from config ──────────────────────────────────────────
        # The Settings toggle writes to both config AND the DB via _toggle_hist().
        # On a fresh launch config is the source of truth; copy it into the DB.
        _sync_logging_flag_from_config()

        return True, "History database initialized successfully."
    except Exception as e:
        return False, f"Failed to initialize history database: {str(e)}"


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
        pass   # config not available in test environments — keep DB value as-is

def get_setting(key: str) -> str:
    """Returns the setting value or an empty string if not found."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM gesture_history_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row['value']
            return ''
    except Exception:
        return ''

def set_setting(key: str, value: str) -> None:
    """Inserts or replaces a setting value."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO gesture_history_settings (key, value)
                VALUES (?, ?)
            """, (key, value))
    except Exception:
        pass

def log_gesture(user_id: int, gesture: str, translated_text: str, confidence: float) -> bool:
    """
    Logs a gesture for a specific user if logging_enabled is '1'.
    Includes translated_text and confidence based on their respective settings.
    """
    if user_id is None:
        return False
    try:
        if get_setting('logging_enabled') != '1':
            return False
            
        final_translation = translated_text if get_setting('include_translation') == '1' else None
        final_confidence = confidence if get_setting('include_confidence') == '1' else None
        logged_at = datetime.now().isoformat(timespec="seconds")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO gesture_history (user_id, gesture, translated_text, confidence, logged_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, gesture, final_translation, final_confidence, logged_at))
        return True
    except Exception:
        return False

def get_history(user_id: int) -> list[dict]:
    """Returns gesture history records for a specific user, ordered by time."""
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
            return [dict(row) for row in rows]
    except Exception:
        return []

def clear_history(user_id: int) -> tuple[bool, str]:
    """Clears gesture history records for a specific user only."""
    if user_id is None:
        return False, "No user session — cannot clear history."
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM gesture_history WHERE user_id = ?", (user_id,))
        return True, "All gesture history records have been cleared successfully."
    except Exception as e:
        return False, f"Failed to clear history: {str(e)}"

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
            if row:
                return row['count']
            return 0
    except Exception:
        return 0
