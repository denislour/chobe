from smtplib import SMTPException
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.tasks import TaskResultStatus
from django.test import TestCase
from django_tasks_db.models import DBTaskResult

from accounts.models import User
from accounts.tasks import send_welcome_email


class WelcomeEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="member", email="member@example.com"
        )

    def run_worker(self):
        with patch(
            "django_tasks_db.management.commands.db_worker.Worker.configure_signals"
        ):
            call_command(
                "db_worker",
                batch=True,
                reload=False,
                startup_delay=False,
                verbosity=0,
            )

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
        for changes in [{"is_active": False}, {"is_active": True, "email": ""}]:
            with self.subTest(changes=changes):
                User.objects.filter(pk=self.user.pk).update(**changes)
                self.assertEqual(send_welcome_email.call(self.user.pk), 0)
        self.assertEqual(mail.outbox, [])

    def test_smtp_failure_is_recorded_without_deleting_the_account(self):
        result = send_welcome_email.enqueue(self.user.pk)
        with patch("accounts.tasks.send_mail", side_effect=SMTPException):
            self.run_worker()
        self.assertEqual(
            DBTaskResult.objects.get(pk=result.id).status, TaskResultStatus.FAILED
        )
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertEqual(mail.outbox, [])
