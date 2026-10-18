from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from discovery.queries import public_listings, search_listings
from listings.models import Notification, NotificationPreference, SavedSearch


def match_searches(listing_id=None, version=None, *, frequency="immediate"):
    queryset = public_listings()
    if listing_id is not None:
        queryset = queryset.filter(pk=listing_id, published__version=version)
    created = 0
    for search in (
        SavedSearch.objects.filter(
            active=True, frequency=frequency, user__is_active=True
        )
        .select_related("user")
        .iterator()
    ):
        preferences = NotificationPreference.objects.filter(
            user=search.user, inbox=True
        ).first()
        if preferences is None:
            continue
        notified = Notification.objects.filter(
            search=search,
            listing_id=OuterRef("pk"),
            listing_version=OuterRef("published__version"),
        )
        matches = (
            search_listings(
                search.filters, queryset.filter(published_at__gte=search.created_at)
            )
            .annotate(already_notified=Exists(notified))
            .filter(already_notified=False)[:100]
        )
        for listing in matches:
            with transaction.atomic():
                current_search = (
                    SavedSearch.objects.select_for_update()
                    .filter(
                        pk=search.pk,
                        active=True,
                        frequency=frequency,
                        user__is_active=True,
                    )
                    .first()
                )
                preferences = (
                    NotificationPreference.objects.select_for_update()
                    .filter(user=search.user, inbox=True)
                    .first()
                )
                if current_search is None or preferences is None:
                    continue
                if (
                    not search_listings(current_search.filters)
                    .filter(
                        pk=listing.pk, published__version=listing.published["version"]
                    )
                    .exists()
                ):
                    continue
                notification, added = Notification.objects.get_or_create(
                    user=search.user,
                    search=search,
                    listing=listing,
                    listing_version=listing.published["version"],
                    defaults={
                        "email_status": "queued" if preferences.email else "blocked"
                    },
                )
                if added:
                    created += 1
                    if preferences.email:
                        from listings.tasks.notifications import deliver_notification

                        deliver_notification.enqueue(notification.pk)
    return created


def send_notification_email(notification_id):
    notification = (
        Notification.objects.select_related("user", "search", "listing")
        .filter(pk=notification_id)
        .first()
    )
    if notification is None or notification.email_status != "queued":
        return False
    allowed = (
        notification.user.is_active
        and notification.search.active
        and NotificationPreference.objects.filter(
            user=notification.user, inbox=True, email=True
        ).exists()
        and search_listings(notification.search.filters)
        .filter(
            pk=notification.listing_id, published__version=notification.listing_version
        )
        .exists()
    )
    if not allowed or not notification.user.email:
        Notification.objects.filter(pk=notification.pk, email_status="queued").update(
            email_status="blocked"
        )
        return False
    if not Notification.objects.filter(
        pk=notification.pk, email_status="queued"
    ).update(email_status="sending"):
        return False
    try:
        send_mail(
            "A new listing matches your saved search",
            f"A listing matches your search on Chobe.\n{settings.FRONTEND_URL}/listings/{notification.listing_id}\n\nManage alerts in your account settings.",
            settings.DEFAULT_FROM_EMAIL,
            [notification.user.email],
        )
    except Exception:
        Notification.objects.filter(pk=notification.pk).update(email_status="failed")
        raise
    Notification.objects.filter(pk=notification.pk).update(email_status="sent")
    return True


def cleanup_notifications():
    return Notification.objects.filter(
        created_at__lt=timezone.now() - timedelta(days=90)
    ).delete()[0]
