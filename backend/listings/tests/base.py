import io
from uuid import uuid4

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import PrivacySettings, Profile
from accounts.tests.base import AccountAPITestCase
from categories.models import Category
from listings.models import Listing
from moderation.models import ModerationCase
from shops.models import Shop


class ListingAPITestCase(AccountAPITestCase):
    def setUp(self):
        super().setUp()
        self.other.is_staff = True
        self.other.is_superuser = True
        self.other.save()
        self.admin_client = APIClient(enforce_csrf_checks=True)
        self.admin_client.force_login(self.other)
        self.admin_client.get("/api/v1/auth/session/")
        self.public = APIClient(enforce_csrf_checks=True)
        self.shop = Shop.objects.create(
            owner=self.user,
            name="Demo shop",
            slug="demo-shop",
            description="Demo items",
            area="Ha Noi",
        )
        self.category = Category.objects.create(
            id=uuid4(),
            name="Electronics",
            slug="electronics",
            status="active",
            version=2,
        )
        self.category.published = {
            "id": str(self.category.pk),
            "name": "Electronics",
            "slug": "electronics",
            "description": "",
            "parent": None,
            "sort_order": 0,
            "version": 2,
            "attributes": [
                {
                    "key": "tested",
                    "label": "Tested",
                    "type": "boolean",
                    "required": True,
                    "filterable": True,
                    "unit": "",
                    "choices": [],
                    "min_value": None,
                    "max_value": None,
                    "max_length": 200,
                }
            ],
        }
        self.category.save()
        self.values = {
            "title": "Điện thoại demo",
            "description": "A used phone with visible wear.",
            "category": str(self.category.pk),
            "condition": "used",
            "price_mode": "fixed",
            "price": 1000000,
            "area": "Ha Noi",
            "attributes": {"tested": False},
            "schema_version": 2,
            "phone_consent": True,
            "rights_confirmed": True,
        }
        Profile.objects.update_or_create(
            user=self.user, defaults={"display_name": "Seller", "phone": "+84901234567"}
        )
        PrivacySettings.objects.update_or_create(
            user=self.user, defaults={"share_phone": True}
        )

    def admin_request(self, method, path, values=None):
        return getattr(self.admin_client, method)(
            f"/api/v1/{path}/",
            values,
            format="json",
            HTTP_X_XSRF_TOKEN=self.admin_client.cookies[
                settings.CSRF_COOKIE_NAME
            ].value,
        )

    def create_draft(self, values=None):
        response = self.request("post", "me/listings", values or self.values)
        self.assertEqual(response.status_code, 201, response.data)
        return Listing.objects.get(pk=response.data["id"])

    def upload(self, listing):
        output = io.BytesIO()
        Image.new("RGB", (16, 16), "red").save(output, format="PNG")
        response = self.client.post(
            f"/api/v1/me/listings/{listing.pk}/images/",
            {
                "version": listing.version,
                "image": SimpleUploadedFile(
                    "photo.png", output.getvalue(), content_type="image/png"
                ),
            },
            format="multipart",
            HTTP_X_XSRF_TOKEN=self.client.cookies[settings.CSRF_COOKIE_NAME].value,
        )
        self.assertEqual(response.status_code, 200, response.data)
        listing.refresh_from_db()
        return listing

    def submit(self, listing):
        self.upload(listing)
        response = self.request(
            "post", f"me/listings/{listing.pk}/submit", {"version": listing.version}
        )
        self.assertEqual(response.status_code, 200, response.data)
        listing.refresh_from_db()
        return ModerationCase.objects.get(
            revision__listing=listing, revision__version=listing.submitted_version
        )

    def approve(self, listing):
        case = self.submit(listing)
        response = self.admin_request(
            "post",
            f"admin/moderation/{case.pk}/decision",
            {
                "version": case.version,
                "decision": "approve",
                "reason": "The submitted details are acceptable.",
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        listing.refresh_from_db()
        return listing
