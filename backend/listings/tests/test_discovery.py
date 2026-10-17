from accounts.models import PrivacySettings
from listings.tests.base import ListingAPITestCase


class MarketplaceDiscoveryTests(ListingAPITestCase):
    def test_home_and_search_include_only_eligible_approved_items(self):
        public = self.approve(self.create_draft())
        self.create_draft(self.values | {"title": "Private draft"})
        self.assertEqual(
            self.public.get("/api/v1/home/").data["latest"][0]["id"], public.pk
        )
        self.assertEqual(self.public.get("/api/v1/listings/").data["count"], 1)
        self.shop.status = "suspended"
        self.shop.save()
        self.assertEqual(self.public.get("/api/v1/listings/").data["count"], 0)
        self.assertEqual(
            self.public.get(f"/api/v1/listings/{public.pk}/").status_code, 404
        )

    def test_search_finds_vietnamese_words_with_and_without_accents(self):
        listing = self.approve(self.create_draft())
        for query in ("Điện thoại", "dien thoai", "thoai", "demo"):
            with self.subTest(query=query):
                response = self.public.get("/api/v1/listings/", {"q": query})
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data["results"][0]["id"], listing.pk)

    def test_search_validates_filters_and_does_not_accept_fts_syntax(self):
        self.approve(self.create_draft())
        self.assertEqual(
            self.public.get(
                "/api/v1/listings/", {"price_min": 20, "price_max": 10}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.public.get("/api/v1/listings/", {"sort": "secret"}).status_code, 400
        )
        self.assertEqual(
            self.public.get(
                "/api/v1/listings/",
                {"attributes": '{"__class__":true}', "category": str(self.category.pk)},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.public.get("/api/v1/listings/", {"q": '" OR * - NOT'}).status_code, 200
        )

    def test_price_location_and_typed_attribute_filters_use_public_snapshot(self):
        self.approve(self.create_draft())
        response = self.public.get(
            "/api/v1/listings/",
            {
                "category": str(self.category.pk),
                "location": "Ha Noi",
                "price_min": 999999,
                "attributes": '{"tested":false}',
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            self.public.get("/api/v1/listings/", {"price_min": 1000001}).data["count"],
            0,
        )
        self.assertEqual(
            self.public.get(
                "/api/v1/listings/",
                {"category": str(self.category.pk), "attributes": '{"tested":"false"}'},
            ).status_code,
            400,
        )

    def test_phone_requires_both_listing_and_current_account_consent(self):
        listing = self.approve(self.create_draft())
        self.assertEqual(
            self.public.get(f"/api/v1/listings/{listing.pk}/").data["phone"],
            "+84901234567",
        )
        PrivacySettings.objects.filter(user=self.user).update(share_phone=False)
        self.assertIsNone(
            self.public.get(f"/api/v1/listings/{listing.pk}/").data["phone"]
        )
        self.assertEqual(
            self.public.post(
                f"/api/v1/listings/{listing.pk}/events/",
                {"kind": "call"},
                format="json",
            ).status_code,
            400,
        )

















    def test_listing_phone_withdrawal_takes_effect_without_another_review(self):
        listing = self.approve(self.create_draft())
        response = self.request(
            "patch",
            f"me/listings/{listing.pk}",
            {"version": listing.version, "phone_consent": False},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(
            self.public.get(f"/api/v1/listings/{listing.pk}/").data["phone"]
        )

