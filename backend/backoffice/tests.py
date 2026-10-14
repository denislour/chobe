from django.core.cache import cache
from django.test import TestCase, override_settings

from accounts.constants import DEMO_ADMIN_PASSWORD, DEMO_ADMIN_USERNAME
from accounts.models import User


class AdminTests(TestCase):
    databases = frozenset({"default", "cache"})

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        User.objects.create_superuser(
            username=DEMO_ADMIN_USERNAME, password=DEMO_ADMIN_PASSWORD
        )

    def test_admin_pages_render_with_unfold(self):
        user = User.objects.get(username=DEMO_ADMIN_USERNAME)
        self.client.force_login(user)
        for path in (
            "/admin/",
            "/admin/accounts/user/add/",
            f"/admin/accounts/user/{user.pk}/change/",
            f"/admin/accounts/user/{user.pk}/password/",
            "/admin/auth/group/add/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "unfold/css/styles.css")

    def test_root_redirects_to_admin(self):
        self.assertRedirects(
            self.client.get("/"), "/admin/", fetch_redirect_response=False
        )

    @override_settings(DEMO_MODE=False)
    def test_login_hides_demo_credentials_when_disabled(self):
        response = self.client.get("/admin/login/")
        self.assertNotContains(response, f'placeholder="{DEMO_ADMIN_USERNAME}"')
        self.assertNotContains(response, DEMO_ADMIN_PASSWORD)

    @override_settings(DEMO_MODE=True)
    def test_login_fields_have_placeholders(self):
        response = self.client.get("/admin/login/")

        self.assertContains(response, f'placeholder="{DEMO_ADMIN_USERNAME}"')
        self.assertContains(response, f'placeholder="{DEMO_ADMIN_PASSWORD}"')
        self.assertContains(response, "unfold/css/styles.css")

    def test_account_limit_is_shared_across_clients_and_ips(self):
        for index in range(5):
            self.client.post(
                "/admin/login/",
                {"username": DEMO_ADMIN_USERNAME, "password": "incorrect"},
                REMOTE_ADDR=f"192.0.2.{index + 1}",
            )
        client = self.client_class()
        response = client.post(
            "/admin/login/",
            {"username": DEMO_ADMIN_USERNAME, "password": DEMO_ADMIN_PASSWORD},
            REMOTE_ADDR="192.0.2.100",
        )
        self.assertContains(response, "Too many login attempts.")
        self.assertNotIn("_auth_user_id", client.session)

    def test_ip_limit_cannot_be_bypassed_by_changing_username(self):
        for index in range(20):
            self.client.post(
                "/admin/login/", {"username": f"missing-{index}", "password": "wrong"}
            )
        response = self.client.post(
            "/admin/login/",
            {"username": DEMO_ADMIN_USERNAME, "password": DEMO_ADMIN_PASSWORD},
        )
        self.assertContains(response, "Too many login attempts.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_valid_admin_login_succeeds_below_limit(self):
        response = self.client.post(
            "/admin/login/",
            {"username": DEMO_ADMIN_USERNAME, "password": DEMO_ADMIN_PASSWORD},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)
