"""
cooldown_persistence.py - Resend Cooldown State Persistence
Saves / loads / clears a 10-minute cooldown timestamp to a local JSON file
so the countdown survives app restarts.  Fully offline — no network needed.
"""

import json
import os
from datetime import datetime

# Same base-directory pattern used by core/config.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOLDOWN_PATH = os.path.join(BASE_DIR, "cooldown_state.json")


def save_cooldown(email: str, expiry: datetime) -> None:
    """
    Persist the cooldown expiry for *email* to cooldown_state.json.

    Parameters
    ----------
    email : str
        The email address the cooldown belongs to.
    expiry : datetime
        The exact moment the cooldown expires (UTC-naive, local time).
    """
    data = {
        "email": email,
        "expires_at": expiry.isoformat(),
    }
    try:
        with open(COOLDOWN_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[cooldown] Failed to save cooldown: {e}")


def load_cooldown(email: str) -> int:
    """
    Return the number of seconds remaining on an active cooldown for *email*.

    Returns 0 if:
    - The file does not exist
    - The stored email does not match
    - The cooldown has already expired
    - Any read / parse error occurs
    """
    if not os.path.exists(COOLDOWN_PATH):
        return 0
    try:
        with open(COOLDOWN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("email") != email:
            return 0

        expiry = datetime.fromisoformat(data["expires_at"])
        remaining = (expiry - datetime.now()).total_seconds()

        if remaining <= 0:
            # Expired — clean up automatically
            clear_cooldown()
            return 0

        return int(remaining)

    except Exception:
        return 0


def clear_cooldown() -> None:
    """Delete cooldown_state.json.  Silently does nothing if the file is absent."""
    try:
        if os.path.exists(COOLDOWN_PATH):
            os.remove(COOLDOWN_PATH)
    except Exception as e:
        print(f"[cooldown] Failed to clear cooldown file: {e}")
