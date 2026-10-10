from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User


class UserEmailTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="first", email="first@example.com")

    def test_database_rejects_duplicate_email_on_create(self):
        for email in ("first@example.com", "FIRST@example.com"):
            with (
                self.subTest(email=email),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                User.objects.create_user(username="second", email=email)

    def test_database_rejects_duplicate_email_on_update(self):
        user = User.objects.create_user(username="second", email="second@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=user.pk).update(email="FIRST@example.com")

    def test_model_validation_reports_duplicate_email(self):
        user = User(username="second", email="FIRST@example.com", password="!")
        with self.assertRaisesMessage(
            ValidationError, "A user with this email already exists."
        ):
            user.full_clean()

    def test_users_without_email_can_coexist(self):
        User.objects.create_user(username="second")
        User.objects.create_user(username="third")
        self.assertEqual(User.objects.filter(email="").count(), 2)
