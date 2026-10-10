from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    class Meta(AbstractUser.Meta):
        constraints = (
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="accounts_user_email_ci_unique",
                violation_error_message="A user with this email already exists.",
            ),
        )
