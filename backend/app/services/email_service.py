import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def _send_email_sync(to_email: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.info("Email delivery skipped because SMTP is not configured")
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls(context=ssl.create_default_context())
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)


async def send_password_reset_email(to_email: str, reset_token: str) -> None:
    reset_url = f"{settings.PASSWORD_RESET_URL_BASE}?token={reset_token}"
    body = (
        "A password reset was requested for your HealthPatch account.\n\n"
        f"Reset your password here: {reset_url}\n\n"
        f"This link expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes. "
        "If you did not request this, you can ignore this email."
    )
    await asyncio.to_thread(_send_email_sync, to_email, "Reset your HealthPatch password", body)
