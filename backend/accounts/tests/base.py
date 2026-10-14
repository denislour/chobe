from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from accounts.constants import DEMO_ADMIN_PASSWORD
from accounts.models import User


class AccountAPITestCase(APITestCase):
    databases = frozenset({"default", "cache"})

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = User.objects.create_user(
            "member", "member@example.com", DEMO_ADMIN_PASSWORD
        )
        self.other = User.objects.create_user(
            "other", "other@example.com", DEMO_ADMIN_PASSWORD
        )
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.client.get("/api/v1/auth/session/")

    def request(self, method, path, payload=None):
        return getattr(self.client, method)(
            f"/api/v1/{path}/",
            payload,
            format="json",
            HTTP_X_XSRF_TOKEN=self.client.cookies[settings.CSRF_COOKIE_NAME].value,
        )
