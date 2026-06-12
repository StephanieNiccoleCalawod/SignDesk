"""
modules/gesture_history/backend.py
SQLite implementation for quiz result logging.

Schema (v3)
-----------
Replaces the legacy gesture_history encryption table with a clean
quiz_results table that stores one row per quiz attempt (Camera Practice
or Flashcard Quiz).  The legacy table is preserved untouched for safety.

quiz_results columns
--------------------
  id         INTEGER PK AUTOINCREMENT
  username   TEXT NOT NULL          -- login username of the user
  source     TEXT NOT NULL          -- 'camera_practice' | 'flashcard_quiz'
  letter     TEXT NOT NULL          -- target ASL letter e.g. 'A'
  result     TEXT NOT NULL          -- 'correct' | 'missed' | 'skipped'
  confidence REAL                   -- CNN confidence 0-1, NULL for flashcard
  set_name   TEXT                   -- e.g. 'Set 1 (A-E)', 'Random 10'
  logged_at  TEXT NOT NULL          -- ISO-8601 timestamp
"""

from datetime import datetime, date
from core.database import get_connection
from core.crypto import encrypt, decrypt  # kept for legacy compat


# ── Init ──────────────────────────────────────────────────────────────────────

def init_history_db() -> tuple[bool, str]:
    """
    Creates the quiz_results table (and legacy tables if absent).
    Safe to call multiple times — uses CREATE TABLE IF NOT EXISTS.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # ── New table ────────────────────────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quiz_results (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    username   TEXT NOT NULL,
                    source     TEXT NOT NULL,
                    letter     TEXT NOT NULL,
                    result     TEXT NOT NULL,
                    confidence REAL,
                    set_name   TEXT,
                    logged_at  TEXT NOT NULL
                )
            """)

            # ── Legacy tables (preserved, not used for new writes) ───────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gesture_history (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id             INTEGER,
                    gesture             TEXT,
                    gesture_enc         TEXT DEFAULT '',
                    translated_text     TEXT,
                    translated_text_enc TEXT DEFAULT '',
                    confidence          REAL,
                    logged_at           TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gesture_history_settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            defaults = {
                "logging_enabled":     "1",   # always on for quiz results
                "include_confidence":  "1",
                "include_translation": "1",
            }
            for k, v in defaults.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO gesture_history_settings (key, value) VALUES (?, ?)",
                    (k, v),
                )

        return True, "History database initialized successfully."
    except Exception as e:
        print(f"[history] init_history_db error: {e}")
        return False, "Failed to initialize history database."


# ── Write ─────────────────────────────────────────────────────────────────────

def log_quiz_result(
    username: str,
    source: str,        # 'camera_practice' | 'flashcard_quiz'
    letter: str,
    result: str,        # 'correct' | 'missed' | 'skipped'
    confidence: float | None = None,
    set_name: str | None = None,
) -> bool:
    """
    Logs one quiz attempt to quiz_results.
    Always succeeds regardless of any privacy setting — quiz results
    are practice data, not surveillance.
    """
    if not username or not letter or not result:
        return False
    try:
        logged_at = datetime.now().isoformat(timespec="seconds")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO quiz_results
                    (username, source, letter, result, confidence, set_name, logged_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (username, source, letter.upper(), result, confidence, set_name, logged_at),
            )
        return True
    except Exception as e:
        print(f"[history] log_quiz_result error: {e}")
        return False


# ── Read ──────────────────────────────────────────────────────────────────────

def get_quiz_results(username: str) -> list[dict]:
    """Returns all quiz_results for a user, newest first."""
    if not username:
        return []
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM quiz_results WHERE username = ? ORDER BY logged_at DESC",
                (username,),
            )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[history] get_quiz_results error: {e}")
        return []


def get_record_count(username: str) -> int:
    """Total quiz attempts for a user."""
    if not username:
        return 0
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as count FROM quiz_results WHERE username = ?",
                (username,),
            )
            row = cursor.fetchone()
            return row["count"] if row else 0
    except Exception:
        return 0


def clear_history(username: str) -> tuple[bool, str]:
    """Deletes all quiz_results for a user."""
    if not username:
        return False, "No username provided."
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM quiz_results WHERE username = ?", (username,))
        return True, "All practice records cleared successfully."
    except Exception as e:
        print(f"[history] clear_history error: {e}")
        return False, "Failed to clear records."


def today_count(username: str) -> int:
    """Number of quiz attempts today for a user."""
    if not username:
        return 0
    try:
        today = date.today().isoformat()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as count FROM quiz_results WHERE username = ? AND logged_at LIKE ?",
                (username, f"{today}%"),
            )
            row = cursor.fetchone()
            return row["count"] if row else 0
    except Exception:
        return 0


# ── Legacy shims (kept so old imports don't break) ────────────────────────────

def get_setting(key: str) -> str:
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
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO gesture_history_settings (key, value) VALUES (?, ?)",
                (key, value),
            )
    except Exception:
        pass


def get_history(user_id: int) -> list[dict]:
    """Legacy shim — returns empty list. Use get_quiz_results() instead."""
    return []


def log_gesture(user_id, gesture, translated_text, confidence) -> bool:
    """Legacy shim — no-op. Use log_quiz_result() instead."""
    return False