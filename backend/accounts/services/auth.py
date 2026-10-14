from django.contrib.auth.password_validation import password_changed
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from accounts.models import User
from accounts.tasks.email import send_password_changed_email, send_welcome_email


def register_account(values):
    values = values.copy()
    values.pop("accept_terms")
    try:
        with transaction.atomic():
            user = User.objects.create_user(**values)
            send_welcome_email.enqueue(user.pk)
            return user
    except IntegrityError as error:
        raise ValidationError(
            {"non_field_errors": ["Username or email is already in use."]}
        ) from error


@transaction.atomic
def reset_password(user, password):
    old_password = user.password
    user.set_password(password)
    if not User.objects.filter(
        pk=user.pk,
        password=old_password,
        email=user.email,
        last_login=user.last_login,
        is_active=True,
    ).update(password=user.password):
        raise ValidationError(
            "This password reset link has already been used. Request a new link."
        )
    password_changed(password, user)
    send_password_changed_email.enqueue(user.pk)
    return user
