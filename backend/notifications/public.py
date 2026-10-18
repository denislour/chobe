from listings.models import (
    Notification,
)


def clear_listing_notifications(listing_id):
    Notification.objects.filter(listing_id=listing_id).delete()
