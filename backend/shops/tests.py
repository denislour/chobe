import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from accounts.constants import DEMO_ADMIN_PASSWORD
from accounts.models import User
from accounts.tests.base import AccountAPITestCase
from shops.models import Shop, ShopAuditEvent, ShopSlug
from shops.services.moderation import moderate_shop


class ShopTests(AccountAPITestCase):
    def setUp(self):
        super().setUp()
        self.values = {
            "name": "Moc Home",
            "slug": "moc-home",
            "area": "Ha Noi",
            "description": "Furniture with a second life.",
        }

    def create_shop(self):
        response = self.request("post", "shops", self.values)
        self.assertEqual(response.status_code, 201)
        return Shop.objects.get(pk=response.data["id"])

    def test_create_is_owner_scoped_and_only_one_shop_is_allowed(self):
        self.assertEqual(self.request("get", "me/shop").status_code, 404)
        response = self.request(
            "post",
            "shops",
            self.values | {"owner": self.other.pk, "status": "suspended"},
        )
        self.assertEqual(response.status_code, 201)
        shop = Shop.objects.get()
        self.assertEqual(shop.owner, self.user)
        self.assertEqual(shop.status, "active")
        duplicate = self.request(
            "post", "shops", self.values | {"slug": "another-shop"}
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(Shop.objects.count(), 1)
        self.assertEqual(self.request("get", "me/shop").data["id"], str(shop.pk))

    def test_other_owners_cannot_update_preview_or_read_images(self):
        shop = self.create_shop()
        self.client.force_login(self.other)
        update = self.request(
            "patch", f"shops/{shop.pk}", {"name": "Stolen", "version": 1}
        )
        self.assertEqual(update.status_code, 404)
        self.assertEqual(
            self.request("get", f"shops/{shop.slug}/preview").status_code, 404
        )
        self.assertEqual(
            self.request("get", f"shops/{shop.pk}/images/logo").status_code, 404
        )
        status = self.request(
            "post", f"shops/{shop.pk}/status", {"status": "closed", "version": 1}
        )
        self.assertEqual(status.status_code, 404)

    def test_slug_changes_reserve_old_addresses_and_do_not_allow_takeover(self):
        shop = self.create_shop()
        response = self.request(
            "patch", f"shops/{shop.pk}", {"slug": "moc-living", "version": 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["version"], 2)
        self.assertEqual(
            self.request("get", "shops/moc-home/preview").data["slug"], "moc-living"
        )
        self.client.force_login(self.other)
        self.assertEqual(self.request("post", "shops", self.values).status_code, 400)
        self.assertEqual(ShopSlug.objects.filter(shop=shop).count(), 2)

    def test_stale_versions_do_not_overwrite_shop_or_change_status(self):
        shop = self.create_shop()
        saved = self.request(
            "patch", f"shops/{shop.pk}", {"name": "Moc Living", "version": 1}
        )
        stale = self.request(
            "patch", f"shops/{shop.pk}", {"name": "Stale", "version": 1}
        )
        status = self.request(
            "post", f"shops/{shop.pk}/status", {"status": "paused", "version": 1}
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(status.status_code, 409)
        shop.refresh_from_db()
        self.assertEqual(shop.name, "Moc Living")
        self.assertEqual(shop.status, "active")

    def test_pause_can_be_reopened_and_closure_is_permanent(self):
        shop = self.create_shop()
        for version, status in [(1, "paused"), (2, "active"), (3, "closed")]:
            response = self.request(
                "post",
                f"shops/{shop.pk}/status",
                {"status": status, "version": version},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["version"], version + 1)
        reopen = self.request(
            "post", f"shops/{shop.pk}/status", {"status": "active", "version": 4}
        )
        update = self.request(
            "patch", f"shops/{shop.pk}", {"name": "Changed", "version": 4}
        )
        self.assertEqual(reopen.status_code, 400)
        self.assertEqual(update.status_code, 400)
        self.assertEqual(
            ShopAuditEvent.objects.filter(shop=shop, action="status_changed").count(), 3
        )

    def test_only_admin_can_suspend_and_restore_a_shop(self):
        shop = self.create_shop()
        with self.assertRaises(PermissionDenied):
            moderate_shop(shop.pk, self.user, suspend=True)
        admin = User.objects.create_superuser(
            "moderator", "moderator@example.com", "a-safe-password"
        )
        moderate_shop(shop.pk, admin, suspend=True)
        reopen = self.request(
            "post", f"shops/{shop.pk}/status", {"status": "active", "version": 2}
        )
        update = self.request(
            "patch",
            f"shops/{shop.pk}",
            {"description": "Corrected details", "version": 2},
        )
        self.assertEqual(reopen.status_code, 400)
        self.assertEqual(update.status_code, 200)
        moderate_shop(shop.pk, admin, suspend=False)
        shop.refresh_from_db()
        self.assertEqual(shop.status, "active")
        self.assertEqual(shop.version, 4)

    def test_images_are_reencoded_private_and_can_be_removed(self):
        shop = self.create_shop()
        data = io.BytesIO()
        Image.new("RGB", (1024, 1024), "red").save(data, format="PNG")
        response = self.client.patch(
            f"/api/v1/shops/{shop.pk}/",
            {
                "logo": SimpleUploadedFile(
                    "logo.png", data.getvalue(), content_type="image/png"
                ),
                "version": 1,
            },
            format="multipart",
            HTTP_X_XSRF_TOKEN=self.client.cookies["XSRF-TOKEN"].value,
        )
        self.assertEqual(response.status_code, 200)
        image = self.request("get", f"shops/{shop.pk}/images/logo")
        body = b"".join(image.streaming_content)
        with Image.open(io.BytesIO(body)) as decoded:
            self.assertEqual(decoded.format, "JPEG")
            self.assertEqual(decoded.size, (512, 512))
        self.assertIn("no-store", image["Cache-Control"])
        self.assertEqual(APIClient().get(response.data["logo_url"]).status_code, 403)
        removed = self.request(
            "patch", f"shops/{shop.pk}", {"remove_logo": True, "version": 2}
        )
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(
            self.request("get", f"shops/{shop.pk}/images/logo").status_code, 404
        )

    def test_oversized_uploads_are_rejected_without_modifying_shop(self):
        shop = self.create_shop()
        response = self.client.patch(
            f"/api/v1/shops/{shop.pk}/",
            {
                "logo": SimpleUploadedFile("large.png", b"x" * (2 * 1024 * 1024 + 1)),
                "version": 1,
            },
            format="multipart",
            HTTP_X_XSRF_TOKEN=self.client.cookies["XSRF-TOKEN"].value,
        )
        self.assertEqual(response.status_code, 400)
        shop.refresh_from_db()
        self.assertFalse(shop.logo)
        self.assertEqual(shop.version, 1)

    def test_validation_and_authentication_reject_invalid_changes(self):
        self.assertEqual(
            APIClient().post("/api/v1/shops/", self.values).status_code, 403
        )
        self.assertEqual(
            self.client.post("/api/v1/shops/", self.values).status_code, 403
        )
        for changes in [
            {"slug": "ADMIN"},
            {"slug": "admin"},
            {"name": ""},
            {"website_url": "javascript:alert(1)"},
            {"website_url": "https://user:password@example.com"},
        ]:
            with self.subTest(changes=changes):
                self.assertEqual(
                    self.request("post", "shops", self.values | changes).status_code,
                    400,
                )
        self.assertFalse(Shop.objects.exists())

    def test_export_includes_shop_and_account_deletion_removes_its_data(self):
        shop = self.create_shop()
        response = self.request("post", "me/data-exports", {})
        self.run_worker()
        payload = self.request(
            "get", f"me/data-exports/{response.data['job_id']}/download"
        ).json()
        self.assertEqual(payload["shop"]["slug"], shop.slug)
        self.assertNotIn("owner", payload["shop"])
        response = self.request(
            "post",
            "me/deletion-requests",
            {"password": DEMO_ADMIN_PASSWORD, "confirmation": "DELETE"},
        )
        self.assertEqual(response.status_code, 202)
        self.run_worker()
        self.assertFalse(Shop.objects.filter(pk=shop.pk).exists())
        self.assertFalse(ShopSlug.objects.filter(shop_id=shop.pk).exists())
        self.assertFalse(ShopAuditEvent.objects.filter(shop_id=shop.pk).exists())
