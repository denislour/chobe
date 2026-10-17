from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from accounts.constants import DEMO_ADMIN_PASSWORD, DEMO_ADMIN_USERNAME
from accounts.management.commands.seed_demo_accounts import seed_demo_admin
from accounts.models import User


@override_settings(DEMO_MODE=True)
class DemoAdminTests(TestCase):
    def setUp(self):
        seed_demo_admin()

    @override_settings(DEMO_MODE=False)
    def test_seed_is_blocked_without_changing_existing_admin(self):
        user = User.objects.get(username=DEMO_ADMIN_USERNAME)
        password_hash = user.password
        User.objects.filter(pk=user.pk).update(is_staff=False, is_superuser=False)
        with self.assertRaisesMessage(CommandError, "Demo mode is disabled."):
            seed_demo_admin()
        user.refresh_from_db()
        self.assertEqual(user.password, password_hash)
        self.assertFalse(user.is_staff or user.is_superuser)

    def test_seed_can_run_again_without_creating_another_user(self):
        user = User.objects.get(username=DEMO_ADMIN_USERNAME)
        password_hash = user.password
        seed_demo_admin()
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
        seed_demo_admin()
        self.assertTrue(
            self.client.login(
                username=DEMO_ADMIN_USERNAME, password=DEMO_ADMIN_PASSWORD
            )
        )
        self.assertEqual(self.client.get("/admin/").status_code, 200)
