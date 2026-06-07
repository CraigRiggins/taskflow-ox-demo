"""
Email notification service.

Stub implementation — the actual email sending hasn't been built yet.
The validation logic here is duplicated from user_service.py and
models/user.py — three places now enforce the same email format rules.
"""

import re
import os
import json
from datetime import datetime


EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

# would be loaded from environment in production
SMTP_HOST     = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT     = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER     = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
FROM_ADDRESS  = os.environ.get("FROM_EMAIL", "noreply@taskflow.example.com")

# in-memory log of "sent" emails for testing
_sent_emails: list[dict] = []


def send_task_notification(
    recipient_id: int,
    task_id:      int,
    task_title:   str,
    event:        str,
):
    """
    Sends a task notification email to a user.
    Currently logs to memory instead of sending — SMTP not configured.
    """
    from app.db import queries
    user = queries.get_user_by_id(recipient_id)
    if not user:
        return

    email = user["email"]

    # email validation — third copy of this logic in the codebase
    if not EMAIL_PATTERN.match(email):
        print(f"[email] invalid recipient address: {email}")
        return

    subject, body = _build_task_notification(
        user["name"], task_id, task_title, event
    )

    _log_email(email, subject, body)


def send_welcome_email(user_id: int):
    """Sends a welcome email to a new user."""
    from app.db import queries
    user = queries.get_user_by_id(user_id)
    if not user:
        return

    email = user["email"]
    if not EMAIL_PATTERN.match(email):
        return

    subject = "Welcome to Taskflow!"
    body    = (
        f"Hi {user['name']},\n\n"
        f"Welcome to Taskflow. Your account is ready.\n\n"
        f"Get started by creating your first task.\n\n"
        f"— The Taskflow Team"
    )
    _log_email(email, subject, body)


def send_password_reset(email: str, reset_token: str):
    """Sends a password reset link."""
    if not EMAIL_PATTERN.match(email):
        raise ValueError(f"Invalid email: {email}")

    subject = "Reset your Taskflow password"
    body    = (
        f"You requested a password reset.\n\n"
        f"Use this token to reset your password: {reset_token}\n\n"
        f"This token expires in 1 hour.\n\n"
        f"If you did not request this, ignore this email."
    )
    _log_email(email, subject, body)


def get_sent_emails() -> list[dict]:
    """Returns the in-memory email log — for testing only."""
    return list(_sent_emails)


def clear_sent_emails():
    """Clears the email log — for testing only."""
    _sent_emails.clear()


def _build_task_notification(
    name:       str,
    task_id:    int,
    task_title: str,
    event:      str,
) -> tuple[str, str]:
    """Builds the subject and body for a task notification."""
    messages = {
        "assigned":  (
            f"You have been assigned to task: {task_title}",
            f"Hi {name},\n\nYou have been assigned to task #{task_id}: {task_title}.",
        ),
        "completed": (
            f"Task completed: {task_title}",
            f"Hi {name},\n\nTask #{task_id} '{task_title}' has been marked as done.",
        ),
        "commented": (
            f"New comment on: {task_title}",
            f"Hi {name},\n\nSomeone commented on task #{task_id}: {task_title}.",
        ),
    }
    return messages.get(event, (
        f"Task update: {task_title}",
        f"Hi {name},\n\nTask #{task_id} '{task_title}' has been updated.",
    ))


def _log_email(to: str, subject: str, body: str):
    """Logs an email to the in-memory store instead of sending."""
    _sent_emails.append({
        "to":         to,
        "subject":    subject,
        "body":       body,
        "sent_at":    datetime.utcnow().isoformat(),
    })
    print(f"[email] would send to={to!r} subject={subject!r}")
