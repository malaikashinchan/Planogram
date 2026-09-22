"""
Email service using Gmail SMTP.

Sends real verification and password-reset emails via TLS.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.app.core.config import settings


def _send_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Sends an email via Gmail SMTP with TLS.
    Also logs to console for development visibility.
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())

        print(f"✅ Email sent to {to_email}: {subject}")

    except Exception as exc:
        # Log but don't crash the API — email failure shouldn't block registration
        print(f"❌ Failed to send email to {to_email}: {exc}")


def send_verification_email(email: str, token: str) -> None:
    """Sends the email-verification link."""

    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    subject = "Verify your email — Planogram Compliance"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 30px;">
        <h2 style="color: #1a1a2e;">Welcome to Planogram Compliance!</h2>
        <p>Please verify your email address by clicking the button below:</p>
        <a href="{verification_url}"
           style="display: inline-block; background-color: #4361ee; color: white;
                  padding: 12px 28px; text-decoration: none; border-radius: 6px;
                  font-weight: bold; margin: 20px 0;">
            Verify Email
        </a>
        <p style="color: #666; font-size: 13px;">
            Or copy this link into your browser:<br>
            <code>{verification_url}</code>
        </p>
        <p style="color: #999; font-size: 12px;">This link expires in 24 hours.</p>
    </div>
    """

    _send_email(email, subject, html_body)


def send_password_reset_email(email: str, token: str) -> None:
    """Sends the password-reset link."""

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    subject = "Reset your password — Planogram Compliance"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 30px;">
        <h2 style="color: #1a1a2e;">Password Reset Request</h2>
        <p>Click the button below to reset your password:</p>
        <a href="{reset_url}"
           style="display: inline-block; background-color: #e63946; color: white;
                  padding: 12px 28px; text-decoration: none; border-radius: 6px;
                  font-weight: bold; margin: 20px 0;">
            Reset Password
        </a>
        <p style="color: #666; font-size: 13px;">
            Or copy this link into your browser:<br>
            <code>{reset_url}</code>
        </p>
        <p style="color: #999; font-size: 12px;">
            This link expires in 1 hour. If you didn't request this, ignore this email.
        </p>
    </div>
    """

    _send_email(email, subject, html_body)
