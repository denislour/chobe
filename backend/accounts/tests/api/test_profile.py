import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import ConsentEvent, Profile
from accounts.services.privacy import privacy_for, public_listing_phone
from accounts.services.profile import profile_for
from accounts.tests.base import AccountAPITestCase


class ProfileTests(AccountAPITestCase):
    def test_current_profile_defaults_and_owner_cannot_be_changed(self):
        response = self.request("get", "me/profile")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["display_name"], self.user.username)
        self.assertEqual(response.data["email"], self.user.email)
        response = self.request(
            "patch",
            "me/profile",
            {
                "display_name": "A member",
                "phone": "+84912345678",
                "version": 1,
                "user": self.other.pk,
                "email": "changed@example.com",
                "is_staff": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["version"], 2)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "member@example.com")
        self.assertFalse(self.user.is_staff)
        self.assertFalse(Profile.objects.filter(user=self.other).exists())

    def test_validation_and_required_version(self):
        for payload in [
            {"display_name": ""},
            {"display_name": "x" * 81},
            {"phone": "0912345678"},
            {"bio": "x" * 201},
        ]:
            with self.subTest(payload=payload):
                self.assertEqual(
                    self.request(
                        "patch", "me/profile", payload | {"version": 1}
                    ).status_code,
                    400,
                )
        self.assertEqual(
            self.request("patch", "me/profile", {"bio": "hello"}).status_code, 400
        )

    def test_out_of_range_version_does_not_modify_profile(self):
        for version in (0, 2**63):
            with self.subTest(version=version):
                response = self.request(
                    "patch", "me/profile", {"bio": "not saved", "version": version}
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("version", response.data)
        self.assertEqual(profile_for(self.user).bio, "")

    def test_stale_version_does_not_overwrite_saved_profile(self):
        self.assertEqual(
            self.request(
                "patch", "me/profile", {"bio": "first", "version": 1}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.request(
                "patch", "me/profile", {"bio": "stale", "version": 1}
            ).status_code,
            409,
        )
        self.assertEqual(profile_for(self.user).bio, "first")

    def test_avatar_is_reencoded_private_and_can_be_removed(self):
        source = io.BytesIO()
        Image.new("RGB", (600, 300), "red").save(source, format="PNG")
        upload = SimpleUploadedFile(
            "avatar.png",
            source.getvalue() + b"<script>attack</script>",
            content_type="image/png",
        )
        response = self.client.patch(
            "/api/v1/me/profile/",
            {"avatar": upload, "version": 1},
            format="multipart",
            HTTP_X_XSRF_TOKEN=self.client.cookies["XSRF-TOKEN"].value,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("version=2", response.data["avatar_url"])
        response = self.request("get", "me/profile/avatar")
        body = b"".join(response.streaming_content)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn(b"<script>", body)
        with Image.open(io.BytesIO(body)) as image:
            self.assertEqual(image.size, (512, 256))
        self.assertEqual(APIClient().get("/api/v1/me/profile/avatar/").status_code, 403)
        self.assertEqual(
            self.request(
                "patch", "me/profile", {"remove_avatar": True, "version": 2}
            ).status_code,
            200,
        )
        self.assertEqual(self.request("get", "me/profile/avatar").status_code, 404)

    def test_fake_and_oversized_avatar_are_rejected(self):
        for body in [b"<html>fake</html>", b"x" * (2 * 1024 * 1024 + 1)]:
            with self.subTest(size=len(body)):
                upload = SimpleUploadedFile("fake.png", body, content_type="image/png")
                response = self.client.patch(
                    "/api/v1/me/profile/",
                    {"avatar": upload, "version": 1},
                    format="multipart",
                    HTTP_X_XSRF_TOKEN=self.client.cookies["XSRF-TOKEN"].value,
                )
                self.assertEqual(response.status_code, 400)
                self.assertFalse(profile_for(self.user).avatar)

    def test_phone_change_withdraws_consent_and_public_projection_reads_fresh_values(
        self,
    ):
        profile = profile_for(self.user)
        profile.phone = "+84912345678"
        profile.save()
        privacy = privacy_for(self.user)
        privacy.share_phone = True
        privacy.save()
        self.assertEqual(
            public_listing_phone(self.user, is_public_listing=True), profile.phone
        )
        self.assertIsNone(public_listing_phone(self.user, is_public_listing=False))
        self.assertEqual(
            self.request(
                "patch", "me/profile", {"phone": "+84912345679", "version": 1}
            ).status_code,
            200,
        )
        self.assertFalse(privacy_for(self.user).share_phone)
        self.assertFalse(ConsentEvent.objects.get(user=self.user).share_phone)
        self.assertIsNone(public_listing_phone(self.user, is_public_listing=True))

    def test_auth_csrf_and_unsupported_methods(self):
        self.assertEqual(APIClient().get("/api/v1/me/profile/").status_code, 403)
        self.assertEqual(
            self.client.patch(
                "/api/v1/me/profile/", {"version": 1}, format="json"
            ).status_code,
            403,
        )
        self.assertEqual(self.request("delete", "me/profile").status_code, 405)
