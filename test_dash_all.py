import sys
import os
import sqlite3

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath('.'))

from modules.dashboard.dashboard_service import get_dashboard_summary
from core.database import get_connection

print("Testing all users...")

with get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT id, username, email FROM users")
    users = c.fetchall()

for row in users:
    username = row["username"]
    print(f"\n--- Testing username: {username} ---")
    summary = get_dashboard_summary(username)
    if summary:
        print(f"Sessions Today: {summary.sessions_today}")
        print(f"Unique Signs: {summary.unique_signs_recognized}")
        print(f"Avg Confidence: {summary.avg_confidence:.1f}%")
        print(f"Recent Activity Count: {len(summary.recent_activity)}")
        for i, a in enumerate(summary.recent_activity):
            print(f"  Activity {i}: {a.gesture_name} - {a.confidence}")
    else:
        print("Summary returned None")

