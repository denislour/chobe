import calendar

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.services.versioning import VersionConflict
from categories.services.attributes import validate_category_attributes
from categories.services.publication import visible_categories
from listings.models import Listing, ListingAuditEvent, ListingRevision, ModerationCase
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


def submit_listing(user, listing, version):
    with transaction.atomic():
        listing = locked_listing(listing, user)
        if listing.submitted_version == listing.version and version in (
            listing.version,
            listing.version - 1,
        ):
            return listing
        check_version(listing, version)
        if listing.shop.status != "active":
            raise ValidationError("Activate your shop before submitting a listing.")
        errors = {}
        for field in ("title", "description", "area"):
            if not getattr(listing, field).strip():
                errors[field] = ["This field is required before submission."]
        if listing.price_mode == "fixed" and listing.price is None:
            errors["price"] = ["Enter a price for a fixed-price listing."]
        if listing.price_mode == "free" and listing.price not in (None, 0):
            errors["price"] = ["A free listing cannot have a price."]
        if not listing.rights_confirmed:
            errors["rights_confirmed"] = [
                "Confirm the item details and your rights to these images."
            ]
        if not listing.images.filter(attached=True).exists():
            errors["images"] = ["Add at least one image."]
        if listing.category_id is None:
            errors["category"] = ["Choose a category."]
        if errors:
            raise ValidationError(errors)
        listing.attributes = validate_category_attributes(
            listing.category_id, listing.schema_version, listing.attributes
        )
        if listing.price_mode == "free":
            listing.price = 0
        listing.version += 1
        listing.submitted_version = listing.version
        listing.status = Listing.Status.PENDING
        owner_activity(listing)
        listing.save()
        snapshot = draft_snapshot(listing)
        snapshot["category_schema"] = visible_categories()[str(listing.category_id)]
        revision = ListingRevision.objects.create(
            listing=listing, version=listing.version, snapshot=snapshot
        )
        ModerationCase.objects.create(revision=revision)
        audit(listing, user, "submitted")
    return listing


def change_status(user, listing, version, target):
    with transaction.atomic():
        listing = locked_listing(listing, user)
        check_version(listing, version)
        allowed = {
            "active": {"hidden", "sold"},
            "pending": {"hidden", "sold"},
            "rejected": {"hidden"},
            "hidden": {"active", "sold"},
            "sold": {"active"},
        }
        if target not in allowed.get(listing.status, set()):
            raise ValidationError("This status change is not available.")
        if target == "active" and listing.moderation_hold:
            raise ValidationError(
                "An admin must review this listing before it can be shown again."
            )
        if target == "active" and not listing.published:
            raise ValidationError("Only an approved snapshot can be made public.")
        listing.status = target
        listing.submitted_version = None
        listing.version += 1
        owner_activity(listing)
        listing.save()
        audit(listing, user, f"status_{target}")
    return listing




def delete_listing(user, listing, version):
    with transaction.atomic():
        listing = locked_listing(listing, user)
        check_version(listing, version)
        erase_listing(listing, user, "owner_deleted")


def erase_listing(listing, user, action):
    from accounts.models import ViewingHistory

    listing.version += 1
    listing.status = "deleted"
    listing.deleted_at = timezone.now()
    listing.title = ""
    listing.description = ""
    listing.area = ""
    listing.attributes = {}
    listing.category = None
    listing.price = None
    listing.rights_confirmed = False
    listing.audit_events.update(reason="")
    listing.published = {}
    listing.phone_consent = False
    listing.submitted_version = None
    listing.save()
    listing.images.all().delete()
    listing.revisions.all().delete()
    listing.favorites.all().delete()
    listing.notification_set.all().delete()
    ViewingHistory.objects.filter(listing_id=listing.pk).delete()
    audit(listing, user, action)


