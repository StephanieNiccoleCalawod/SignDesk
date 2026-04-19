"""
SignDesk — Gesture History Backend
SQLite implementation for logging ASL gestures and managing history settings.
"""

from datetime import datetime
from core.database import get_connection

def init_history_db() -> tuple[bool, str]:
    """
    Creates gesture_history and gesture_history_settings tables.
    Seeds default settings if they are missing.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gesture_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gesture TEXT NOT NULL,
                translated_text TEXT,
                confidence REAL,
                logged_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gesture_history_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Insert defaults if missing (SD009-AC1)
        defaults = {
            'logging_enabled': '0',
            'include_confidence': '1',
            'include_translation': '0'
        }
        
        for k, v in defaults.items():
            cursor.execute("""
                INSERT OR IGNORE INTO gesture_history_settings (key, value)
                VALUES (?, ?)
            """, (k, v))
            
        conn.commit()
        conn.close()
        return True, "History database initialized successfully."
    except Exception as e:
        return False, f"Failed to initialize history database: {str(e)}"

def get_setting(key: str) -> str:
    """Returns the setting value or an empty string if not found."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM gesture_history_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row['value']
        return ''
    except Exception:
        return ''

def set_setting(key: str, value: str) -> None:
    """Inserts or replaces a setting value."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO gesture_history_settings (key, value)
            VALUES (?, ?)
        """, (key, value))
        conn.commit()
        conn.close()
    except Exception:
        pass

def log_gesture(gesture: str, translated_text: str, confidence: float) -> bool:
    """
    Logs a gesture if logging_enabled is '1'.
    Includes translated_text and confidence based on their respective settings.
    """
    try:
        if get_setting('logging_enabled') != '1':
            return False
            
        final_translation = translated_text if get_setting('include_translation') == '1' else None
        final_confidence = confidence if get_setting('include_confidence') == '1' else None
        logged_at = datetime.now().isoformat()
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO gesture_history (gesture, translated_text, confidence, logged_at)
            VALUES (?, ?, ?, ?)
        """, (gesture, final_translation, final_confidence, logged_at))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def get_history() -> list[dict]:
    """Returns all gesture history records ordered by time."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gesture_history ORDER BY logged_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception:
        return []

def clear_history() -> tuple[bool, str]:
    """Clears all gesture history records."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM gesture_history")
        conn.commit()
        conn.close()
        return True, "All gesture history records have been cleared successfully."
    except Exception as e:
        return False, f"Failed to clear history: {str(e)}"

def get_record_count() -> int:
    """Returns the total number of logged gestures."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM gesture_history")
        row = cursor.fetchone()
        conn.close()
        if row:
            return row['count']
        return 0
    except Exception:
        return 0
