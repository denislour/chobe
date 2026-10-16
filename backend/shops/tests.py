import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from accounts.constants import DEMO_ADMIN_PASSWORD
from accounts.models import User
from accounts.tests.base import AccountAPITestCase
from shops.models import Shop, ShopAuditEvent, ShopSlug


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

    def test_stale_versions_do_not_overwrite_shop_or_change_status(self):
        shop = self.create_shop()
        saved = self.request(
            "patch", f"shops/{shop.pk}", {"name": "Moc Living", "version": 1}
        )
        stale = self.request(
            "patch", f"shops/{shop.pk}", {"name": "Stale", "version": 1}
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(stale.status_code, 409)
        shop.refresh_from_db()
        self.assertEqual(shop.name, "Moc Living")
        self.assertEqual(shop.status, "active")

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
