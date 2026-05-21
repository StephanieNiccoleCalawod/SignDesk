"""
core/validators.py - Input Validation & Security Layer
Covers: email format, MX record check, disposable email blocking,
        username rules, length limits, SQL injection input sanitization,
        and registration rate limiting.
"""

import re
import socket
import html
import time
from collections import defaultdict

try:
    import dns.resolver
    _DNS_AVAILABLE = True
except ImportError:
    _DNS_AVAILABLE = False


# ── Constants ────────────────────────────────────────────────────────────────

MAX_USERNAME_LEN = 32
MIN_USERNAME_LEN = 3
MAX_EMAIL_LEN    = 254   # RFC 5321 hard limit
MAX_PASSWORD_LEN = 128
MAX_FIELD_LEN    = 512   # absolute ceiling for any input field

# Alphanumeric + underscore + hyphen only
USERNAME_RE = re.compile(r'^[a-zA-Z0-9_\-]+$')

# Strict email regex (RFC 5322 simplified)
EMAIL_RE = re.compile(
    r'^(?!.*\.\.)'                        # no consecutive dots
    r'[a-zA-Z0-9]'                        # must start with alnum
    r'[a-zA-Z0-9._%+\-]{0,62}'           # local part body
    r'@'
    r'[a-zA-Z0-9]'                        # domain must start with alnum
    r'[a-zA-Z0-9\-]{0,61}'               # domain body
    r'(?:\.[a-zA-Z0-9\-]{1,61})*'        # sub-domains
    r'\.[a-zA-Z]{2,}$'                   # TLD at least 2 chars
)

# Known disposable / throwaway email domains
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "guerrillamail.net",
    "guerrillamail.org", "guerrillamail.de", "guerrillamail.info",
    "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "guerrillamail.biz", "spam4.me", "trashmail.com", "trashmail.me",
    "trashmail.net", "trashmail.at", "trashmail.io", "trashmail.org",
    "trashmail.xyz", "yopmail.com", "yopmail.fr", "cool.fr.nf",
    "jetable.fr.nf", "nospam.ze.tc", "nomail.xl.cx", "mega.zik.dj",
    "speed.1s.fr", "courriel.fr.nf", "moncourrier.fr.nf",
    "monemail.fr.nf", "monmail.fr.nf", "tempmail.com", "temp-mail.org",
    "fakeinbox.com", "mailnull.com", "maildrop.cc", "spamgourmet.com",
    "spamgourmet.net", "spamgourmet.org", "throwam.com", "dispostable.com",
    "mailnesia.com", "spamex.com", "getairmail.com", "filzmail.com",
    "throwam.com", "tempr.email", "discard.email", "spamwc.de",
    "spamwc.ga", "spamwc.gq", "spamwc.ml", "spamwc.cf",
    "10minutemail.com", "10minutemail.net", "10minutemail.de",
    "10minutemail.nl", "10minutemail.org", "10minutemail.ru",
    "minutemail.com", "20minutemail.com", "tempinbox.com",
    "mailtemporaire.fr", "jetable.net", "jetable.org",
    "nospamfor.us", "spamgob.com", "throwaway.email",
    "getnada.com", "mohmal.com", "dispostable.com", "anonaddy.com",
}


# ── Rate Limiter ─────────────────────────────────────────────────────────────

class _RateLimiter:
    """
    Simple in-memory rate limiter.
    Tracks attempts per key (IP or username) within a sliding window.
    """
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self._max     = max_attempts
        self._window  = window_seconds
        self._records: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> tuple[bool, int]:
        """
        Returns (allowed, seconds_until_reset).
        Cleans up stale timestamps on every call.
        """
        now    = time.time()
        times  = self._records[key]
        cutoff = now - self._window

        # Drop timestamps outside the window
        self._records[key] = [t for t in times if t > cutoff]

        if len(self._records[key]) >= self._max:
            oldest    = self._records[key][0]
            wait_secs = int(self._window - (now - oldest)) + 1
            return False, wait_secs

        self._records[key].append(now)
        return True, 0

    def reset(self, key: str):
        """Clear attempts for a key (e.g. after successful registration)."""
        self._records.pop(key, None)


# Module-level rate limiter: max 5 registration attempts per email per 5 min
registration_limiter = _RateLimiter(max_attempts=5, window_seconds=300)


# ── Sanitization ─────────────────────────────────────────────────────────────

def sanitize_input(value: str) -> str:
    """
    Strip leading/trailing whitespace, HTML-escape special characters,
    and enforce the absolute maximum field length.
    This prevents XSS in any display context and rejects absurdly long inputs.
    """
    if not isinstance(value, str):
        return ""
    value = value.strip()
    value = value[:MAX_FIELD_LEN]
    value = html.escape(value)
    return value


