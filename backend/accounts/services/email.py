from django.contrib.auth.models import AbstractUser
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

EMAIL_SUBJECTS = {
    "welcome": "Welcome to Chobe",
    "password_reset": "Reset your Chobe password",
    "password_changed": "Your Chobe password was changed",
}


def send_account_email(
    template: str, user: AbstractUser, context: dict | None = None
) -> int:
    subject = EMAIL_SUBJECTS[template]
    context = {"user": user, **(context or {}), "subject": subject}
    email = EmailMessage(
        subject=subject,
        body=render_to_string(f"accounts/emails/{template}.html", context),
        to=[user.email],
    )
    email.content_subtype = "html"
    return email.send()
