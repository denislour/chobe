import calendar

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.services.versioning import VersionConflict
from listings.models import Listing, ListingAuditEvent
from shops.models import Shop

DRAFT_FIELDS = (
    "title",
    "description",
    "condition",
    "price_mode",
    "price",
    "area",
    "attributes",
    "schema_version",
    "phone_consent",
    "rights_confirmed",
)


def six_months_after(value):
    month = value.month + 6
    year = value.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return value.replace(
        year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1])
    )


def owner_activity(listing):
    listing.last_owner_action_at = timezone.now()
    listing.retention_due_at = six_months_after(listing.last_owner_action_at)


def check_version(listing, version):
    if listing.version != version:
        raise VersionConflict("This listing changed. Reload it before trying again.")


def audit(listing, user, action, reason="", source="manual"):
    ListingAuditEvent.objects.create(
        listing=listing,
        actor=user,
        action=action,
        version=listing.version,
        reason=reason,
        source=source,
    )


def locked_listing(listing, user=None):
    queryset = Listing.objects.select_for_update().select_related("shop")
    if user is not None:
        queryset = queryset.filter(shop__owner=user)
    instance = queryset.get(pk=listing.pk)
    if instance.status == "deleted":
        raise ValidationError("This listing has been deleted and cannot be restored.")
    return instance


def draft_snapshot(listing):
    snapshot = {key: getattr(listing, key) for key in DRAFT_FIELDS}
    snapshot.update(
        id=listing.pk,
        version=listing.version,
        category=str(listing.category_id) if listing.category_id else None,
        images=[
            str(value)
            for value in listing.images.filter(attached=True).values_list(
                "pk", flat=True
            )
        ],
    )
    return snapshot


def save_draft(user, values, instance=None):
    values = values.copy()
    with transaction.atomic():
        if instance:
            instance = locked_listing(instance, user)
            check_version(instance, values.pop("version"))
            instance.version += 1
            instance.submitted_version = None
        else:
            shop = (
                Shop.objects.select_for_update()
                .filter(owner=user, status="active", owner__is_active=True)
                .first()
            )
            if shop is None:
                raise ValidationError("Create an active shop before adding a listing.")
            instance = Listing(shop=shop)
        for key, value in values.items():
            setattr(instance, key, value)
        owner_activity(instance)
        instance.save()
        audit(instance, user, "draft_saved")
    return instance












