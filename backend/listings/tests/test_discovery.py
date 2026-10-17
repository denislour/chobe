from accounts.models import PrivacySettings, ViewingHistory
from listings.models import Favorite, Listing
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

    def test_contact_events_are_aggregate_counts_and_never_owner_activity(self):
        listing = self.approve(self.create_draft())
        deadline = listing.retention_due_at
        response = self.public.post(
            f"/api/v1/listings/{listing.pk}/events/", {"kind": "call"}, format="json"
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(listing.listingmetric_set.get(kind="call").count, 1)
        listing.refresh_from_db()
        self.assertEqual(listing.retention_due_at, deadline)

    def test_favorites_are_idempotent_private_and_hide_unavailable_items(self):
        listing = self.approve(self.create_draft())
        for _ in range(2):
            self.assertEqual(
                self.request("put", f"me/favorites/{listing.pk}", {}).status_code, 204
            )
        self.assertEqual(Favorite.objects.count(), 1)
        self.assertEqual(self.request("get", "me/favorites").data["count"], 1)
        self.assertEqual(self.admin_request("get", "me/favorites").data["count"], 0)
        self.assertEqual(
            self.public.put(
                f"/api/v1/me/favorites/{listing.pk}/", {}, format="json"
            ).status_code,
            403,
        )
        Listing.objects.filter(pk=listing.pk).update(status="hidden")
        self.assertEqual(self.request("get", "me/favorites").data["count"], 0)
        self.assertEqual(
            self.request("delete", f"me/favorites/{listing.pk}").status_code, 204
        )

    def test_history_respects_privacy_and_returns_only_public_items(self):
        listing = self.approve(self.create_draft())
        response = self.request(
            "post", "me/viewing-history", {"listing_id": listing.pk}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.request("get", "me/favorites/history").data[0]["id"], listing.pk
        )
        PrivacySettings.objects.filter(user=self.user).update(record_history=False)
        ViewingHistory.objects.all().delete()
        self.assertEqual(
            self.request(
                "post", "me/viewing-history", {"listing_id": listing.pk}
            ).status_code,
            204,
        )
        self.assertFalse(ViewingHistory.objects.exists())
        self.assertEqual(self.request("get", "me/favorites/history").data, [])














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

