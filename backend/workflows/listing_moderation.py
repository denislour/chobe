from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.exceptions import VersionConflict
from listings.models import Listing
from listings.public import apply_review_decision
from listings.services.management import audit
from moderation.models import ModerationCase


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
        decision = values["decision"]
        apply_review_decision(listing, case.revision, user, decision, values["reason"])
        case.status = "approved" if decision == "approve" else "rejected"
        case.source = "manual"
        case.reason = values["reason"]
        case.appeal_open = False
        case.version += 1
        case.save()
        if decision == "approve":
            from notifications.tasks import match_listing_searches

            match_listing_searches.enqueue(listing.pk, case.revision.version)
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
