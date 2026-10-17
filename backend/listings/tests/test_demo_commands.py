from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from accounts.models import User
from accounts.tests.base import AccountAPITestCase
from categories.models import Category, CategoryRevision
from listings.models import Listing
from shops.models import Shop


@override_settings(DEMO_MODE=True)
class DemoCommandTests(AccountAPITestCase):
    def command(self, name, **options):
        call_command(name, stdout=StringIO(), **options)

    def seed(self, directory):
        self.command("seed_demo_accounts")
        self.command("seed_demo_categories")
        self.command("seed_demo_shops")
        self.command("seed_demo_listings", guide=Path(directory) / "demo.md")

    def test_native_commands_seed_and_clear_without_removing_unrelated_data(self):
        real_shop = Shop.objects.create(owner=self.user, name="Real shop", slug="real")
        with TemporaryDirectory() as directory:
            self.seed(directory)
        self.assertEqual(Listing.objects.count(), 100)
        self.assertEqual(Shop.objects.count(), 11)
        self.assertEqual(User.objects.filter(username__startswith="demo_").count(), 21)
        for app in ("listings", "shops", "categories", "accounts"):
            for _ in range(2):
                self.command(f"clear_seed_demo_{app}")
        self.assertFalse(Listing.objects.exists())
        self.assertFalse(Category.objects.exists())
        self.assertFalse(User.objects.filter(username__startswith="demo_").exists())
        self.assertTrue(Shop.objects.filter(pk=real_shop.pk, owner=self.user).exists())
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_clear_refuses_accounts_and_shops_that_still_have_dependencies(self):
        with TemporaryDirectory() as directory:
            self.seed(directory)
        for app in ("accounts", "shops", "categories"):
            with self.subTest(app=app), self.assertRaises(CommandError):
                self.command(f"clear_seed_demo_{app}")
        self.assertEqual(Listing.objects.count(), 100)
        self.assertEqual(Shop.objects.count(), 10)

    def test_clear_preserves_taxonomy_with_children_outside_the_demo(self):
        self.command("seed_demo_accounts")
        self.command("seed_demo_categories")
        category = Category.objects.get(slug="electronics")
        Category.objects.create(name="Real child", slug="real-child", parent=category)
        before = CategoryRevision.objects.count()
        with self.assertRaises(CommandError):
            self.command("clear_seed_demo_categories")
        self.assertEqual(CategoryRevision.objects.count(), before)
        self.assertTrue(Category.objects.filter(pk=category.pk).exists())

    def test_clear_preserves_reserved_usernames_owned_by_other_accounts(self):
        user = User.objects.create_user(
            "demo_minh", "real@example.invalid", "pass12345"
        )
        self.command("clear_seed_demo_accounts")
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

    @override_settings(DEMO_MODE=False)
    def test_seed_and_clear_commands_require_demo_mode(self):
        before = User.objects.count()
        for app in ("accounts", "categories", "shops", "listings"):
            for prefix in ("seed_demo", "clear_seed_demo"):
                with (
                    self.subTest(app=app, prefix=prefix),
                    self.assertRaises(CommandError),
                ):
                    self.command(f"{prefix}_{app}")
        self.assertEqual(User.objects.count(), before)
        self.assertFalse(Shop.objects.exists())
