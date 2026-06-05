import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath('.'))

from modules.gesture_history.backend import get_history
from core.database import get_connection

with get_connection() as conn:
    users = conn.execute("SELECT id, username FROM users").fetchall()

for row in users:
    user_id = row["id"]
    username = row["username"]
    print(f"\n======================================")
    print(f"User ID: {user_id}, Username: {username}")
    
    history = get_history(user_id)
    print(f"Total history rows: {len(history)}")
    
    if not history:
        continue
        
    print(f"First row raw: {history[0]}")
    
    sessions_today = 0
    unique_signs = set()
    recent_activity = []
    
    today_date = datetime.now().date()
    print(f"today_date={today_date}")
    
    last_dt = None
    
    for r in history:
        logged_at = r.get("logged_at")
        try:
            dt = datetime.fromisoformat(logged_at)
        except Exception as e:
            print(f"Failed to parse dt: {logged_at} - {e}")
            continue
            
        g = r.get("gesture")
        if g:
            unique_signs.add(g)
            
        if dt.date() == today_date:
            if last_dt is None:
                sessions_today += 1
                last_dt = dt
            else:
                gap = (last_dt - dt).total_seconds()
                if gap > 15 * 60:
                    sessions_today += 1
                last_dt = dt
                
        if len(recent_activity) < 5:
            recent_activity.append(r)
            
    print(f"Sessions Today computed: {sessions_today}")
    print(f"Unique signs computed: {len(unique_signs)}")
    print(f"Recent Activity Count: {len(recent_activity)}")
    if recent_activity:
        print("Recent Activities:")
        for a in recent_activity:
            print(f"  Gesture: '{a.get('gesture')}' | Logged At: {a.get('logged_at')} | Confidence: {a.get('confidence')}")
