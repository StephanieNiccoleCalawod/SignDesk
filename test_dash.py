import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath('.'))

from modules.dashboard.dashboard_service import get_dashboard_summary

print("Running dashboard summary test...")

# Need to find a valid user
import sqlite3
from core.database import get_connection

with get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT username FROM users LIMIT 1")
    row = c.fetchone()
    username = row["username"] if row else None

print(f"Testing with username: {username}")

if username:
    summary = get_dashboard_summary(username)
    print("--- Summary ---")
    print(f"Sessions Today: {summary.sessions_today}")
    print(f"Unique Signs: {summary.unique_signs_recognized}")
    print(f"Avg Confidence: {summary.avg_confidence}")
    print(f"Recent Activity Count: {len(summary.recent_activity)}")
    for i, a in enumerate(summary.recent_activity):
        print(f"  Activity {i}: {a}")
else:
    print("No users found.")
