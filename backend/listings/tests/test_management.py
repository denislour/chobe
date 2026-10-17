from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django_tasks_db.models import DBTaskResult

from listings.models import Listing, ListingRevision
from listings.services.management import cleanup_inactive_listings, six_months_after
from listings.tests.base import ListingAPITestCase


class ListingManagementTests(ListingAPITestCase):

    def test_owner_cannot_read_or_edit_another_owners_draft(self):
        listing = self.create_draft()
        self.assertEqual(
            self.admin_request("get", f"me/listings/{listing.pk}").status_code, 404
        )
        self.assertEqual(
            self.admin_request(
                "patch", f"me/listings/{listing.pk}", {"version": 1, "title": "Attack"}
            ).status_code,
            404,
        )

    def test_create_requires_an_active_shop_and_ignores_owner_input(self):
        self.shop.status = "suspended"
        self.shop.save()
        self.assertEqual(
            self.request("post", "me/listings", self.values).status_code, 400
        )
        self.shop.status = "active"
        self.shop.save()
        self.assertEqual(
            self.request(
                "post", "me/listings", self.values | {"shop": str(self.shop.pk)}
            ).status_code,
            400,
        )

    def test_patch_requires_current_version(self):
        listing = self.create_draft()
        first = self.request(
            "patch", f"me/listings/{listing.pk}", {"version": 1, "title": "Updated"}
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(
            self.request(
                "patch", f"me/listings/{listing.pk}", {"version": 1, "title": "Lost"}
            ).status_code,
            409,
        )
        self.assertEqual(
            self.request(
                "patch", f"me/listings/{listing.pk}", {"title": "Missing version"}
            ).status_code,
            400,
        )
        listing.refresh_from_db()
        self.assertEqual(listing.title, "Updated")

    def test_submit_validates_required_data_and_current_schema(self):
        listing = self.create_draft()
        self.assertEqual(
            self.request(
                "post", f"me/listings/{listing.pk}/submit", {"version": 1}
            ).status_code,
            400,
        )
        self.upload(listing)
        listing.schema_version = 1
        listing.save()
        self.assertEqual(
            self.request(
                "post", f"me/listings/{listing.pk}/submit", {"version": listing.version}
            ).status_code,
            409,
        )
        self.assertFalse(ListingRevision.objects.exists())

    def test_false_boolean_is_valid_and_duplicate_submission_is_idempotent(self):
        listing = self.create_draft()
        self.submit(listing)
        response = self.request(
            "post", f"me/listings/{listing.pk}/submit", {"version": listing.version}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(listing.revisions.count(), 1)
        self.assertFalse(listing.revisions.get().snapshot["attributes"]["tested"])

    def test_invalid_image_bytes_do_not_advance_the_version(self):
        listing = self.create_draft()
        response = self.client.post(
            f"/api/v1/me/listings/{listing.pk}/images/",
            {
                "version": 1,
                "image": SimpleUploadedFile(
                    "bad.jpg", b"<svg>bad</svg>", content_type="image/jpeg"
                ),
            },
            format="multipart",
            HTTP_X_XSRF_TOKEN=self.client.cookies[settings.CSRF_COOKIE_NAME].value,
        )
        self.assertEqual(response.status_code, 400)
        listing.refresh_from_db()
        self.assertEqual(listing.version, 1)
        self.assertFalse(listing.images.exists())

    def test_photo_reordering_rejects_duplicates_and_foreign_assets(self):
        listing = self.upload(self.create_draft())
        image = str(listing.images.get().pk)
        self.assertEqual(
            self.request(
                "post",
                f"me/listings/{listing.pk}/images/order",
                {"version": listing.version, "images": [image, image]},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.request(
                "post",
                f"me/listings/{listing.pk}/images/order",
                {
                    "version": listing.version,
                    "images": ["00000000-0000-0000-0000-000000000000"],
                },
            ).status_code,
            400,
        )

    def test_manual_approval_publishes_only_the_submitted_snapshot(self):
        listing = self.approve(self.create_draft())
        response = self.public.get(f"/api/v1/listings/{listing.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], self.values["title"])
        self.assertNotIn("rights_confirmed", response.data)
        self.assertTrue(
            DBTaskResult.objects.filter(
                task_path="listings.tasks.notifications.match_listing_searches"
            ).exists()
        )

    def test_manual_rejection_can_be_appealed_and_overridden_with_audit(self):
        listing = self.create_draft()
        case = self.submit(listing)
        response = self.admin_request(
            "post",
            f"admin/moderation/{case.pk}/decision",
            {
                "version": case.version,
                "decision": "reject",
                "reason": "Please clarify the condition.",
            },
        )
        self.assertEqual(response.status_code, 200)
        listing.refresh_from_db()
        self.assertEqual(
            self.public.get(f"/api/v1/listings/{listing.pk}/").status_code, 404
        )
        self.assertEqual(
            self.request(
                "post",
                f"me/listings/{listing.pk}/appeal",
                {
                    "version": listing.version,
                    "reason": "The description explains the condition.",
                },
            ).status_code,
            200,
        )
        case.refresh_from_db()
        response = self.admin_request(
            "post",
            f"admin/moderation/{case.pk}/decision",
            {
                "version": case.version,
                "decision": "approve",
                "reason": "Reviewed the appeal and approved.",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.public.get(f"/api/v1/listings/{listing.pk}/").status_code, 200
        )
        self.assertEqual(
            listing.audit_events.filter(action__in=("approve", "reject")).count(), 2
        )

    def test_owner_cannot_moderate_and_admin_cannot_skip_csrf(self):
        listing = self.create_draft()
        case = self.submit(listing)
        data = {"version": case.version, "decision": "approve", "reason": "Approved"}
        self.assertEqual(
            self.request(
                "post", f"admin/moderation/{case.pk}/decision", data
            ).status_code,
            403,
        )
        self.assertEqual(
            self.admin_client.post(
                f"/api/v1/admin/moderation/{case.pk}/decision/", data, format="json"
            ).status_code,
            403,
        )

    def test_new_draft_makes_the_previous_moderation_result_stale(self):
        listing = self.create_draft()
        case = self.submit(listing)
        self.request(
            "patch",
            f"me/listings/{listing.pk}",
            {"version": listing.version, "title": "New draft"},
        )
        response = self.admin_request(
            "post",
            f"admin/moderation/{case.pk}/decision",
            {
                "version": case.version,
                "decision": "approve",
                "reason": "Stale approval",
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(Listing.objects.get(pk=listing.pk).published)

    def test_edit_and_remove_photo_do_not_change_the_live_snapshot(self):
        listing = self.approve(self.create_draft())
        old_image = listing.published["images"][0]
        response = self.request(
            "patch",
            f"me/listings/{listing.pk}",
            {"version": listing.version, "title": "Private new title"},
        )
        response = self.request(
            "post",
            f"me/listings/{listing.pk}/images/order",
            {"version": response.data["version"], "images": []},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.public.get(f"/api/v1/listings/{listing.pk}/").data["title"],
            self.values["title"],
        )
        self.assertEqual(
            self.public.get(
                f"/api/v1/listings/{listing.pk}/image/{old_image}/"
            ).status_code,
            200,
        )

    def test_status_requires_approval_and_sold_items_leave_public_results(self):
        listing = self.create_draft()
        self.assertEqual(
            self.request(
                "post",
                f"me/listings/{listing.pk}/status",
                {"version": 1, "status": "active"},
            ).status_code,
            400,
        )
        self.approve(listing)
        response = self.request(
            "post",
            f"me/listings/{listing.pk}/status",
            {"version": listing.version, "status": "sold"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.public.get(f"/api/v1/listings/{listing.pk}/").status_code, 404
        )

    def test_owner_summary_and_csv_are_private_and_escape_formulas(self):
        listing = self.create_draft(self.values | {"title": "=SUM(A1:A2)"})
        self.assertEqual(self.request("get", "me/listings/summary").data, {"draft": 1})
        response = self.request("get", "me/listings/export")
        self.assertIn("'=SUM", response.content.decode())
        self.assertNotIn(
            str(listing.pk),
            self.admin_request("get", "me/listings/export").content.decode(),
        )

    def test_retention_uses_calendar_months_and_public_reads_do_not_renew(self):
        value = datetime(2026, 8, 31, tzinfo=UTC)
        self.assertEqual(six_months_after(value), datetime(2027, 2, 28, tzinfo=UTC))
        listing = self.approve(self.create_draft())
        deadline = listing.retention_due_at
        self.public.get(f"/api/v1/listings/{listing.pk}/")
        listing.refresh_from_db()
        self.assertEqual(listing.retention_due_at, deadline)

    def test_expired_listings_are_hidden_before_cleanup_and_erased_once(self):
        listing = self.approve(self.create_draft())
        Listing.objects.filter(pk=listing.pk).update(
            retention_due_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(self.public.get("/api/v1/listings/").data["count"], 0)
        self.assertEqual(cleanup_inactive_listings(), 1)
        self.assertEqual(cleanup_inactive_listings(), 0)
        listing.refresh_from_db()
        self.assertEqual(listing.status, "deleted")
        self.assertFalse(listing.published)
        self.assertFalse(listing.images.exists())
        self.assertFalse(listing.revisions.exists())

    def test_renewal_prevents_cleanup_and_deleted_items_cannot_be_restored(self):
        listing = self.create_draft()
        Listing.objects.filter(pk=listing.pk).update(
            retention_due_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(
            self.request(
                "post", f"me/listings/{listing.pk}/renew", {"version": listing.version}
            ).status_code,
            200,
        )
        self.assertEqual(cleanup_inactive_listings(), 0)
        listing.refresh_from_db()
        self.assertEqual(
            self.request(
                "delete", f"me/listings/{listing.pk}", {"version": listing.version}
            ).status_code,
            204,
        )
        self.assertEqual(
            self.request(
                "post",
                f"me/listings/{listing.pk}/renew",
                {"version": listing.version + 1},
            ).status_code,
            404,
        )

    def test_submitted_revision_is_immutable(self):
        from django.core.exceptions import ValidationError

        listing = self.create_draft()
        self.submit(listing)
        revision = listing.revisions.get()
        revision.snapshot["title"] = "Changed after submission"
        with self.assertRaises(ValidationError):
            revision.save()
        self.assertEqual(
            listing.revisions.get().snapshot["title"], self.values["title"]
        )

    def test_hiding_a_submission_withdraws_it_from_the_moderation_queue(self):
        listing = self.create_draft()
        case = self.submit(listing)
        self.assertEqual(
            self.request(
                "post",
                f"me/listings/{listing.pk}/status",
                {"version": listing.version, "status": "hidden"},
            ).status_code,
            200,
        )
        response = self.admin_request(
            "post",
            f"admin/moderation/{case.pk}/decision",
            {"version": case.version, "decision": "approve", "reason": "Late decision"},
        )
        self.assertEqual(response.status_code, 409)

