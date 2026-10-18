from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management.base import CommandError
from django.db import transaction
from django.test import override_settings
from django_tasks_db.models import DBTaskResult

from accounts.management.commands.seed_demo_accounts import (
    DEMO_PASSWORD,
    seed_demo_account_lifecycle,
    seed_demo_accounts,
)
from accounts.models import PrivacySettings, User, ViewingHistory
from accounts.tests.base import AccountAPITestCase
from categories.management.commands.seed_demo_categories import (
    finish_demo_taxonomy,
    seed_demo_taxonomy,
)
from discovery.queries import public_listings
from listings.management.commands.seed_demo_listings import (
    seed_demo_engagement,
    seed_demo_listings,
    write_demo_guide,
)
from listings.models import Listing
from moderation.models import Report
from notifications.models import Notification
from shops.management.commands.seed_demo_shops import seed_demo_shops
from shops.models import Shop


@override_settings(DEMO_MODE=True)
class DemoSeedTests(AccountAPITestCase):
    def seed(self, guide):
        with transaction.atomic():
            users = seed_demo_accounts()
            categories = seed_demo_taxonomy(users["demo_catalog"])
            shops = seed_demo_shops(users)
            listings = seed_demo_listings(users, shops, categories)
            seed_demo_engagement(users, listings, categories)
            finish_demo_taxonomy(users["demo_catalog"], categories)
            seed_demo_account_lifecycle(users)
        write_demo_guide(guide, users, shops, listings, categories)

    def test_complete_demo_links_accounts_shops_and_private_scenarios(self):
        with TemporaryDirectory() as directory:
            guide = Path(directory) / "demo.md"
            jobs_before = DBTaskResult.objects.count()
            self.seed(guide)
            users = User.objects.filter(email__endswith="@demo.chobe.invalid")
            shops = Shop.objects.filter(owner__in=users)
            listings = Listing.objects.filter(shop__in=shops)
            self.assertEqual(users.count(), 21)
            self.assertEqual(shops.count(), 10)
            self.assertEqual(listings.count(), 100)
            self.assertEqual(
                set(listings.values_list("status", flat=True)),
                set(Listing.Status.values),
            )
            self.assertEqual(public_listings().filter(shop__in=shops).count(), 30)
            self.assertFalse(
                Shop.objects.filter(
                    owner__username__in=(
                        "demo_ha",
                        "demo_quang",
                        "demo_vy",
                        "demo_tuan",
                        "demo_trang",
                    )
                ).exists()
            )
            self.assertFalse(
                ViewingHistory.objects.filter(user__username="demo_vy").exists()
            )
            self.assertFalse(
                PrivacySettings.objects.get(user__username="demo_vy").record_history
            )
            self.assertTrue(
                User.objects.get(username="demo_minh").check_password(DEMO_PASSWORD)
            )
            self.assertEqual(DBTaskResult.objects.count(), jobs_before)
            self.assertEqual(
                set(
                    Notification.objects.filter(user__in=users).values_list(
                        "email_status", flat=True
                    )
                ),
                {"queued", "sending", "sent", "blocked", "failed"},
            )
            self.assertEqual(Report.objects.filter(reporter__in=users).count(), 9)
            text = guide.read_text()
            self.assertIn("demo_trang", text)
            self.assertIn("/compare?ids=1101,1102,1103", text)
            self.assertIn("không phải bằng chứng gửi thư thật", text)

    def test_rerun_preserves_demo_edits_and_unrelated_accounts(self):
        with TemporaryDirectory() as directory:
            guide = Path(directory) / "demo.md"
            self.seed(guide)
            user = User.objects.get(username="demo_minh")
            user.set_password("ChangedDemoPassword!123")
            user.save()
            profile = user.profile
            profile.bio = "A manual demo edit that must survive seeding."
            profile.save()
            listing = Listing.objects.get(pk=1101)
            listing.title = "Manually edited demo title"
            listing.save()
            counts = (
                User.objects.count(),
                Shop.objects.count(),
                Listing.objects.count(),
                Notification.objects.count(),
            )
            self.seed(guide)
            self.assertEqual(
                (
                    User.objects.count(),
                    Shop.objects.count(),
                    Listing.objects.count(),
                    Notification.objects.count(),
                ),
                counts,
            )
            user.refresh_from_db()
            profile.refresh_from_db()
            listing.refresh_from_db()
            self.assertTrue(user.check_password("ChangedDemoPassword!123"))
            self.assertEqual(
                profile.bio, "A manual demo edit that must survive seeding."
            )
            self.assertEqual(listing.title, "Manually edited demo title")
            self.assertTrue(
                User.objects.filter(pk=self.user.pk, username="member").exists()
            )

    def test_demo_mode_is_required_and_reserved_username_conflicts_rollback(self):
        with TemporaryDirectory() as directory:
            guide = Path(directory) / "demo.md"
            with override_settings(DEMO_MODE=False), self.assertRaises(CommandError):
                self.seed(guide)
            self.assertFalse(guide.exists())
            User.objects.create_user(
                "demo_minh", "existing@example.invalid", "ExistingPassword!123"
            )
            before = User.objects.count()
            with self.assertRaises(CommandError):
                self.seed(guide)
            self.assertEqual(User.objects.count(), before)
            self.assertFalse(Shop.objects.exists())
