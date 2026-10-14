from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.tasks import TaskResultStatus
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_tasks_db.models import DBTaskResult
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient, APITestCase

from accounts.constants import DEMO_ADMIN_PASSWORD
from accounts.models import User
from accounts.serializers.password_reset import ResetPasswordSerializer
from accounts.tasks import send_password_reset_email


class PasswordResetTests(APITestCase):
    databases = frozenset({"default", "cache"})

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = User.objects.create_user(
            username="member", email="member@example.com", password=DEMO_ADMIN_PASSWORD
        )
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.get("/api/v1/auth/session/")
        self.payload = {
            "uid": urlsafe_base64_encode(force_bytes(self.user.pk)),
            "token": default_token_generator.make_token(self.user),
            "password": "New-safe-password-2026!",
            "password_confirm": "New-safe-password-2026!",
        }

    def post(self, path="reset-password", payload=None, **headers):
        return self.client.post(
            f"/api/v1/auth/{path}/",
            self.payload if payload is None else payload,
            format="json",
            HTTP_X_XSRF_TOKEN=self.client.cookies[settings.CSRF_COOKIE_NAME].value,
            **headers,
        )

    def test_requests_do_not_reveal_accounts_or_send_email_in_the_request(self):
        for email in [self.user.email.upper(), "unknown@example.com"]:
            with self.subTest(email=email):
                response = self.post("forgot-password", {"email": email})
                self.assertEqual(response.status_code, 202)
                self.assertEqual(response.content, b"")
                self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(DBTaskResult.objects.count(), 2)
        self.assertEqual(mail.outbox, [])

    def test_worker_sends_a_password_reset_link_to_the_configured_frontend(self):
        response = self.post(
            "forgot-password",
            {"email": self.user.email.upper()},
            HTTP_HOST="localhost",
            HTTP_ORIGIN="http://localhost",
        )
        self.assertEqual(response.status_code, 202)
        with patch(
            "django_tasks_db.management.commands.db_worker.Worker.configure_signals"
        ):
            call_command(
                "db_worker", batch=True, reload=False, startup_delay=False, verbosity=0
            )
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [self.user.email])
        self.assertIn(
            f"{settings.FRONTEND_URL}/reset-password/{self.payload['uid']}/",
            message.body,
        )
        self.assertIn("30 minutes", message.body)
        self.assertEqual(DBTaskResult.objects.get().status, TaskResultStatus.SUCCESSFUL)

    def test_unknown_inactive_or_unusable_accounts_receive_no_email(self):
        self.assertEqual(send_password_reset_email.call("unknown@example.com"), 0)
        self.user.is_active = False
        self.user.save()
        self.assertEqual(send_password_reset_email.call(self.user.email), 0)
        self.user.is_active = True
        self.user.set_unusable_password()
        self.user.save()
        self.assertEqual(send_password_reset_email.call(self.user.email), 0)
        self.assertEqual(mail.outbox, [])

    def test_smtp_errors_are_not_silently_swallowed(self):
        with (
            patch("accounts.emails.EmailMessage.send", side_effect=SMTPException),
            self.assertRaises(SMTPException),
        ):
            send_password_reset_email.call(self.user.email)

    def test_reset_password_and_invalidates_all_old_sessions_and_token(self):
        other_client = APIClient()
        other_client.force_login(self.user)
        self.client.force_login(self.user)
        self.user.refresh_from_db()
        self.payload["token"] = default_token_generator.make_token(self.user)
        response = self.post()
        self.assertEqual(response.status_code, 204)
        self.assertIn("no-store", response["Cache-Control"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.payload["password"]))
        self.assertFalse(
            default_token_generator.check_token(self.user, self.payload["token"])
        )
        self.assertEqual(other_client.get("/api/v1/auth/session/").data, {"user": None})
        self.assertEqual(self.client.get("/api/v1/auth/session/").data, {"user": None})
        self.assertEqual(self.post().status_code, 400)
        for password, status in [
            (DEMO_ADMIN_PASSWORD, 400),
            (self.payload["password"], 200),
        ]:
            response = self.post(
                "login", {"username": self.user.email, "password": password}
            )
            self.assertEqual(response.status_code, status)

    def test_expired_token_is_rejected(self):
        now = default_token_generator._now()
        with patch.object(
            default_token_generator,
            "_now",
            return_value=now - timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT + 1),
        ):
            token = default_token_generator.make_token(self.user)
        response = self.post(payload=self.payload | {"token": token})
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(DEMO_ADMIN_PASSWORD))

    def test_password_reset_queues_one_html_notification_without_secrets(self):
        self.assertEqual(self.post().status_code, 204)
        self.assertEqual(DBTaskResult.objects.count(), 1)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(self.post().status_code, 400)
        self.assertEqual(DBTaskResult.objects.count(), 1)
        with patch(
            "django_tasks_db.management.commands.db_worker.Worker.configure_signals"
        ):
            call_command(
                "db_worker", batch=True, reload=False, startup_delay=False, verbosity=0
            )
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Your Chobe password was changed")
        self.assertEqual(message.to, [self.user.email])
        self.assertEqual(message.message().get_content_type(), "text/html")
        self.assertIn("changed successfully", message.body)
        self.assertIn(f"{settings.FRONTEND_URL}/forgot-password", message.body)
        for secret in [
            DEMO_ADMIN_PASSWORD,
            self.payload["password"],
            self.payload["token"],
        ]:
            self.assertNotIn(secret, message.body)
        self.assertEqual(DBTaskResult.objects.get().status, TaskResultStatus.SUCCESSFUL)

    def test_notification_queue_failure_rolls_back_password_reset(self):
        with (
            patch(
                "accounts.views.send_password_changed_email",
                **{"enqueue.side_effect": RuntimeError("Queue unavailable")},
            ),
            self.assertRaises(RuntimeError),
        ):
            self.post()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(DEMO_ADMIN_PASSWORD))
        self.assertTrue(
            default_token_generator.check_token(self.user, self.payload["token"])
        )
        self.assertFalse(DBTaskResult.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_invalid_or_inactive_user_link_is_rejected(self):
        for changes in [
            {"uid": "bad-uid"},
            {"uid": "!"},
            {"uid": "MA"},
            {"token": "wrong"},
        ]:
            with self.subTest(changes=changes):
                self.assertEqual(
                    self.post(payload=self.payload | changes).status_code, 400
                )
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.post().status_code, 400)
        self.assertFalse(DBTaskResult.objects.exists())

    def test_password_validation_preserves_a_valid_recovery_link(self):
        for changes in [
            {"password_confirm": "different-password"},
            {"password": "short", "password_confirm": "short"},
            {"password": "123456789", "password_confirm": "123456789"},
            {"password": "password", "password_confirm": "password"},
        ]:
            with self.subTest(changes=changes):
                response = self.post(payload=self.payload | changes)
                self.assertEqual(response.status_code, 400)
                self.assertIn("password_confirm", response.data)
                self.assertTrue(
                    default_token_generator.check_token(
                        self.user, self.payload["token"]
                    )
                )
        self.assertEqual(self.post().status_code, 204)

    def test_missing_fields_and_invalid_input_are_rejected(self):
        for payload in [{}, [], self.payload | {"password": None}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.post(payload=payload).status_code, 400)
        for payload in [{}, {"email": "invalid"}, []]:
            with self.subTest(payload=payload):
                self.assertEqual(self.post("forgot-password", payload).status_code, 400)
        self.assertFalse(DBTaskResult.objects.exists())

    def test_csrf_and_origin_checks_cover_both_recovery_endpoints(self):
        for path, payload in [
            ("forgot-password", {"email": self.user.email}),
            ("reset-password", self.payload),
        ]:
            with self.subTest(path=path):
                response = self.client.post(
                    f"/api/v1/auth/{path}/", payload, format="json"
                )
                self.assertEqual(response.status_code, 403)
                response = self.post(
                    path, payload, HTTP_ORIGIN="https://attacker.example"
                )
                self.assertEqual(response.status_code, 403)
        self.assertFalse(DBTaskResult.objects.exists())

    def test_forgot_password_requests_are_limited_by_email_and_ip(self):
        for _ in range(3):
            self.assertEqual(
                self.post(
                    "forgot-password", {"email": "unknown@example.com"}
                ).status_code,
                202,
            )
        response = self.post("forgot-password", {"email": "UNKNOWN@example.com"})
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
        cache.clear()
        for index in range(5):
            self.assertEqual(
                self.post(
                    "forgot-password", {"email": f"unknown{index}@example.com"}
                ).status_code,
                202,
            )
        self.assertEqual(
            self.post("forgot-password", {"email": "last@example.com"}).status_code,
            429,
        )

    def test_password_resets_are_limited_by_ip(self):
        for _ in range(10):
            self.assertEqual(
                self.post(payload=self.payload | {"token": "wrong"}).status_code, 400
            )
        self.assertEqual(self.post().status_code, 429)

    def test_two_validated_password_resets_cannot_reuse_one_link(self):
        first = ResetPasswordSerializer(data=self.payload)
        second = ResetPasswordSerializer(data=self.payload)
        first.is_valid(raise_exception=True)
        second.is_valid(raise_exception=True)
        first.save()
        with self.assertRaises(ValidationError):
            second.save()

    def test_openapi_describes_recovery_requests_and_empty_responses(self):
        paths = self.client.get(
            "/api/v1/schema/", HTTP_ACCEPT="application/json"
        ).json()["paths"]
        self.assertNotIn("/api/v1/auth/change-password/", paths)
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/change-password/", {}, format="json"
            ).status_code,
            404,
        )
        for path, status, serializer in [
            ("forgot-password", "202", "ForgotPassword"),
            ("reset-password", "204", "ResetPassword"),
        ]:
            operation = paths[f"/api/v1/auth/{path}/"]["post"]
            self.assertEqual(
                operation["requestBody"]["content"]["application/json"]["schema"][
                    "$ref"
                ],
                f"#/components/schemas/{serializer}",
            )
            self.assertNotIn("content", operation["responses"][status])
            self.assertTrue(operation["parameters"][0]["required"])
