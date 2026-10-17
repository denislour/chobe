from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.services.versioning import VersionConflict
from categories.services.attributes import validate_category_attributes
from categories.services.publication import visible_categories
from listings.models import Listing, ModerationCase
from listings.services.management import audit


def decide_listing(user, case, values):
    if (
        not user.is_active
        or not user.is_staff
        or not user.has_perm("listings.moderate_listing")
    ):
        raise PermissionDenied()
    with transaction.atomic():
        listing = Listing.objects.select_for_update().get(pk=case.revision.listing_id)
        case = (
            ModerationCase.objects.select_for_update()
            .select_related("revision")
            .get(pk=case.pk)
        )
        if (
            case.version != values["version"]
            or listing.submitted_version != case.revision.version
        ):
            raise VersionConflict(
                "This review is out of date. Reload the current submitted version."
            )
        if listing.status == "deleted" or listing.retention_due_at <= timezone.now():
            raise ValidationError("This listing is no longer available for review.")
        decision = values["decision"]
        if decision == "approve":
            if listing.shop.status != "active" or not listing.shop.owner.is_active:
                raise ValidationError("The shop must be active before publishing.")
            snapshot = case.revision.snapshot
            if snapshot["category"] not in visible_categories():
                raise ValidationError("The category is no longer available.")
            validate_category_attributes(
                snapshot["category"], snapshot["schema_version"], snapshot["attributes"]
            )
            listing.published = snapshot
            listing.published_at = timezone.now()
            listing.status = "active"
            listing.moderation_hold = False
        else:
            listing.status = "rejected"
            if listing.published.get("version") == case.revision.version:
                listing.published = {}
                listing.published_at = None
        case.status = "approved" if decision == "approve" else "rejected"
        case.source = "manual"
        case.reason = values["reason"]
        case.appeal_open = False
        case.version += 1
        case.save()
        listing.version += 1
        listing.save()
        audit(listing, user, decision, values["reason"])
    return case


def appeal_listing(user, listing, version, reason):
    with transaction.atomic():
        listing = Listing.objects.select_for_update().get(
            pk=listing.pk, shop__owner=user
        )
        if listing.version != version:
            raise VersionConflict("This listing changed. Reload before appealing.")
        case = ModerationCase.objects.filter(
            revision__listing=listing, revision__version=listing.submitted_version
        ).first()
        if case is None or case.status != "rejected" or case.appeal_open:
            raise ValidationError("This decision cannot be appealed right now.")
        case.appeal = reason
        case.appeal_open = True
        case.version += 1
        case.save()
        audit(listing, user, "appealed", reason)
    return listing
