from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.tasks import task
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.emails import send_account_email
from accounts.models import User


@task
def send_welcome_email(user_id: int) -> int:
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None or not user.email:
        return 0
    return send_account_email("welcome", user)


@task
def send_password_changed_email(user_id: int) -> int:
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None or not user.email:
        return 0
    return send_account_email(
        "password_changed",
        user,
        {"frontend_url": settings.FRONTEND_URL.rstrip("/")},
    )


@task
def send_password_reset_email(email: str) -> int:
    sent = 0
    for user in PasswordResetForm().get_users(email):
        sent += send_account_email(
            "password_reset",
            user,
            {
                "frontend_url": settings.FRONTEND_URL.rstrip("/"),
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": default_token_generator.make_token(user),
                "minutes": settings.PASSWORD_RESET_TIMEOUT // 60,
            },
        )
    return sent
