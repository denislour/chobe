from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError
from django.tasks import TaskResultStatus
from django_tasks_db.models import DBTaskResult
from rest_framework.test import APIClient, APITestCase

from accounts.constants import DEMO_ADMIN_PASSWORD
from accounts.models import User


class RegisterTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.get("/api/v1/auth/session/")
        self.payload = {
            "username": "new_member",
            "email": "member@example.com",
            "password": DEMO_ADMIN_PASSWORD,
            "accept_terms": True,
        }

    def register(self, **changes):
        return self.client.post(
            "/api/v1/auth/register/",
            self.payload | changes,
            format="json",
            HTTP_X_XSRF_TOKEN=self.client.cookies[settings.CSRF_COOKIE_NAME].value,
        )

    def test_registration_creates_a_normal_user_and_rotates_csrf(self):
        old_token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        response = self.register(
            email="MEMBER@example.com", is_staff=True, is_superuser=True
        )
        user = User.objects.get(username=self.payload["username"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, {"id": user.pk, "username": user.username})
        self.assertEqual(user.email, self.payload["email"])
        self.assertTrue(user.check_password(self.payload["password"]))
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        self.assertTrue(response.cookies[settings.SESSION_COOKIE_NAME]["httponly"])
        self.assertNotEqual(
            response.cookies[settings.CSRF_COOKIE_NAME].value, old_token
        )
        self.assertIn("no-store", response["Cache-Control"])
        task = DBTaskResult.objects.get()
        self.assertEqual(task.task_path, "accounts.tasks.send_welcome_email")
        self.assertEqual(task.args_kwargs, {"args": [user.pk], "kwargs": {}})
        self.assertEqual(task.status, TaskResultStatus.READY)
        self.assertEqual(mail.outbox, [])

    def test_queue_failure_rolls_back_the_new_account(self):
        with (
            patch("django.tasks.base.Task.enqueue", side_effect=RuntimeError),
            self.assertRaises(RuntimeError),
        ):
            self.register()
        self.assertFalse(User.objects.exists())
        self.assertFalse(DBTaskResult.objects.exists())

    def test_existing_session_cannot_create_another_account(self):
        self.register()
        response = self.register(username="other", email="other@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["non_field_errors"],
            ["Log out before creating another account."],
        )
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_username_or_email_is_rejected(self):
        User.objects.create_user(username="existing", email="existing@example.com")
        for field, value in [
            ("username", "existing"),
            ("email", "EXISTING@example.com"),
        ]:
            with self.subTest(field=field):
                response = self.register(**{field: value})
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_email_cannot_match_an_existing_username(self):
        User.objects.create_user(
            username="MEMBER@example.com", email="other@example.com"
        )
        response = self.register()
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_username_is_validated_after_unicode_normalization(self):
        User.objects.create_user(username="Alice", email="alice@example.com")
        for username in ["Ａlice", "⑴", "ﬃ" * 60]:
            with self.subTest(username=username):
                response = self.register(username=username)
                self.assertEqual(response.status_code, 400)
                self.assertIn("username", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_fields_create_no_user(self):
        cases = [
            ("username", "n@m"),
            ("username", "bad name"),
            ("username", "a" * 151),
            ("email", "invalid"),
            ("accept_terms", False),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                cache.clear()
                response = self.register(**{field: value})
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)
        self.assertFalse(User.objects.exists())
        self.assertFalse(DBTaskResult.objects.exists())

    def test_django_password_validators_are_applied(self):
        for password in ["short", "123456789", "password", "new_member", "x" * 129]:
            with self.subTest(password=password):
                response = self.register(password=password)
                self.assertEqual(response.status_code, 400)
                self.assertIn("password", response.data)
        self.assertFalse(User.objects.exists())

    def test_missing_fields_and_non_object_input_are_rejected(self):
        for payload in [{}, [], self.payload | {"password": None}]:
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/api/v1/auth/register/",
                    payload,
                    format="json",
                    HTTP_X_XSRF_TOKEN=self.client.cookies[
                        settings.CSRF_COOKIE_NAME
                    ].value,
                )
                self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_csrf_cookie_header_and_trusted_origin_are_required(self):
        for headers in [
            {},
            {"HTTP_X_XSRF_TOKEN": "x" * 32},
            {
                "HTTP_X_XSRF_TOKEN": self.client.cookies[
                    settings.CSRF_COOKIE_NAME
                ].value,
                "HTTP_ORIGIN": "https://attacker.example",
            },
        ]:
            with self.subTest(headers=headers):
                response = self.client.post(
                    "/api/v1/auth/register/",
                    self.payload,
                    format="json",
                    **headers,
                )
                self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.exists())

    def test_registration_is_limited_by_ip(self):
        for index in range(5):
            self.client.defaults["HTTP_X_FORWARDED_FOR"] = f"192.0.2.{index}"
            self.assertEqual(self.register(password="short").status_code, 400)
        response = self.register()
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
        self.assertFalse(User.objects.exists())

    def test_unique_conflict_during_save_returns_validation_error(self):
        with patch(
            "accounts.serializers.register.User.objects.create_user",
            side_effect=IntegrityError,
        ):
            response = self.register()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["non_field_errors"], ["Username or email is already in use."]
        )
        self.assertFalse(User.objects.exists())

    def test_registered_user_can_log_in_with_username_or_email(self):
        self.register()
        for identifier in [self.payload["username"], self.payload["email"].upper()]:
            with self.subTest(identifier=identifier):
                self.client.logout()
                self.client.get("/api/v1/auth/session/")
                response = self.client.post(
                    "/api/v1/auth/login/",
                    {"username": identifier, "password": self.payload["password"]},
                    format="json",
                    HTTP_X_XSRF_TOKEN=self.client.cookies[
                        settings.CSRF_COOKIE_NAME
                    ].value,
                )
                self.assertEqual(response.status_code, 200)

    def test_registration_contract_is_in_openapi(self):
        schema = self.client.get(
            "/api/v1/schema/", HTTP_ACCEPT="application/json"
        ).json()
        operation = schema["paths"]["/api/v1/auth/register/"]["post"]
        self.assertEqual(
            operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/Register",
        )
        self.assertEqual(
            operation["responses"]["201"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/AuthUser",
        )
        self.assertEqual(operation["parameters"][0]["name"], "X-XSRF-TOKEN")
