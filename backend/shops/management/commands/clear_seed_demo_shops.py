from uuid import NAMESPACE_URL, uuid5

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.management.commands.seed_demo_accounts import demo_accounts
from listings.models import Listing
from shops.management.commands.seed_demo_shops import DEMO_SHOPS
from shops.models import Shop


@transaction.atomic
def clear_seed_demo_shops():
    if not settings.DEMO_MODE:
        raise CommandError("Set DJANGO_DEMO_MODE=true before clearing demo data.")
    shop_ids = [
        uuid5(NAMESPACE_URL, f"chobe-demo-v1/shop/{username}")
        for username, *_ in DEMO_SHOPS
    ]
    shops = Shop.objects.filter(
        pk__in=shop_ids, owner__in=demo_accounts(require_all=False).values()
    )
    if Listing.objects.filter(shop__in=shops).exists():
        raise CommandError(
            "Clear demo listings first. Shops with listings are preserved."
        )
    count = shops.count()
    shops.delete()
    return count


class Command(BaseCommand):
    help = "Clear reserved demo shops, their follows, slug history and audit data."

    def handle(self, *args, **options):
        count = clear_seed_demo_shops()
        self.stdout.write(self.style.SUCCESS(f"Cleared {count} demo shops."))