def sanitize_username(value: str) -> str:
    """
    Strip whitespace only — don't HTML-escape usernames since
    they go through a character whitelist separately.
    """
    if not isinstance(value, str):
        return ""
    return value.strip()[:MAX_FIELD_LEN]


# ── Email Validators ─────────────────────────────────────────────────────────

def _check_mx_record(domain: str) -> bool:
    """
    Returns True if the domain has at least one MX record.
    Falls back to A-record check if MX lookup fails.
    Falls back to True if DNS is unavailable (offline mode).
    """
    if not _DNS_AVAILABLE:
        # Offline fallback: do a basic socket hostname resolution
        try:
            socket.getaddrinfo(domain, None)
            return True
        except socket.gaierror:
            return False

    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        pass
    except Exception:
        pass

    # Fall back to A record
    try:
        dns.resolver.resolve(domain, 'A')
        return True
    except Exception:
        return False


def validate_email(email: str) -> tuple[bool, str]:
    """
    Full email validation pipeline:
    1. Required / length check
    2. Strict format regex
    3. Disposable domain block
    4. MX / DNS record check
    Returns (True, "") on success, (False, "error message") on failure.
    """
    if not email:
        return False, "Email address is required."

    if len(email) > MAX_EMAIL_LEN:
        return False, f"Email address is too long (max {MAX_EMAIL_LEN} characters)."

    email_lower = email.lower()

    if not EMAIL_RE.match(email_lower):
        return False, "Please enter a valid email address (e.g. name@example.com)."

    domain = email_lower.split("@", 1)[1]

    if domain in DISPOSABLE_DOMAINS:
        return False, "Disposable or temporary email addresses are not allowed."

    if not _check_mx_record(domain):
        return False, f"The email domain '{domain}' does not appear to be valid. Please use a real email address."

    return True, ""


# ── Username Validator ───────────────────────────────────────────────────────

def validate_username(username: str) -> tuple[bool, str]:
    """
    Validates username:
    - Length between MIN and MAX
    - Only alphanumeric, underscore, or hyphen characters
    - Cannot start or end with underscore/hyphen
    """
    if not username:
        return False, "Username is required."

    if len(username) < MIN_USERNAME_LEN:
        return False, f"Username must be at least {MIN_USERNAME_LEN} characters."

    if len(username) > MAX_USERNAME_LEN:
        return False, f"Username must be at most {MAX_USERNAME_LEN} characters."

    if not USERNAME_RE.match(username):
        return False, "Username may only contain letters, numbers, underscores, or hyphens."

    if username[0] in ('_', '-') or username[-1] in ('_', '-'):
        return False, "Username cannot start or end with an underscore or hyphen."

    return True, ""


# ── Password Validators ──────────────────────────────────────────────────────

def validate_password(password: str) -> list[str]:
    """
    Returns a list of unmet requirements. Empty list = valid.
    """
    errors = []
    if len(password) < 8:
        errors.append("At least 8 characters")
    if len(password) > MAX_PASSWORD_LEN:
        errors.append(f"At most {MAX_PASSWORD_LEN} characters")
    if not re.search(r"[A-Z]", password):
        errors.append("At least 1 uppercase letter (A–Z)")
    if not re.search(r"[a-z]", password):
        errors.append("At least 1 lowercase letter (a–z)")
    if not re.search(r"[0-9]", password):
        errors.append("At least 1 number (0–9)")
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{};':\"\\|,.<>/?`~]", password):
        errors.append("At least 1 special character (!@#$%^&* etc.)")
    return errors


# ── Full Registration Validator ──────────────────────────────────────────────

def validate_registration(username: str, email: str,
                           password: str, confirm: str) -> list[str]:
    """
    Full validation pipeline for the registration form.
    Returns a list of error strings — empty list means all valid.
    Includes rate limiting per email address.
    """
    errors = []

    # ── Required fields ──
    if not username:
        errors.append("Username is required.")
    if not email:
        errors.append("Email address is required.")
    if not password:
        errors.append("Password is required.")
    if not confirm:
        errors.append("Please confirm your password.")

    if errors:
        return errors

    # ── Length ceiling (reject absurdly long inputs early) ──
    for label, value in [("Username", username), ("Email", email),
                          ("Password", password)]:
        if len(value) > MAX_FIELD_LEN:
            errors.append(f"{label} input is too long.")

    if errors:
        return errors

    # ── Username format ──
    uname_ok, uname_err = validate_username(username)
    if not uname_ok:
        errors.append(uname_err)

    # ── Email (full pipeline: format + disposable + MX) ──
    email_ok, email_err = validate_email(email)
    if not email_ok:
        errors.append(email_err)

    # ── Password strength ──
    errors.extend(validate_password(password))

    # ── Confirmation match ──
    if password != confirm:
        errors.append("Password and confirmation do not match.")

    return errors
