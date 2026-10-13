from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from accounts.models import User

EMAIL_SUBJECTS = {
    "password_recovery": "Change your Chobe password",
    "welcome": "Welcome to Chobe",
}


def send_account_email(template: str, user: User, context: dict | None = None) -> int:
    subject = EMAIL_SUBJECTS[template]
    context = {"user": user, **(context or {}), "subject": subject}
    email = EmailMessage(
        subject=subject,
        body=render_to_string(f"accounts/emails/{template}.html", context),
        to=[user.email],
    )
    email.content_subtype = "html"
    return email.send()
