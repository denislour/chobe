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
from accounts.tasks.account_data import build_account_data_export
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
            client.get(f"/api/v1/me/profile/?receipt={receipt}").status_code, 403
        )
        self.assertEqual(
            client.post(f"/api/v1/account-deletion-status/{receipt}/", {}).status_code,
            405,
        )


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
