from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.constants import DEMO_ADMIN_PASSWORD, DEMO_ADMIN_USERNAME
from accounts.models import User


class DemoAdminTests(TestCase):
    def setUp(self):
        call_command("seed_demo_admin", stdout=StringIO())

    def test_seed_can_run_again_without_creating_another_user(self):
        user = User.objects.get(username=DEMO_ADMIN_USERNAME)
        password_hash = user.password
        call_command("seed_demo_admin", stdout=StringIO())
        user.refresh_from_db()

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.password, password_hash)
        self.assertTrue(user.is_active and user.is_staff and user.is_superuser)
        self.assertTrue(
            self.client.login(
                username=DEMO_ADMIN_USERNAME, password=DEMO_ADMIN_PASSWORD
            )
        )

    def test_seed_restores_demo_admin_access(self):
        User.objects.filter(username=DEMO_ADMIN_USERNAME).update(
            password="!", is_active=False, is_staff=False, is_superuser=False
        )
        call_command("seed_demo_admin", stdout=StringIO())
        self.assertTrue(
            self.client.login(
                username=DEMO_ADMIN_USERNAME, password=DEMO_ADMIN_PASSWORD
            )
        )
        self.assertEqual(self.client.get("/admin/").status_code, 200)
