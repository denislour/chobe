import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.services.demo import seed_demo_account_lifecycle, seed_demo_accounts
from categories.services.demo import finish_demo_taxonomy, seed_demo_taxonomy
from listings.services.demo.catalog import seed_demo_listings
from listings.services.demo.engagement import seed_demo_engagement
from listings.services.demo.guide import write_demo_guide
from shops.services.demo import seed_demo_shops


class Command(BaseCommand):
    help = (
        "Create a complete fictional marketplace demo without sending messages "
        "or starting workers."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--guide",
            type=Path,
            default=settings.BASE_DIR.parent / "docs" / "DEMO_DATA.md",
        )
        parser.add_argument(
            "--skip-backup",
            action="store_true",
            help="Skip the SQLite backup, for an isolated test database only.",
        )

    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError("Set DJANGO_DEMO_MODE=true before seeding demo data.")
        if not options["skip_backup"]:
            self.backup_database()
        with transaction.atomic():
            users = seed_demo_accounts()
            categories = seed_demo_taxonomy(users["demo_catalog"])
            shops = seed_demo_shops(users)
            listings = seed_demo_listings(users, shops, categories)
            seed_demo_engagement(users, listings, categories)
            finish_demo_taxonomy(users["demo_catalog"], categories)
            seed_demo_account_lifecycle(users)
        guide = options["guide"].resolve()
        write_demo_guide(guide, users, shops, listings, categories)
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo ready: {len(users)} accounts, {len(shops)} shops, "
                f"{len(listings)} listing scenarios."
            )
        )
        self.stdout.write(f"Account and scenario guide: {guide}")
        self.stdout.write(
            "No emails, SMS, AI requests, outbox jobs, or worker tasks "
            "were sent or started."
        )

    def backup_database(self):
        configuration = settings.DATABASES["default"]
        if configuration["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("This local demo command expects SQLite.")
        source = Path(configuration["NAME"])
        if not source.is_file():
            raise CommandError("Apply migrations before seeding the demo.")
        folder = settings.BASE_DIR / "backups"
        folder.mkdir(mode=0o700, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        destination = folder / f"before-demo-{timestamp}.sqlite3"
        destination.touch(mode=0o600, exist_ok=False)
        with (
            sqlite3.connect(source) as database,
            sqlite3.connect(destination) as backup,
        ):
            database.backup(backup)
        self.stdout.write(f"Database backup: {destination}")
