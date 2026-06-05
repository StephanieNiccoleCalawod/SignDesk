"""
modules/dashboard/dashboard_service.py - Dashboard Data Service
Provides a centralized data model (DashboardSummary) for the UI, minimizing DB calls.
"""

import cv2
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from core.config import config
from core.audit_log import get_events_for_user
from modules.gesture_history.backend import get_history
from modules.settings.account_backend import get_user_by_username


@dataclass
class RecentActivity:
    gesture_name: str
    translated_text: str
    confidence: float
    timestamp: datetime


@dataclass
class DashboardSummary:
    display_name: str
    email: str
    role: str
    greeting: str
    last_login: Optional[datetime]
    sessions_today: int
    avg_confidence: float
    unique_signs_recognized: int
    camera_status: str
    privacy_mode: str
    history_logging_enabled: bool
    recent_activity: list[RecentActivity]


# Cache for camera status to avoid opening VideoCapture repeatedly
_cached_camera_status: Optional[str] = None
_last_camera_check: float = 0.0

def get_camera_status(force_check: bool = False) -> str:
    global _cached_camera_status, _last_camera_check
    import time

    # Check at most once every 60 seconds unless forced
    current_time = time.time()
    if not force_check and _cached_camera_status is not None and (current_time - _last_camera_check) < 60:
        return _cached_camera_status

    if not config.webcam_enabled:
        _cached_camera_status = "Disabled"
        _last_camera_check = current_time
        return _cached_camera_status

    try:
        # Check standard config index or fallback to 0
        source = config.get("webcam.camera_source", "builtin")
        idx = 1 if source == "external" else 0
        
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap is not None and cap.isOpened():
            _cached_camera_status = "Ready"
            cap.release()
        else:
            _cached_camera_status = "Not Available"
    except Exception:
        _cached_camera_status = "Error"
        
    _last_camera_check = current_time
    return _cached_camera_status


def _get_time_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 18:
        return "Good afternoon"
    else:
        return "Good evening"


def get_dashboard_summary(username: str) -> Optional[DashboardSummary]:
    user_info = get_user_by_username(username)
    if not user_info:
        return None

    user_id = user_info.get("id")
    display_name = user_info.get("name") or username
    email = user_info.get("email") or ""
    role = "User" # hardcoded role as per DB schema limitation (no role column)
    
    greeting = _get_time_greeting()
    
    # 1. Last Login
    # get_events_for_user hashes the user_id internally
    events = get_events_for_user(str(user_id), limit=10)
    last_login_dt = None
    for e in events:
        if e["event"] == "LOGIN_SUCCESS":
            try:
                last_login_dt = datetime.fromisoformat(e["timestamp"])
            except ValueError:
                pass
            break
            
    print(f"[DEBUG] get_dashboard_summary called for username='{username}' (user_id={user_id})")
    
    # 2. History Analytics
    history = get_history(user_id)
    print(f"[DEBUG] get_history({user_id}) returned {len(history)} rows.")
    if history:
        print(f"[DEBUG] First row: {history[0]}")
    
    sessions_today = 0
    unique_signs = set()
    total_confidence = 0.0
    count_confidence = 0
    recent_activity = []
    
    today_date = datetime.now().date()
    print(f"[DEBUG] today_date={today_date}")
    
    last_dt = None
    
    for row in history:
        # Parse timestamp
        try:
            dt = datetime.fromisoformat(row["logged_at"])
        except ValueError as e:
            print(f"[DEBUG] Failed to parse timestamp {row.get('logged_at')}: {e}")
            continue
            
        # Count unique signs (history deciphers it transparently)
        gesture = row.get("gesture")
        if gesture:
            unique_signs.add(gesture)
            
        # Confidence
        conf = row.get("confidence")
        if conf is not None:
            total_confidence += float(conf)
            count_confidence += 1
            
        # Session logic for today
        if dt.date() == today_date:
            if last_dt is None:
                sessions_today += 1
                last_dt = dt
                print(f"[DEBUG] First session of today started at {dt}")
            else:
                # Compare gap (history is ordered DESC, so dt is older than last_dt)
                gap = (last_dt - dt).total_seconds()
                if gap > 15 * 60: # 15 minutes
                    sessions_today += 1
                    print(f"[DEBUG] New session counted! Gap: {gap}s. dt={dt}, last_dt={last_dt}")
                last_dt = dt
                
        # Recent activity (first 5)
        if len(recent_activity) < 5:
            trans = row.get("translated_text") or ""
            act = RecentActivity(
                gesture_name=gesture or "Unknown",
                translated_text=trans,
                confidence=float(conf) if conf is not None else 0.0,
                timestamp=dt
            )
            recent_activity.append(act)

    print(f"[DEBUG] Final sessions_today={sessions_today}, recent_activity len={len(recent_activity)}")

    avg_confidence = (total_confidence / count_confidence * 100) if count_confidence > 0 else 0.0
    
    # 3. System Status
    cam_status = get_camera_status()
    privacy_mode = "Local Only" if config.get("privacy.local_only_processing", True) else "Cloud Enabled"
    history_log_enabled = config.get("privacy.gesture_history_log", False)
    
    return DashboardSummary(
        display_name=display_name,
        email=email,
        role=role,
        greeting=greeting,
        last_login=last_login_dt,
        sessions_today=sessions_today,
        avg_confidence=avg_confidence,
        unique_signs_recognized=len(unique_signs),
        camera_status=cam_status,
        privacy_mode=privacy_mode,
        history_logging_enabled=history_log_enabled,
        recent_activity=recent_activity
    )

