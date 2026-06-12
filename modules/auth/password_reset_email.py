

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.email_config import SMTP_EMAIL, SMTP_APP_PASSWORD, SMTP_HOST, SMTP_PORT
from modules.auth.otp_manager import PASSWORD_RESET_OTP_EXPIRY_MINUTES


# ──────────────────────────────────────────────────────────────
# PASSWORD RESET EMAIL
# ──────────────────────────────────────────────────────────────

def send_password_reset_email(to_email: str, otp_code: str) -> tuple[bool, str]:
    """
    Sends a password reset OTP email via Gmail SMTP.

    Returns:
        (True, "Email sent successfully") — email was sent.
        (False, "error message") — sending failed.
    """
    expiry = PASSWORD_RESET_OTP_EXPIRY_MINUTES

    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"SignDesk <{SMTP_EMAIL}>"
        msg["To"]      = to_email
        msg["Subject"] = "Your SignDesk Verification Code"

        text_body = (
            f"Your verification code is: {otp_code}\n\n"
            f"This code expires in {expiry} minutes.\n"
            f"If you did not request this, ignore this email."
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
                        <p style="color:#1A1A2E; font-size:16px; margin:0 0 4px;">
                            Password Reset Request
                        </p>
                        <p style="color:#6B7280; font-size:13px; margin:0 0 16px;">
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
                            This code expires in <strong>{expiry} minutes</strong>.<br>
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

        return True, "Password reset email sent successfully."

    except smtplib.SMTPAuthenticationError:
        return False, (
            "Email authentication failed. Please check SMTP credentials in email_config.py.\n"
            "Make sure you are using a Gmail App Password (not your regular password)."
        )
    except smtplib.SMTPRecipientsRefused:
        return False, "The email address was rejected. Please enter a valid email."
    except smtplib.SMTPException as e:
        print(f"[email] SMTP error sending password reset: {e}")
        return False, "Failed to send email. Please try again later."
    except TimeoutError:
        return False, "Email sending timed out. Please check your internet connection."
    except Exception as e:
        print(f"[email] Unexpected error sending password reset: {e}")
        return False, "Failed to send email. Please try again later."
