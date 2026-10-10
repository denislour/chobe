import json
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import User


class DemoAdminTests(TestCase):
    def setUp(self):
        call_command("seed_demo_admin", stdout=StringIO())

    def test_seed_can_run_again_without_creating_another_user(self):
        user = User.objects.get(username="admin")
        password_hash = user.password
        call_command("seed_demo_admin", stdout=StringIO())
        user.refresh_from_db()

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.password, password_hash)
        self.assertTrue(user.is_active and user.is_staff and user.is_superuser)
        self.assertTrue(self.client.login(username="admin", password="abc123ABC!!!"))

    def test_seed_restores_demo_admin_access(self):
        User.objects.filter(username="admin").update(
            password="!", is_active=False, is_staff=False, is_superuser=False
        )
        call_command("seed_demo_admin", stdout=StringIO())
        self.assertTrue(self.client.login(username="admin", password="abc123ABC!!!"))
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_admin_pages_render_with_unfold(self):
        user = User.objects.get(username="admin")
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


class ApiDocsTests(TestCase):
    def test_schema_endpoint_returns_api_metadata(self):
        response = self.client.get("/api/v1/schema/", HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["info"]["title"], "Chobe API")

    def test_swagger_ui_is_available(self):
        response = self.client.get("/api/v1/docs/")

        self.assertEqual(response.status_code, 200)
