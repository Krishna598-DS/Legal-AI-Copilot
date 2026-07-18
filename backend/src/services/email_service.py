"""Email delivery — SMTP when configured, otherwise console/log backend."""

import smtplib
from email.message import EmailMessage

from src.config import get_settings
from src.logging_config import logger

settings = get_settings()


def send_email(to_email: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.SMTP_HOST:
        logger.info(
            "EMAIL[console] to=%s subject=%s\n%s", to_email, subject, body
        )
        # Also write to a file for local testing
        import os

        os.makedirs(settings.LOG_DIR, exist_ok=True)
        path = os.path.join(settings.LOG_DIR, "emails.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n---\nTO: {to_email}\nSUBJECT: {subject}\n{body}\n")
        return

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(
        settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT
    ) as smtp:
        if settings.SMTP_TLS:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)
    logger.info("EMAIL[smtp] to=%s subject=%s", to_email, subject)


def send_verification_email(to_email: str, token: str) -> None:
    settings = get_settings()
    link = f"{settings.APP_BASE_URL}/auth/verify-email?token={token}"
    send_email(
        to_email,
        "Verify your AI Legal Copilot account",
        (
            f"Welcome to AI Legal Copilot!\n\nVerify your email by opening this link:\n{link}\n\n"
            f"Or use token: {token}\n\n"
            "If you did not create an account, ignore this message."
        ),
    )


def send_password_reset_email(to_email: str, token: str) -> None:
    settings = get_settings()
    link = f"{settings.FRONTEND_URL}/?reset_token={token}"
    send_email(
        to_email,
        "Reset your AI Legal Copilot password"
        (
            f"Reset your password using this link:\n{link}\n\n"
            f"Or use token: {token}\n\n"
            "If you did not request a reset, ignore this message."
        ),
    )
