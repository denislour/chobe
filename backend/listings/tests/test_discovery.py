from accounts.models import PrivacySettings, ViewingHistory
from listings.models import (
    Favorite,
    Listing,
    Notification,
    NotificationPreference,
    Report,
    SavedSearch,
)
from listings.services.notifications import match_searches, send_notification_email
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

    def test_comparison_limits_ids_and_does_not_expose_private_items(self):
        listing = self.approve(self.create_draft())
        private = self.create_draft()
        response = self.public.get(
            "/api/v1/listings/compare/", {"ids": f"{listing.pk},{private.pk}"}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["unavailable"], [private.pk])
        self.assertEqual(len(response.data["results"]), 1)
        for ids in ("1,1", "1,2,3,4", "bad", "-1"):
            self.assertEqual(
                self.public.get("/api/v1/listings/compare/", {"ids": ids}).status_code,
                400,
            )

    def test_saved_searches_validate_filters_and_require_current_version(self):
        response = self.request(
            "post",
            "me/saved-searches",
            {"name": "Phones", "filters": {"q": "demo"}, "frequency": "immediate"},
        )
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        self.assertEqual(
            self.admin_request("get", f"me/saved-searches/{pk}").status_code, 404
        )
        self.assertEqual(
            self.request(
                "patch", f"me/saved-searches/{pk}", {"version": 1, "name": "New name"}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.request(
                "patch", f"me/saved-searches/{pk}", {"version": 1, "name": "Lost"}
            ).status_code,
            409,
        )
        self.assertEqual(
            self.request(
                "post",
                "me/saved-searches",
                {"name": "Unsafe", "filters": {"private": "secret"}},
            ).status_code,
            400,
        )

    def test_matching_requires_consent_and_deduplicates_notifications(self):
        SavedSearch.objects.create(
            user=self.user, name="Phones", filters={"q": "demo"}, frequency="immediate"
        )
        listing = self.approve(self.create_draft())
        self.assertEqual(match_searches(listing.pk, listing.published["version"]), 0)
        NotificationPreference.objects.create(user=self.user, inbox=True, email=False)
        self.assertEqual(match_searches(listing.pk, listing.published["version"]), 1)
        self.assertEqual(match_searches(listing.pk, listing.published["version"]), 0)
        notification = Notification.objects.get()
        self.assertEqual(notification.email_status, "blocked")
        self.assertEqual(
            self.request("get", "me/notifications").data["results"][0]["title"],
            self.values["title"],
        )
        self.assertEqual(
            self.admin_request(
                "post", f"me/notifications/{notification.pk}/read", {}
            ).status_code,
            404,
        )

    def test_email_rechecks_opt_in_and_visibility_before_sending(self):
        SavedSearch.objects.create(
            user=self.user, name="Phones", filters={}, frequency="immediate"
        )
        preferences = NotificationPreference.objects.create(
            user=self.user, inbox=True, email=True
        )
        listing = self.approve(self.create_draft())
        match_searches(listing.pk, listing.published["version"])
        notification = Notification.objects.get()
        preferences.email = False
        preferences.save()
        self.assertFalse(send_notification_email(notification.pk))
        notification.refresh_from_db()
        self.assertEqual(notification.email_status, "blocked")

    def test_daily_matching_and_read_actions_are_private_and_idempotent(self):
        SavedSearch.objects.create(
            user=self.user, name="Daily", filters={}, frequency="daily"
        )
        NotificationPreference.objects.create(user=self.user, inbox=True)
        listing = self.approve(self.create_draft())
        self.assertEqual(match_searches(listing.pk, listing.published["version"]), 0)
        self.assertEqual(match_searches(frequency="daily"), 1)
        notification = Notification.objects.get()
        for _ in range(2):
            self.assertEqual(
                self.request(
                    "post", f"me/notifications/{notification.pk}/read", {}
                ).status_code,
                200,
            )
        self.assertEqual(
            self.request("post", "me/notifications/read-all", {}).status_code, 204
        )
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    def test_notification_preferences_require_current_version(self):
        data = self.request("get", "me/notification-preferences/me").data
        self.assertFalse(data["inbox"])
        self.assertEqual(
            self.request(
                "patch",
                "me/notification-preferences/me",
                {"version": data["version"], "inbox": True},
            ).status_code,
            200,
        )
        self.assertEqual(
            self.request(
                "patch",
                "me/notification-preferences/me",
                {"version": data["version"], "email": True},
            ).status_code,
            409,
        )

    def test_report_requires_login_and_duplicate_reports_return_one_receipt(self):
        listing = self.approve(self.create_draft())
        values = {
            "listing": listing.pk,
            "reason": "incorrect",
            "description": "The description needs checking.",
        }
        self.assertEqual(
            self.public.post("/api/v1/me/reports/", values, format="json").status_code,
            403,
        )
        first = self.request("post", "me/reports", values)
        second = self.request("post", "me/reports", values)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Report.objects.count(), 1)
        self.assertEqual(self.admin_request("get", "me/reports").data["count"], 0)

    def test_reports_validate_targets_and_do_not_publish_reporter_identity(self):
        listing = self.approve(self.create_draft())
        values = {
            "listing": listing.pk,
            "shop": str(self.shop.pk),
            "reason": "fraud",
            "description": "Concern",
        }
        self.assertEqual(self.request("post", "me/reports", values).status_code, 400)
        response = self.request(
            "post",
            "me/reports",
            {
                "shop": str(self.shop.pk),
                "reason": "spam",
                "description": "Repeated content.",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("reporter", response.data)
        self.assertNotIn("reporter_id", response.data)

    def test_report_decision_hides_listing_with_audit_and_safe_response(self):
        listing = self.approve(self.create_draft())
        report = self.request(
            "post",
            "me/reports",
            {"listing": listing.pk, "reason": "incorrect", "description": "Concern"},
        ).data
        values = {
            "version": report["version"],
            "action": "hide_listing",
            "reason": "Internal evidence reviewed.",
            "response": "We reviewed your report and took action.",
        }
        self.assertEqual(
            self.request(
                "post", f"admin/reports/{report['id']}/decision", values
            ).status_code,
            403,
        )
        response = self.admin_request(
            "post", f"admin/reports/{report['id']}/decision", values
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            self.public.get(f"/api/v1/listings/{listing.pk}/").status_code, 404
        )
        safe = self.request("get", f"me/reports/{report['id']}").data
        self.assertNotIn("Internal evidence", str(safe))
        self.assertEqual(safe["response"], values["response"])
        self.assertEqual(
            self.admin_request(
                "post", f"admin/reports/{report['id']}/decision", values
            ).status_code,
            409,
        )
        self.assertEqual(Report.objects.get().decisions.count(), 1)

    def test_report_admin_can_suspend_the_target_shop(self):
        self.approve(self.create_draft())
        report = self.request(
            "post",
            "me/reports",
            {"shop": str(self.shop.pk), "reason": "fraud", "description": "Concern"},
        ).data
        response = self.admin_request(
            "post",
            f"admin/reports/{report['id']}/decision",
            {
                "version": 1,
                "action": "suspend_shop",
                "reason": "Reviewed the evidence.",
                "response": "We took action.",
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.status, "suspended")
        self.assertEqual(self.public.get("/api/v1/listings/").data["count"], 0)


    def test_queued_email_is_blocked_when_search_filters_no_longer_match(self):
        search = SavedSearch.objects.create(
            user=self.user, name="Phones", filters={}, frequency="immediate"
        )
        NotificationPreference.objects.create(user=self.user, inbox=True, email=True)
        listing = self.approve(self.create_draft())
        match_searches(listing.pk, listing.published["version"])
        notification = Notification.objects.get()
        search.filters = {"price_min": 1000001}
        search.save()
        self.assertFalse(send_notification_email(notification.pk))
        notification.refresh_from_db()
        self.assertEqual(notification.email_status, "blocked")

    def test_nonpublic_items_cannot_be_added_to_favorites_or_reported(self):
        listing = self.create_draft()
        self.assertEqual(
            self.request("put", f"me/favorites/{listing.pk}", {}).status_code, 404
        )
        self.assertEqual(
            self.request(
                "post",
                "me/reports",
                {
                    "listing": listing.pk,
                    "reason": "spam",
                    "description": "Private target",
                },
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

    def test_owner_cannot_restore_a_listing_hidden_by_report_review(self):
        listing = self.approve(self.create_draft())
        report = self.request(
            "post",
            "me/reports",
            {"listing": listing.pk, "reason": "fraud", "description": "Concern"},
        ).data
        self.admin_request(
            "post",
            f"admin/reports/{report['id']}/decision",
            {
                "version": 1,
                "action": "hide_listing",
                "reason": "Reviewed",
                "response": "We took action.",
            },
        )
        listing.refresh_from_db()
        self.assertTrue(listing.moderation_hold)
        response = self.request(
            "post",
            f"me/listings/{listing.pk}/status",
            {"version": listing.version, "status": "active"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.public.get(f"/api/v1/listings/{listing.pk}/").status_code, 404
        )
