from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import ConsentEvent, ViewingHistory
from accounts.services.privacy import privacy_for, public_listing_phone
from accounts.services.profile import profile_for
from accounts.tests.base import AccountAPITestCase


class PrivacyTests(AccountAPITestCase):
    def test_defaults_and_phone_required_before_sharing(self):
        response = self.request("get", "privacy-settings/me")
        self.assertFalse(response.data["share_phone"])
        self.assertTrue(response.data["record_history"])
        self.assertEqual(
            self.request(
                "patch", "privacy-settings/me", {"share_phone": True, "version": 1}
            ).status_code,
            400,
        )

    def test_consent_has_timestamp_policy_version_and_immediate_withdrawal(self):
        profile = profile_for(self.user)
        profile.phone = "+84912345678"
        profile.save()
        for value, version in [(True, 1), (False, 2)]:
            response = self.request(
                "patch",
                "privacy-settings/me",
                {"share_phone": value, "version": version},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.data["consent_at"])
            self.assertEqual(
                ConsentEvent.objects.filter(user=self.user).count(), version
            )
        self.assertEqual(ConsentEvent.objects.first().policy_version, 1)
        self.assertIsNone(public_listing_phone(self.user, is_public_listing=True))
        self.assertEqual(
            self.request(
                "patch", "privacy-settings/me", {"share_phone": True, "version": 1}
            ).status_code,
            409,
        )

    def test_history_is_owner_scoped_deduplicated_and_can_be_cleared(self):
        ViewingHistory.objects.create(user=self.other, listing_id=999)
        for _ in range(2):
            self.assertEqual(
                self.request(
                    "post", "me/viewing-history", {"listing_id": 12}
                ).status_code,
                201,
            )
        response = self.request("get", "me/viewing-history")
        self.assertEqual([entry["listing_id"] for entry in response.data], [12])
        self.assertEqual(self.request("delete", "me/viewing-history/clear").status_code, 204)
        self.assertTrue(ViewingHistory.objects.filter(user=self.other).exists())
        self.assertFalse(ViewingHistory.objects.filter(user=self.user).exists())

    def test_opt_out_removes_history_and_prevents_new_records(self):
        self.request("post", "me/viewing-history", {"listing_id": 1})
        response = self.request(
            "patch", "privacy-settings/me", {"record_history": False, "version": 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.request("post", "me/viewing-history", {"listing_id": 2}).status_code,
            204,
        )
        self.assertFalse(ViewingHistory.objects.filter(user=self.user).exists())
        self.assertEqual(self.request("get", "me/viewing-history").data, [])

    def test_history_retention_limit_and_invalid_input(self):
        ViewingHistory.objects.bulk_create(
            [ViewingHistory(user=self.user, listing_id=i) for i in range(1, 102)]
        )
        ViewingHistory.objects.filter(user=self.user, listing_id=1).update(
            viewed_at=timezone.now() - timedelta(days=31)
        )
        response = self.request("get", "me/viewing-history")
        self.assertEqual(len(response.data), 100)
        self.assertNotIn(1, [entry["listing_id"] for entry in response.data])
        self.request("post", "me/viewing-history", {"listing_id": 102})
        self.assertEqual(ViewingHistory.objects.filter(user=self.user).count(), 100)
        self.assertEqual(
            self.request("post", "me/viewing-history", {"listing_id": 0}).status_code,
            400,
        )

    def test_out_of_range_integer_inputs_are_rejected_without_writes(self):
        for listing_id in (-1, 0, 2**63):
            with self.subTest(listing_id=listing_id):
                response = self.request(
                    "post", "me/viewing-history", {"listing_id": listing_id}
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("listing_id", response.data)
        self.assertFalse(ViewingHistory.objects.filter(user=self.user).exists())
        for version in (0, 2**63):
            with self.subTest(version=version):
                response = self.request(
                    "patch",
                    "privacy-settings/me",
                    {"record_history": False, "version": version},
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("version", response.data)
        self.assertTrue(privacy_for(self.user).record_history)

    def test_private_endpoints_require_session_csrf_and_version(self):
        self.assertEqual(
            APIClient().get("/api/v1/privacy-settings/me/").status_code, 403
        )
        self.assertEqual(
            self.request(
                "patch", "privacy-settings/me", {"record_history": False}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.delete("/api/v1/me/viewing-history/clear/").status_code, 403
        )
        self.assertTrue(privacy_for(self.user).record_history)
