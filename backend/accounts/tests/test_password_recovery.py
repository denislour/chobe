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
from rest_framework.test import APIClient, APITestCase

from accounts.constants import DEMO_ADMIN_PASSWORD
from accounts.models import User
from accounts.tasks import send_password_recovery_email


class PasswordRecoveryTests(APITestCase):
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

    def post(self, path="change-password", payload=None, **headers):
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

    def test_worker_sends_a_password_change_link_to_the_configured_frontend(self):
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
            f"{settings.FRONTEND_URL}/change-password/{self.payload['uid']}/",
            message.body,
        )
        self.assertIn("30 minutes", message.body)
        self.assertEqual(DBTaskResult.objects.get().status, TaskResultStatus.SUCCESSFUL)

    def test_unknown_inactive_or_unusable_accounts_receive_no_email(self):
        self.assertEqual(send_password_recovery_email.call("unknown@example.com"), 0)
        self.user.is_active = False
        self.user.save()
        self.assertEqual(send_password_recovery_email.call(self.user.email), 0)
        self.user.is_active = True
        self.user.set_unusable_password()
        self.user.save()
        self.assertEqual(send_password_recovery_email.call(self.user.email), 0)
        self.assertEqual(mail.outbox, [])

    def test_smtp_errors_are_not_silently_swallowed(self):
        with (
            patch("accounts.emails.EmailMessage.send", side_effect=SMTPException),
            self.assertRaises(SMTPException),
        ):
            send_password_recovery_email.call(self.user.email)
