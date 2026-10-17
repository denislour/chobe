
from django.utils import timezone

from categories.services.publication import visible_categories
from listings.models import Listing


def public_listings():
    categories = list(visible_categories())
    return (
        Listing.objects.filter(
            status__in=("active", "pending", "rejected"),
            moderation_hold=False,
            shop__status="active",
            shop__owner__is_active=True,
            retention_due_at__gt=timezone.now(),
            published__category__in=categories,
        )
        .exclude(published={})
        .select_related("shop", "shop__owner")
    )


