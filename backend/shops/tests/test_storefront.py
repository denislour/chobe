import io

from PIL import Image
from rest_framework.test import APIClient

from accounts.tests.base import AccountAPITestCase
from shops.models import Shop, ShopFollow
from shops.services.management import create_shop, update_shop


class StorefrontTests(AccountAPITestCase):
    def setUp(self):
        super().setUp()
        self.shop = create_shop(
            self.other,
            {
                "name": "Moc Home",
                "slug": "moc-home",
                "area": "Ha Noi",
                "description": "Furniture with a second life.",
            },
        )
        self.url = "/api/v1/shop-storefronts/moc-home/"
        self.image_url = "/api/v1/shop-storefronts/moc-home/images/logo/"
        self.public = APIClient(enforce_csrf_checks=True)

    def test_guest_reads_only_the_public_projection(self):
        response = self.public.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.data),
            {
                "id", "name", "slug", "description", "area", "contact_hours",
                "website_url", "social_url", "logo_url", "banner_url", "created_at",
                "is_following",
            },
        )
        self.assertFalse(response.data["is_following"])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertFalse(ShopFollow.objects.exists())
        self.assertEqual(self.public.patch(self.url, {}).status_code, 405)

    def test_follow_state_depends_on_the_current_viewer(self):
        ShopFollow.objects.create(user=self.user, shop=self.shop)
        self.assertTrue(self.client.get(self.url).data["is_following"])
        self.assertFalse(self.public.get(self.url).data["is_following"])
        self.client.force_login(self.other)
        self.assertFalse(self.client.get(self.url).data["is_following"])

    def test_old_slug_redirects_to_the_canonical_storefront(self):
        update_shop(self.shop, self.other, {"slug": "moc-living", "version": 1})
        response = self.public.get(self.url)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response["Location"], "/api/v1/shop-storefronts/moc-living/")
        self.assertIn("no-store", response["Cache-Control"])
        canonical = self.public.get(response["Location"])
        self.assertEqual(canonical.status_code, 200)
        self.assertEqual(canonical.data["slug"], "moc-living")

    def test_uuid_shaped_slug_has_a_distinct_public_route(self):
        slug = str(self.shop.pk)
        update_shop(self.shop, self.other, {"slug": slug, "version": 1})
        self.assertEqual(
            self.public.get(f"/api/v1/shop-storefronts/{slug}/").status_code, 200
        )
        self.assertEqual(
            self.public.get(f"/api/v1/shops/{self.shop.pk}/").status_code, 405
        )

    def test_public_images_recheck_shop_and_owner_visibility(self):
        output = io.BytesIO()
        Image.new("RGB", (8, 8), "red").save(output, format="JPEG")
        self.shop.logo = output.getvalue()
        self.shop.save(update_fields=("logo",))
        response = self.public.get(self.image_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), self.shop.logo)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("no-store", response["Cache-Control"])
        for status in (Shop.Status.PAUSED, Shop.Status.SUSPENDED, Shop.Status.CLOSED):
            with self.subTest(status=status):
                Shop.objects.filter(pk=self.shop.pk).update(status=status)
                self.assertEqual(self.public.get(self.url).status_code, 404)
                self.assertEqual(self.public.get(self.image_url).status_code, 404)
        Shop.objects.filter(pk=self.shop.pk).update(status=Shop.Status.ACTIVE)
        self.other.is_active = False
        self.other.save(update_fields=("is_active",))
        self.assertEqual(self.public.get(self.url).status_code, 404)
        self.assertEqual(self.public.get(self.image_url).status_code, 404)

    def test_unknown_and_missing_images_return_not_found(self):
        self.assertEqual(self.public.get(self.image_url).status_code, 404)
        self.assertEqual(
            self.public.get("/api/v1/shop-storefronts/moc-home/images/password/").status_code,
            404,
        )
        self.assertEqual(
            self.public.get("/api/v1/shop-storefronts/missing/").status_code, 404
        )
