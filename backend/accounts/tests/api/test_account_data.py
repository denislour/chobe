import base64
from datetime import timedelta
from importlib import import_module
from unittest.mock import patch

from django.apps import apps
from django.contrib.sessions.models import Session
from django.core import signing
from django.core.management import call_command
from django.db import connection
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django_tasks_db.models import DBTaskResult
from rest_framework.test import APIClient

from accounts.constants import DEMO_ADMIN_PASSWORD
from accounts.models import (
    AccountDataExport,
    ConsentEvent,
    DeletionRequest,
    Profile,
    User,
    ViewingHistory,
)
from accounts.services.privacy import privacy_for
from accounts.services.profile import profile_for
from accounts.tasks.account_data import build_account_data_export, delete_account_data
from accounts.tasks.email import (
    send_password_changed_email,
    send_password_reset_email,
    send_welcome_email,
)
from accounts.tests.base import AccountAPITestCase


class AccountDataTests(AccountAPITestCase):
    def test_export_serializes_nested_consent_and_only_recent_owned_history(self):
        consent = ConsentEvent.objects.create(user=self.user, share_phone=False)
        ConsentEvent.objects.create(user=self.other, share_phone=True)
        ViewingHistory.objects.create(user=self.user, listing_id=1)
        expired = ViewingHistory.objects.create(user=self.user, listing_id=2)
        ViewingHistory.objects.filter(pk=expired.pk).update(
            viewed_at=timezone.now() - timedelta(days=31)
        )
        ViewingHistory.objects.create(user=self.other, listing_id=3)

        response = self.request("post", "me/data-exports", {})
        self.run_worker()
        payload = self.request(
            "get", f"me/data-exports/{response.data['job_id']}/download"
        ).json()

        self.assertEqual(payload["account"]["id"], self.user.pk)
        self.assertEqual(len(payload["consent"]), 1)
        self.assertEqual(payload["consent"][0]["share_phone"], False)
        self.assertEqual(payload["consent"][0]["policy_version"], 1)
        self.assertEqual(
            parse_datetime(payload["consent"][0]["created_at"]), consent.created_at
        )
        self.assertEqual(
            [entry["listing_id"] for entry in payload["viewing_history"]], [1]
        )
        self.assertIsNotNone(parse_datetime(payload["generated_at"]))
        self.assertIsNone(payload["avatar_jpeg_base64"])

    def test_export_is_async_idempotent_owner_scoped_and_downloadable(self):
        profile = profile_for(self.user)
        profile.phone = "+84912345678"
        profile.avatar = b"stored-avatar-bytes"
        profile.save()
        privacy = privacy_for(self.user)
        ViewingHistory.objects.create(user=self.other, listing_id=99)
        first = self.request("post", "me/data-exports", {})
        second = self.request("post", "me/data-exports", {})
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.data["job_id"], second.data["job_id"])
        self.assertEqual(DBTaskResult.objects.count(), 1)
        job_id = str(first.data["job_id"])
        self.assertEqual(
            self.request("get", f"me/data-exports/{job_id}/download").status_code, 409
        )
        self.run_worker()
        response = self.request("get", f"me/data-exports/{job_id}/download")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("no-store", response["Cache-Control"])
        payload = response.json()
        self.assertEqual(payload["profile"]["phone"], profile.phone)
        self.assertEqual(payload["profile"]["email"], self.user.email)
        self.assertNotIn("avatar_url", payload["profile"])
        self.assertEqual(
            base64.b64decode(payload["avatar_jpeg_base64"]), profile.avatar
        )
        self.assertEqual(payload["privacy"]["share_phone"], privacy.share_phone)
        self.assertEqual(payload["privacy"]["record_history"], privacy.record_history)
        self.assertIsNone(payload["privacy"]["consent_at"])
        self.assertEqual(payload["viewing_history"], [])
        for secret in [
            self.user.password,
            DEMO_ADMIN_PASSWORD,
            self.other.email,
            "_auth_user_id",
        ]:
            self.assertNotIn(secret, response.content.decode())
        self.assertEqual(build_account_data_export.call(job_id), 0)
        client = APIClient()
        client.force_login(self.other)
        self.assertEqual(
            client.get(f"/api/v1/me/data-exports/{job_id}/").status_code, 404
        )
        self.assertEqual(
            client.get(f"/api/v1/me/data-exports/{job_id}/download/").status_code, 404
        )

    def test_expired_export_is_not_downloaded_and_payload_is_wiped(self):
        job = AccountDataExport.objects.create(
            user=self.user,
            status="ready",
            payload={"email": self.user.email},
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        self.assertEqual(
            self.request("get", f"me/data-exports/{job.pk}").data["status"], "expired"
        )
        self.assertEqual(
            self.request("get", f"me/data-exports/{job.pk}/download").status_code, 410
        )
        job.refresh_from_db()
        self.assertEqual(job.payload, {})

    def test_export_queue_failure_rolls_back_and_worker_failure_can_retry(self):
        with (
            patch(
                "accounts.tasks.account_data.build_account_data_export",
                **{"enqueue.side_effect": RuntimeError("Queue unavailable")},
            ),
            self.assertRaises(RuntimeError),
        ):
            self.request("post", "me/data-exports", {})
        self.assertFalse(AccountDataExport.objects.exists())
        job = AccountDataExport.objects.create(user=self.user)
        with (
            patch(
                "accounts.services.account_data.profile_for",
                side_effect=RuntimeError("Unavailable"),
            ),
            self.assertRaises(RuntimeError),
        ):
            build_account_data_export.call(str(job.pk))
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertEqual(build_account_data_export.call(str(job.pk)), 1)

    def test_deletion_requires_current_password_and_confirmation(self):
        for payload in [
            {"password": "wrong", "confirmation": "DELETE"},
            {"password": DEMO_ADMIN_PASSWORD, "confirmation": "delete"},
            {},
        ]:
            with self.subTest(payload=payload):
                self.assertEqual(
                    self.request("post", "me/deletion-requests", payload).status_code,
                    400,
                )
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertFalse(DeletionRequest.objects.exists())

    def test_deletion_disables_account_then_worker_removes_data_and_receipt_has_no_pii(
        self,
    ):
        profile_for(self.user)
        privacy = privacy_for(self.user)
        privacy.share_phone = True
        privacy.save()
        AccountDataExport.objects.create(
            user=self.user, payload={"email": self.user.email}
        )
        ViewingHistory.objects.create(user=self.user, listing_id=1)
        response = self.request(
            "post",
            "me/deletion-requests",
            {"password": DEMO_ADMIN_PASSWORD, "confirmation": "DELETE"},
        )
        self.assertEqual(response.status_code, 202)
        receipt = response.data["receipt"]
        job_id = str(response.data["job_id"])
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(privacy_for(self.user).share_phone)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get("/api/v1/profiles/me/").status_code, 403)
        self.run_worker()
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(Profile.objects.filter(user_id=self.user.pk).exists())
        self.assertFalse(
            AccountDataExport.objects.filter(user_id=self.user.pk).exists()
        )
        self.assertTrue(User.objects.filter(pk=self.other.pk).exists())
        status = APIClient().get(f"/api/v1/account-deletion-status/{receipt}/")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.data["status"], "completed")
        self.assertNotIn(self.user.email, str(status.data))
        self.assertEqual(delete_account_data.call(job_id), 0)

    def test_deletion_queue_failure_keeps_account_active(self):
        with (
            patch(
                "accounts.tasks.account_data.delete_account_data",
                **{"enqueue.side_effect": RuntimeError("Queue unavailable")},
            ),
            self.assertRaises(RuntimeError),
        ):
            self.request(
                "post",
                "me/deletion-requests",
                {"password": DEMO_ADMIN_PASSWORD, "confirmation": "DELETE"},
            )
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertFalse(DeletionRequest.objects.exists())

    def test_receipt_rejects_tampering_expiry_and_cannot_authorize_other_data(self):
        job = DeletionRequest.objects.create(user=self.user)
        receipt = signing.dumps(str(job.pk), salt="account-deletion", compress=True)
        client = APIClient()
        self.assertEqual(
            client.get(f"/api/v1/account-deletion-status/{receipt}x/").status_code, 404
        )
        with patch(
            "django.core.signing.time.time",
            return_value=timezone.now().timestamp() + 8 * 24 * 3600,
        ):
            self.assertEqual(
                client.get(f"/api/v1/account-deletion-status/{receipt}/").status_code,
                404,
            )
        self.assertEqual(
            client.get(f"/api/v1/profiles/me/?receipt={receipt}").status_code, 403
        )
        self.assertEqual(
            client.post(f"/api/v1/account-deletion-status/{receipt}/", {}).status_code,
            405,
        )

    def test_cleanup_removes_only_expired_data(self):
        old = ViewingHistory.objects.create(user=self.user, listing_id=1)
        ViewingHistory.objects.filter(pk=old.pk).update(
            viewed_at=timezone.now() - timedelta(days=31)
        )
        current = ViewingHistory.objects.create(user=self.other, listing_id=2)
        expired = AccountDataExport.objects.create(
            user=self.user,
            status="ready",
            payload={"private": True},
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        job = DeletionRequest.objects.create(
            status="completed", completed_at=timezone.now() - timedelta(days=8)
        )
        call_command("cleanup_account_data", verbosity=0)
        self.assertFalse(ViewingHistory.objects.filter(pk=old.pk).exists())
        self.assertTrue(ViewingHistory.objects.filter(pk=current.pk).exists())
        self.assertFalse(DeletionRequest.objects.filter(pk=job.pk).exists())
        expired.refresh_from_db()
        self.assertEqual(expired.payload, {})

    def test_csrf_and_authentication_are_required_for_data_requests(self):
        for path in ["me/data-exports", "me/deletion-requests"]:
            with self.subTest(path=path):
                self.assertEqual(
                    APIClient().post(f"/api/v1/{path}/", {}, format="json").status_code,
                    403,
                )
                self.assertEqual(
                    self.client.post(f"/api/v1/{path}/", {}, format="json").status_code,
                    403,
                )

    def test_deletion_cleans_own_sessions_and_email_tasks_only(self):
        other_client = APIClient()
        other_client.force_login(self.other)
        other_session = other_client.session.session_key
        own_session = self.client.session.session_key
        send_password_reset_email.enqueue(self.user.email.upper())
        send_welcome_email.enqueue(self.user.pk)
        other_task = send_welcome_email.enqueue(self.other.pk)
        job = DeletionRequest.objects.create(user=self.user)

        self.assertEqual(delete_account_data.call(str(job.pk)), 1)
        self.assertFalse(Session.objects.filter(session_key=own_session).exists())
        self.assertTrue(Session.objects.filter(session_key=other_session).exists())
        self.assertEqual(DBTaskResult.objects.count(), 1)
        self.assertTrue(DBTaskResult.objects.filter(pk=other_task.id).exists())

    def test_deletion_worker_failure_rolls_back_and_can_retry(self):
        profile_for(self.user)
        job = DeletionRequest.objects.create(user=self.user)
        with (
            patch(
                "accounts.models.User.delete",
                side_effect=RuntimeError("Unavailable"),
            ),
            self.assertRaises(RuntimeError),
        ):
            delete_account_data.call(str(job.pk))
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(Profile.objects.filter(user=self.user).exists())
        self.assertEqual(delete_account_data.call(str(job.pk)), 1)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_export_limit_does_not_limit_polling_or_overwrite_previous_exports(self):
        job_ids = []
        for _ in range(2):
            response = self.request("post", "me/data-exports", {})
            self.assertEqual(response.status_code, 202)
            job_ids.append(response.data["job_id"])
            self.run_worker()
        limited = self.request("post", "me/data-exports", {})
        self.assertEqual(limited.status_code, 429)
        self.assertIn(
            "limit of 2 account exports per hour", str(limited.data["detail"])
        )
        self.assertIn("Retry-After", limited)
        self.assertEqual(self.request("get", "me/data-exports").status_code, 200)
        with patch(
            "rest_framework.throttling.SimpleRateThrottle.timer",
            return_value=timezone.now().timestamp() + 3601,
        ):
            response = self.request("post", "me/data-exports", {})
        self.assertEqual(response.status_code, 202)
        self.assertNotIn(response.data["job_id"], job_ids)
        self.assertEqual(AccountDataExport.objects.filter(user=self.user).count(), 3)
        self.assertEqual(
            AccountDataExport.objects.filter(pk__in=job_ids, status="ready").count(), 2
        )

    def test_task_path_migration_preserves_existing_export_jobs(self):
        migration = import_module(
            "accounts.migrations.0004_account_data_and_privacy_tasks"
        )
        job = AccountDataExport.objects.create(user=self.user)
        queued = build_account_data_export.enqueue(str(job.pk))
        DBTaskResult.objects.filter(pk=queued.id).update(
            task_path="accounts.data_tasks.build_data_export"
        )
        other_task = send_welcome_email.enqueue(self.other.pk)
        editor = connection.schema_editor()
        migration.move_privacy_tasks(apps, editor)
        self.assertEqual(
            DBTaskResult.objects.get(pk=queued.id).task_path,
            "accounts.privacy_tasks.build_account_data_export",
        )
        self.assertEqual(
            DBTaskResult.objects.get(pk=other_task.id).task_path,
            "accounts.tasks.email.send_welcome_email",
        )
        migration.restore_privacy_tasks(apps, editor)
        self.assertEqual(
            DBTaskResult.objects.get(pk=queued.id).task_path,
            "accounts.data_tasks.build_data_export",
        )
        migration.move_privacy_tasks(apps, editor)
        import_module("accounts.migrations.0005_organize_task_modules").move_tasks(
            apps, editor
        )
        import_module("accounts.migrations.0006_group_account_modules").move_tasks(
            apps, editor
        )
        import_module("accounts.migrations.0007_merge_accounts_module").move_tasks(
            apps, editor
        )
        import_module("accounts.migrations.0008_consolidate_api_app").move_tasks(
            apps, editor
        )
        import_module("accounts.migrations.0009_modular_monolith").move_tasks(
            apps, editor
        )
        import_module("accounts.migrations.0010_simplify_accounts").move_tasks(
            apps, editor
        )
        self.run_worker()
        job.refresh_from_db()
        self.assertEqual(job.status, "ready")

    def test_task_package_migration_moves_all_jobs_without_changing_arguments(self):
        migration = import_module("accounts.migrations.0005_organize_task_modules")
        export = AccountDataExport.objects.create(user=self.user)
        deletion = DeletionRequest.objects.create(user=self.other)
        queued = []
        for task, argument, old_path in [
            (send_welcome_email, self.user.pk, "accounts.tasks.send_welcome_email"),
            (
                send_password_reset_email,
                self.user.email,
                "accounts.tasks.send_password_reset_email",
            ),
            (
                send_password_changed_email,
                self.user.pk,
                "accounts.tasks.send_password_changed_email",
            ),
            (
                build_account_data_export,
                str(export.pk),
                "accounts.privacy_tasks.build_account_data_export",
            ),
            (
                delete_account_data,
                str(deletion.pk),
                "accounts.privacy_tasks.delete_account_data",
            ),
        ]:
            result = task.enqueue(argument)
            DBTaskResult.objects.filter(pk=result.id).update(task_path=old_path)
            record = DBTaskResult.objects.get(pk=result.id)
            queued.append((record.pk, old_path, record.args_kwargs, record.status))
        editor = connection.schema_editor()
        migration.move_tasks(apps, editor)
        for pk, old_path, arguments, status in queued:
            with self.subTest(path=old_path):
                record = DBTaskResult.objects.get(pk=pk)
                self.assertEqual(record.task_path, migration.TASK_PATHS[old_path])
                self.assertEqual(record.args_kwargs, arguments)
                self.assertEqual(record.status, status)
        migration.restore_tasks(apps, editor)
        for pk, old_path, _, _ in queued:
            self.assertEqual(DBTaskResult.objects.get(pk=pk).task_path, old_path)

    def test_feature_module_migration_preserves_existing_queue_records(self):
        migration = import_module("accounts.migrations.0006_group_account_modules")
        export = AccountDataExport.objects.create(user=self.user)
        deletion = DeletionRequest.objects.create(user=self.other)
        queued = []
        for task, argument, old_path in [
            (
                send_welcome_email,
                self.user.pk,
                "accounts.tasks.email.send_welcome_email",
            ),
            (
                send_password_reset_email,
                self.user.email,
                "accounts.tasks.email.send_password_reset_email",
            ),
            (
                send_password_changed_email,
                self.user.pk,
                "accounts.tasks.email.send_password_changed_email",
            ),
            (
                build_account_data_export,
                str(export.pk),
                "accounts.tasks.privacy.build_account_data_export",
            ),
            (
                delete_account_data,
                str(deletion.pk),
                "accounts.tasks.privacy.delete_account_data",
            ),
        ]:
            result = task.enqueue(argument)
            DBTaskResult.objects.filter(pk=result.id).update(task_path=old_path)
            record = DBTaskResult.objects.get(pk=result.id)
            queued.append((record.pk, old_path, record.args_kwargs, record.status))
        editor = connection.schema_editor()
        migration.move_tasks(apps, editor)
        for pk, old_path, arguments, status in queued:
            with self.subTest(path=old_path):
                record = DBTaskResult.objects.get(pk=pk)
                self.assertEqual(record.task_path, migration.TASK_PATHS[old_path])
                self.assertEqual(record.args_kwargs, arguments)
                self.assertEqual(record.status, status)
        migration.restore_tasks(apps, editor)
        for pk, old_path, _, _ in queued:
            self.assertEqual(DBTaskResult.objects.get(pk=pk).task_path, old_path)
