from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import ConsentEvent, ViewingHistory
from accounts.services.privacy import privacy_for, public_listing_phone
from accounts.services.profile import profile_for
from accounts.tests.base import AccountAPITestCase


class PrivacyTests(AccountAPITestCase):
    def test_defaults_and_phone_required_before_sharing(self):
        response = self.request("get", "me/privacy-settings")
        self.assertFalse(response.data["share_phone"])
        self.assertTrue(response.data["record_history"])
        self.assertEqual(
            self.request(
                "patch", "me/privacy-settings", {"share_phone": True, "version": 1}
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
                "me/privacy-settings",
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
                "patch", "me/privacy-settings", {"share_phone": True, "version": 1}
            ).status_code,
            409,
        )
