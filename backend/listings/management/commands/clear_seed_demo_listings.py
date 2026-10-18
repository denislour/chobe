from uuid import NAMESPACE_URL, uuid5

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from accounts.management.commands.seed_demo_accounts import demo_accounts
from accounts.models import ViewingHistory
from engagement.models import Favorite, SavedSearch
from listings.management.commands.seed_demo_listings import DEMO_PRODUCTS
from listings.models import Listing
from moderation.models import Report
from notifications.models import NotificationPreference


@transaction.atomic
def clear_seed_demo_listings():
    if not settings.DEMO_MODE:
        raise CommandError("Set DJANGO_DEMO_MODE=true before clearing demo data.")
    users = list(demo_accounts(require_all=False).values())
    scope = Q(pk__in=[])
    for shop_index, (username, products) in enumerate(DEMO_PRODUCTS.items(), start=1):
        scope |= Q(
            pk__in=[
                1000 + shop_index * 100 + index + 1 for index in range(len(products))
            ],
            shop_id=uuid5(NAMESPACE_URL, f"chobe-demo-v1/shop/{username}"),
        )
    listings = Listing.objects.filter(scope, shop__owner__in=users)
    ids = list(listings.values_list("pk", flat=True))
    count = len(ids)
    ViewingHistory.objects.filter(Q(listing_id__in=ids) | Q(user__in=users)).delete()
    Favorite.objects.filter(user__in=users).delete()
    SavedSearch.objects.filter(user__in=users).delete()
    NotificationPreference.objects.filter(user__in=users).delete()
    Report.objects.filter(reporter__in=users).delete()
    listings.delete()
    return count


class Command(BaseCommand):
    help = "Clear reserved demo listings and demo search, notification and report data."

    def handle(self, *args, **options):
        count = clear_seed_demo_listings()
        self.stdout.write(self.style.SUCCESS(f"Cleared {count} demo listings."))
