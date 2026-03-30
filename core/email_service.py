"""
email_service.py - Email Sending Utility
Sends verification emails via Gmail SMTP using Python's built-in smtplib.
Email MUST be properly configured — no fallback to on-screen display.
No extra dependencies required.
"""

import smtplib
import secrets
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

from core.email_config import (
    SMTP_EMAIL, SMTP_APP_PASSWORD, SMTP_HOST, SMTP_PORT,
    OTP_LENGTH, OTP_EXPIRY_MINUTES, OTP_RESEND_COOLDOWN, OTP_MAX_RESENDS,
    OTP_MAX_VERIFY_ATTEMPTS
)


# ──────────────────────────────────────────────────────────────
# OTP GENERATION
# ──────────────────────────────────────────────────────────────

def generate_otp() -> str:
    """Generates a cryptographically secure random 6-digit verification code."""
    lower = 10 ** (OTP_LENGTH - 1)
    upper = 10 ** OTP_LENGTH - 1
    return str(secrets.randbelow(upper - lower + 1) + lower)


def get_otp_expiry() -> datetime:
    """Returns the expiry timestamp for a newly generated OTP."""
    return datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)


def is_otp_expired(expiry_time: datetime) -> bool:
    """Returns True if the OTP has expired."""
    return datetime.now() > expiry_time


# ──────────────────────────────────────────────────────────────
# EMAIL SENDING
# ──────────────────────────────────────────────────────────────

def send_verification_email(to_email: str, otp_code: str) -> tuple[bool, str]:
    """
    Sends a verification email with the OTP code via SMTP.

    SMTP credentials MUST be configured in email_config.py.
    If sending fails for any reason, returns (False, "error message").
    The OTP is NEVER displayed on screen — it is only delivered via email.

    Returns:
        (True, "Email sent successfully") — email was sent.
        (False, "error message") — sending failed.
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"SignDesk <{SMTP_EMAIL}>"
        msg["To"]      = to_email
        msg["Subject"] = f"SignDesk — Your verification code is {otp_code}"

        text_body = (
            f"Your SignDesk verification code is: {otp_code}\n\n"
            f"This code expires in {OTP_EXPIRY_MINUTES} minutes.\n"
            f"If you did not request this, please ignore this email."
        )

        html_body = f"""
        <html>
        <body style="margin:0; padding:0; background-color:#F0F4FF; font-family:'Trebuchet MS',sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px; margin:32px auto;">
                <tr>
                    <td style="background:#1A237E; padding:28px 32px; border-radius:12px 12px 0 0; text-align:center;">
                        <span style="font-size:36px;">🤟</span><br>
                        <span style="color:#FFFFFF; font-size:22px; font-weight:bold; font-family:Georgia,serif;">
                            SignDesk
                        </span><br>
                        <span style="color:#00BCD4; font-size:13px; font-style:italic;">
                            Sign Language to Speech
                        </span>
                    </td>
                </tr>
                <tr>
                    <td style="background:#FFFFFF; padding:32px 32px 24px; border-radius:0 0 12px 12px;
                               border:1px solid #C5CAE9; border-top:none;">
                        <p style="color:#1A1A2E; font-size:16px; margin:0 0 8px;">
                            Your verification code is:
                        </p>
                        <div style="background:#EEF2FF; border:2px solid #C5CAE9; border-radius:10px;
                                    padding:18px; text-align:center; margin:16px 0;">
                            <span style="font-size:36px; font-weight:bold; letter-spacing:10px;
                                         color:#1A237E; font-family:'Courier New',monospace;">
                                {otp_code}
                            </span>
                        </div>
                        <p style="color:#4A5568; font-size:13px; margin:16px 0 0;">
                            This code expires in <strong>{OTP_EXPIRY_MINUTES} minutes</strong>.<br>
                            If you did not request this, you can safely ignore this email.
                        </p>
                    </td>
                </tr>
                <tr>
                    <td style="padding:16px; text-align:center;">
                        <span style="color:#A0AEC0; font-size:11px;">
                            &copy; 2025 SignDesk Project &bull; All rights reserved
                        </span>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

        return True, "Verification email sent successfully."

    except smtplib.SMTPAuthenticationError:
        return False, (
            "Email authentication failed. Please check SMTP credentials in email_config.py.\n"
            "Make sure you are using a Gmail App Password (not your regular password)."
        )
    except smtplib.SMTPRecipientsRefused:
        return False, "The email address was rejected. Please enter a valid email."
    except smtplib.SMTPException as e:
        return False, f"Failed to send email: {str(e)}"
    except TimeoutError:
        return False, "Email sending timed out. Please check your internet connection."
    except Exception as e:
        return False, f"Failed to send verification email: {str(e)}"


# ──────────────────────────────────────────────────────────────
# RESEND TRACKING (in-memory, per session)
# ──────────────────────────────────────────────────────────────

class ResendTracker:
    """
    Tracks resend attempts and enforces cooldown + max resend limits.
    Lives in memory — no database needed for a desktop app.
    """

    def __init__(self):
        self._resend_count = 0
        self._last_resend_time = 0.0

    def can_resend(self) -> tuple[bool, str]:
        if self._resend_count >= OTP_MAX_RESENDS:
            return False, f"Maximum resend limit ({OTP_MAX_RESENDS}) reached. Please try again later."
        elapsed = time.time() - self._last_resend_time
        if elapsed < OTP_RESEND_COOLDOWN:
            remaining = int(OTP_RESEND_COOLDOWN - elapsed)
            return False, f"Please wait {remaining} seconds before requesting a new code."
        return True, ""

    def record_resend(self):
        self._resend_count += 1
        self._last_resend_time = time.time()

    @property
    def resend_count(self) -> int:
        return self._resend_count

    @property
    def cooldown_remaining(self) -> int:
        elapsed = time.time() - self._last_resend_time
        remaining = OTP_RESEND_COOLDOWN - elapsed
        return max(0, int(remaining))

    def reset(self):
        self._resend_count = 0
        self._last_resend_time = 0.0


# ──────────────────────────────────────────────────────────────
# VERIFICATION ATTEMPT TRACKING (brute-force protection)
# ──────────────────────────────────────────────────────────────

class VerificationAttemptTracker:
    """
    Tracks failed OTP entry attempts to prevent brute-force attacks.
    After OTP_MAX_VERIFY_ATTEMPTS wrong entries, the user is locked out
    and must restart the registration process.
    """

    def __init__(self):
        self._attempts = 0

    def record_attempt(self):
        """Records a failed verification attempt."""
        self._attempts += 1

    def can_attempt(self) -> tuple[bool, str]:
        """Returns (True, '') if attempts remain, (False, reason) if locked out."""
        if self._attempts >= OTP_MAX_VERIFY_ATTEMPTS:
            return False, (
                f"Too many failed attempts ({OTP_MAX_VERIFY_ATTEMPTS}/{OTP_MAX_VERIFY_ATTEMPTS}). "
                f"Please restart the registration process."
            )
        return True, ""

    @property
    def attempts_used(self) -> int:
        return self._attempts

    @property
    def attempts_remaining(self) -> int:
        return max(0, OTP_MAX_VERIFY_ATTEMPTS - self._attempts)

    def reset(self):
        self._attempts = 0
