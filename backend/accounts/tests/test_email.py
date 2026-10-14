from smtplib import SMTPException
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.tasks import TaskResultStatus
from django.test import TestCase
from django_tasks_db.models import DBTaskResult

from accounts.constants import DEMO_ADMIN_PASSWORD
from accounts.models import User
from accounts.tasks.email import (
    send_password_changed_email,
    send_password_reset_email,
    send_welcome_email,
)
from accounts.tests.base import run_huey_worker


class WelcomeEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="member", email="member@example.com", password=DEMO_ADMIN_PASSWORD
        )

    def run_worker(self):
        run_huey_worker()

    def test_worker_sends_the_queued_email(self):
        result = send_welcome_email.enqueue(self.user.pk)
        self.assertEqual(mail.outbox, [])
        self.run_worker()
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Welcome to Chobe")
        self.assertEqual(message.to, [self.user.email])
        self.assertEqual(message.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertIn(self.user.username, message.body)
        self.assertEqual(
            DBTaskResult.objects.get(pk=result.id).status, TaskResultStatus.SUCCESSFUL
        )
        self.run_worker()
        self.assertEqual(len(mail.outbox), 1)

    def test_missing_inactive_or_email_less_user_receives_no_email(self):
        self.assertEqual(send_welcome_email.call(0), 0)
        self.assertEqual(send_password_changed_email.call(0), 0)
        for changes in [{"is_active": False}, {"is_active": True, "email": ""}]:
            with self.subTest(changes=changes):
                User.objects.filter(pk=self.user.pk).update(**changes)
                self.assertEqual(send_welcome_email.call(self.user.pk), 0)
                self.assertEqual(send_password_changed_email.call(self.user.pk), 0)
        self.assertEqual(mail.outbox, [])

    def test_account_emails_use_html_only(self):
        for send, argument, subject in [
            (send_welcome_email, self.user.pk, "Welcome to Chobe"),
            (
                send_password_changed_email,
                self.user.pk,
                "Your Chobe password was changed",
            ),
            (
                send_password_reset_email,
                self.user.email,
                "Reset your Chobe password",
            ),
        ]:
            with self.subTest(subject=subject):
                self.assertEqual(send.call(argument), 1)
                message = mail.outbox[-1]
                self.assertEqual(message.subject, subject)
                self.assertIn("Chobe is a portfolio project.", message.body)
                self.assertEqual(message.message().get_content_type(), "text/html")
                self.assertFalse(message.message().is_multipart())
                self.assertIn(subject, message.body)
                self.assertIn(self.user.username, message.body)
                self.assertNotIn("<mjml", message.body)
                self.assertNotIn("{{", message.body)

    def test_html_escapes_user_content(self):
        self.user.username = "<b>member</b>&"
        self.user.save()
        for send, argument in [
            (send_welcome_email, self.user.pk),
            (send_password_changed_email, self.user.pk),
            (send_password_reset_email, self.user.email),
        ]:
            with self.subTest(task=send.module_path):
                self.assertEqual(send.call(argument), 1)
                message = mail.outbox[-1]
                self.assertIn("&lt;b&gt;member&lt;/b&gt;&amp;", message.body)
                self.assertNotIn(self.user.username, message.body)

    def test_smtp_failure_is_recorded_without_deleting_the_account(self):
        result = send_welcome_email.enqueue(self.user.pk)
        with (
            patch("accounts.emails.EmailMessage.send", side_effect=SMTPException),
            self.assertLogs("huey", level="ERROR"),
        ):
            self.run_worker()
        self.assertEqual(
            DBTaskResult.objects.get(pk=result.id).status, TaskResultStatus.FAILED
        )
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertEqual(mail.outbox, [])