def search_dashboard(query: str, username: str) -> list[dict]:
    """
    Searches across navigation and history. 
    Returns a list of dicts: {"title": str, "type": str, "action": str, "desc": str}
    Priority: Exact Nav > Exact Gesture > Partial Gesture > History Match
    """
    query = query.lower().strip()
    if not query:
        return []
        
    results = []
    
    # 1. Navigation (hardcoded map)
    nav_items = [
        ("Dashboard", "dashboard", "Overview and statistics"),
        ("Gesture Translator", "gesture", "Real-time sign language translation"),
        ("Settings", "settings", "Application configuration"),
        ("Sign Dictionary", "dictionary", "ASL gesture library"),
        ("Gesture History", "history", "Past translation sessions"),
    ]
    
    for title, action, desc in nav_items:
        if query == title.lower():
            results.append({"title": title, "type": "Navigation", "action": action, "desc": desc, "score": 100})
        elif query in title.lower():
            results.append({"title": title, "type": "Navigation", "action": action, "desc": desc, "score": 80})

    # 2. History & Gestures
    user_info = get_user_by_username(username)
    if user_info:
        history = get_history(user_info.get("id"))
        
        # Build distinct gestures from history
        gestures_seen = set()
        
        for row in history:
            g = row.get("gesture") or ""
            t = row.get("translated_text") or ""
            d = row.get("logged_at", "")[:10]
            
            if not g and not t:
                continue
                
            if g and g not in gestures_seen:
                if query == g.lower():
                    results.append({"title": f"Sign: {g}", "type": "Gesture", "action": "history", "desc": "Found in your recognized signs", "score": 90})
                    gestures_seen.add(g)
                elif query in g.lower():
                    results.append({"title": f"Sign: {g}", "type": "Gesture", "action": "history", "desc": "Found in your recognized signs", "score": 70})
                    gestures_seen.add(g)
                    
            if query in t.lower():
                # Avoid flooding with history
                if len([r for r in results if r["type"] == "History"]) < 3:
                    results.append({"title": f'"{t}"', "type": "History", "action": "history", "desc": f"Translated on {d}", "score": 50})
                    
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:8] # Max 8 results
