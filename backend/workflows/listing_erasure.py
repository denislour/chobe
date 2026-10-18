from django.db import transaction
from django.utils import timezone

from accounts.models import ViewingHistory
from engagement.public import clear_listing_favorites
from listings.models import Listing
from listings.public import erase_listing_content
from listings.services.management import (
    check_version,
    locked_listing,
)
from notifications.public import clear_listing_notifications


def delete_listing(user, listing, version):
    with transaction.atomic():
        listing = locked_listing(listing, user)
        check_version(listing, version)
        erase_listing(listing, user, "owner_deleted")


@transaction.atomic
def erase_listing(listing, user, action):
    erase_listing_content(listing, user, action)
    clear_listing_favorites(listing.pk)
    clear_listing_notifications(listing.pk)
    ViewingHistory.objects.filter(listing_id=listing.pk).delete()


def cleanup_inactive_listings():
    count = 0
    for pk in (
        Listing.objects.filter(retention_due_at__lte=timezone.now())
        .exclude(status="deleted")
        .values_list("pk", flat=True)
        .iterator()
    ):
        with transaction.atomic():
            listing = Listing.objects.select_for_update().get(pk=pk)
            if (
                listing.status != "deleted"
                and listing.retention_due_at <= timezone.now()
            ):
                erase_listing(listing, None, "retention_deleted")
                count += 1
    return count
