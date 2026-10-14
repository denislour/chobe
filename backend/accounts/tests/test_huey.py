import json
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core import mail
from django.db import transaction
from django.tasks import TaskResultStatus
from django.test import SimpleTestCase, TransactionTestCase
from django.utils import timezone
from django_tasks_db.models import DBTaskResult
from huey.contrib.djhuey import HUEY
from huey.storage import SqliteStorage

from accounts.constants import DEMO_ADMIN_PASSWORD
from accounts.models import User, ViewingHistory
from accounts.services.auth import register_account
from accounts.tasks.dispatch import cleanup_account_data_and_sessions
from accounts.tasks.email import send_welcome_email
from tasks.dispatch import (
    cleanup_outbox_results,
    dispatch_pending_tasks,
    execute_outbox_task,
    queue_outbox_task,
)


class HueyOutboxTests(TransactionTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        storage = SqliteStorage(
            "chobe-test", filename=str(Path(directory.name) / "queue.sqlite3")
        )
        self.addCleanup(storage.close)
        self.enterContext(patch.object(HUEY, "storage", storage))
        self.user = User.objects.create_user("member", "member@example.com")

    def drain_queue(self):
        while task := HUEY.dequeue():
            HUEY.execute(task)

    def test_job_is_published_after_commit_and_contains_only_its_id(self):
        with transaction.atomic():
            result = send_welcome_email.enqueue(self.user.pk)
            self.assertEqual(HUEY.pending_count(), 0)
            self.assertEqual(DBTaskResult.objects.get(pk=result.id).status, "READY")
        self.assertEqual(HUEY.pending()[0].args, (str(result.id),))
        self.assertEqual(mail.outbox, [])
        self.drain_queue()
        result.refresh()
        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(len(mail.outbox), 1)

    def test_rollback_removes_user_and_outbox_without_publishing(self):
        with self.assertRaises(RuntimeError), transaction.atomic():
            register_account(
                {
                    "username": "rolled-back",
                    "email": "rollback@example.com",
                    "password": DEMO_ADMIN_PASSWORD,
                    "accept_terms": True,
                }
            )
            raise RuntimeError("Rollback")
        self.assertFalse(User.objects.filter(username="rolled-back").exists())
        self.assertFalse(DBTaskResult.objects.exists())
        self.assertEqual(HUEY.pending_count(), 0)

    def test_queue_failure_keeps_outbox_for_periodic_recovery(self):
        with (
            patch("tasks.dispatch.queue_outbox_task", side_effect=OSError),
            self.assertLogs("django.db.backends.base", level="ERROR"),
        ):
            result = send_welcome_email.enqueue(self.user.pk)
        self.assertEqual(DBTaskResult.objects.get(pk=result.id).status, "READY")
        self.assertEqual(HUEY.pending_count(), 0)
        self.assertEqual(dispatch_pending_tasks.call_local(), 1)
        self.drain_queue()
        self.assertEqual(len(mail.outbox), 1)
        result.refresh()
        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)

    def test_duplicate_delivery_does_not_execute_finished_task_again(self):
        result = send_welcome_email.enqueue(self.user.pk)
        queue_outbox_task(str(result.id))
        self.assertEqual(HUEY.pending_count(), 2)
        delivery = HUEY.dequeue()
        data = HUEY.serialize_task(delivery)
        message = HUEY.serializer.deserialize(data)
        self.assertEqual(message.name, "accounts.tasks.dispatch.execute_outbox_task")
        HUEY.execute(HUEY.deserialize_task(data))
        self.drain_queue()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(execute_outbox_task.call_local(str(result.id)), 0)

    def test_removed_outbox_job_is_ignored_by_existing_delivery(self):
        result = send_welcome_email.enqueue(self.user.pk)
        DBTaskResult.objects.filter(pk=result.id).delete()
        self.drain_queue()
        self.assertEqual(mail.outbox, [])

    def test_future_job_is_not_executed_before_its_due_time(self):
        due = timezone.now() + timedelta(hours=1)
        result = send_welcome_email.using(run_after=due).enqueue(self.user.pk)
        self.assertEqual(execute_outbox_task.call_local(str(result.id)), 0)
        self.assertEqual(dispatch_pending_tasks.call_local(), 0)
        self.assertEqual(mail.outbox, [])
        result.refresh()
        self.assertEqual(result.status, TaskResultStatus.READY)
        DBTaskResult.objects.filter(pk=result.id).update(
            run_after=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(dispatch_pending_tasks.call_local(), 1)
        self.drain_queue()
        self.assertEqual(len(mail.outbox), 1)

    def test_periodic_maintenance_removes_expired_sessions_history_and_results(self):
        now = timezone.now()
        expired = Session.objects.create(
            session_key="expired", session_data="", expire_date=now - timedelta(days=1)
        )
        active = Session.objects.create(
            session_key="active", session_data="", expire_date=now + timedelta(days=1)
        )
        history = ViewingHistory.objects.create(user=self.user, listing_id=1)
        ViewingHistory.objects.filter(pk=history.pk).update(
            viewed_at=now - timedelta(days=31)
        )
        result = send_welcome_email.enqueue(self.user.pk)
        self.drain_queue()
        DBTaskResult.objects.filter(pk=result.id).update(
            finished_at=now - timedelta(days=15)
        )
        cleanup_account_data_and_sessions.call_local()
        cleanup_outbox_results.call_local()
        self.assertFalse(Session.objects.filter(pk=expired.pk).exists())
        self.assertTrue(Session.objects.filter(pk=active.pk).exists())
        self.assertFalse(ViewingHistory.objects.filter(pk=history.pk).exists())
        self.assertFalse(DBTaskResult.objects.filter(pk=result.id).exists())

    def test_scheduler_registers_recovery_and_daily_maintenance(self):
        at_three = timezone.now().replace(hour=3, minute=0, second=0, microsecond=0)
        names = {task.name for task in HUEY.read_periodic(at_three)}
        self.assertIn("dispatch_pending_tasks", names)
        self.assertIn("cleanup_account_data_and_sessions", names)
        self.assertIn("cleanup_outbox_results", names)
        at_four = at_three.replace(hour=4)
        names = {task.name for task in HUEY.read_periodic(at_four)}
        self.assertIn("dispatch_pending_tasks", names)
        self.assertNotIn("cleanup_account_data_and_sessions", names)
        self.assertNotIn("cleanup_outbox_results", names)


class HueyConsumerTests(SimpleTestCase):
    def test_real_threaded_consumer_recovers_committed_job_from_outbox(self):
        with TemporaryDirectory() as directory:
            environment = {
                **os.environ,
                "DJANGO_SETTINGS_MODULE": "config.settings",
                "DJANGO_QUEUE_DB_PATH": str(Path(directory) / "queue.sqlite3"),
                "DJANGO_CACHE_DB_PATH": str(Path(directory) / "cache.sqlite3"),
                "TEST_BUSINESS_DB": str(Path(directory) / "business.sqlite3"),
            }
            script = """
import json
import os
import time
from io import StringIO
from django.conf import settings
settings.DATABASES["default"]["NAME"] = os.environ["TEST_BUSINESS_DB"]
settings.MAILERS = {
    "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
}
import django
django.setup()
from django.core import mail
from django.core.management import call_command
from django_tasks_db.models import DBTaskResult
from huey.contrib.djhuey import HUEY
from accounts.services.auth import register_account
call_command("migrate", verbosity=0, stdout=StringIO())
register_account({
    "username": "consumer-member",
    "email": "consumer@example.com",
    "password": "safe-test-password",
    "accept_terms": True,
})
assert not hasattr(mail, "outbox") or not mail.outbox
HUEY.storage.flush_queue()
consumer = HUEY.create_consumer(
    workers=2, worker_type="thread", periodic=False,
    scheduler_interval=1, initial_delay=0.01, max_delay=0.05,
    shutdown_timeout=5,
)
consumer.start()
try:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        status = DBTaskResult.objects.get().status
        if status == "SUCCESSFUL":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Consumer did not finish the task")
finally:
    consumer.stop(graceful=True)
print(json.dumps({
    "status": status,
    "emails": len(mail.outbox),
    "queue_mode": HUEY.storage.sql("PRAGMA journal_mode", results=True)[0][0],
}))
"""
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=settings.BASE_DIR,
                env=environment,
                capture_output=True,
                text=True,
                timeout=40,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(result.stdout),
                {"status": "SUCCESSFUL", "emails": 1, "queue_mode": "wal"},
            )
