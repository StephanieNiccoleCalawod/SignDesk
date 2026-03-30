"""
service.py - Authentication Logic
Handles user login and registration with MSSQL via pyodbc and bcrypt.
Includes email verification support for account creation.
"""

import re
import bcrypt
from core.database import get_connection


# ──────────────────────────────────────────────────────────────
# VALIDATION
# ──────────────────────────────────────────────────────────────

def validate_email(email: str) -> tuple[bool, str]:
    """
    Validates email format.
    Returns (True, "") if valid, (False, "error message") if not.
    """
    if not email:
        return False, "Email address is required."

    # Basic email format check
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Please enter a valid email address."

    return True, ""


def validate_password(password: str) -> list[str]:
    """
    Checks password against all character requirements.
    Returns a list of error strings — empty list means password is valid.
    """
    errors = []

    if len(password) < 8:
        errors.append("At least 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("At least 1 uppercase letter (A–Z)")
    if not re.search(r"[a-z]", password):
        errors.append("At least 1 lowercase letter (a–z)")
    if not re.search(r"[0-9]", password):
        errors.append("At least 1 number (0–9)")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        errors.append("At least 1 special character (!@#$%^&* etc.)")

    return errors


def validate_registration(username: str, email: str, password: str, confirm: str) -> list[str]:
    """
    Full validation of all registration fields.
    Returns a list of error strings — empty means all fields are valid.
    """
    errors = []

    # Required fields
    if not username:
        errors.append("Username is required.")
    if not email:
        errors.append("Email address is required.")
    if not password:
        errors.append("Password is required.")
    if not confirm:
        errors.append("Please confirm your password.")

    if errors:
        return errors  # Stop early if required fields missing

    # Email format
    email_valid, email_err = validate_email(email)
    if not email_valid:
        errors.append(email_err)

    # Password strength
    pwd_errors = validate_password(password)
    errors.extend(pwd_errors)

    # Password confirmation
    if password != confirm:
        errors.append("Password and confirmation password do not match.")

    return errors


# ──────────────────────────────────────────────────────────────
# DUPLICATE CHECKS
# ──────────────────────────────────────────────────────────────

def check_duplicate_username(username: str) -> tuple[bool, str]:
    """
    Returns (True, "error") if username already exists.
    Returns (False, "") if username is available.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM dbo.users WHERE username = ?", (username,))
        exists = cursor.fetchone() is not None
        conn.close()

        if exists:
            return True, "This username already exists. Please choose another username."
        return False, ""

    except Exception as e:
        return True, f"Database error: {str(e)}"


def check_duplicate_email(email: str) -> tuple[bool, str]:
    """
    Returns (True, "error") if email already exists in the database.
    Returns (False, "") if email is available.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM dbo.users WHERE email = ?", (email,))
        exists = cursor.fetchone() is not None
        conn.close()

        if exists:
            return True, "An account with this email already exists."
        return False, ""

    except Exception as e:
        return True, f"Database error: {str(e)}"


# ──────────────────────────────────────────────────────────────
# AUTH FUNCTIONS
# ──────────────────────────────────────────────────────────────

def login_user(username: str, password: str) -> tuple[bool, str]:
    """
    Validates user credentials against the database.
    Returns (True, "Login successful") or (False, "error message").
    """
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT password_hash
            FROM   dbo.users
            WHERE  username = ?
            """,
            (username,)
        )

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return False, "Incorrect username or password. Please try again."

        stored_hash = row[0].encode("utf-8")
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            return True, "Login successful."
        else:
            return False, "Incorrect username or password. Please try again."

    except Exception as e:
        return False, f"Database error: {str(e)}"


def register_user(username: str, email: str, password: str) -> str:
    """
    Creates a new user account in the database AFTER email verification.
    This function should only be called after OTP is verified.

    The account is stored with:
    - username
    - email
    - password_hash (bcrypt)
    - email_verified = 1

    Returns a result message string (prefixed with ERROR: on failure).
    """
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        # Final duplicate checks (safety — may have changed since form submission)
        cursor.execute("SELECT 1 FROM dbo.users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return "ERROR: This username already exists. Please choose another username."

        cursor.execute("SELECT 1 FROM dbo.users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return "ERROR: An account with this email already exists."

        # Hash the password securely with bcrypt
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        # Insert new user with email_verified = 1 (verified via OTP)
        cursor.execute(
            """
            INSERT INTO dbo.users (username, email, password_hash, email_verified)
            VALUES (?, ?, ?, 1)
            """,
            (username, email, password_hash)
        )

        conn.commit()
        conn.close()

        return "Account created successfully! Your email has been verified. You can now log in."

    except Exception as e:
        return f"ERROR: {str(e)}"
