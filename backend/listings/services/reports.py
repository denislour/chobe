from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.exceptions import VersionConflict
from listings.models import (
    Listing,
    Report,
    ReportDecision,
)
from listings.public import hide_reported_listing
from shops.services.moderation import moderate_shop


def decide_report(user, report, values):
    if (
        not user.is_active
        or not user.is_staff
        or not user.has_perm("listings.review_report")
    ):
        raise PermissionDenied()
    with transaction.atomic():
        report = Report.objects.select_for_update().get(pk=report.pk)
        if report.version != values["version"]:
            raise VersionConflict()
        action = values["action"]
        if action == "hide_listing":
            if not user.has_perm("listings.moderate_listing"):
                raise PermissionDenied("You do not have permission to hide listings.")
            if report.listing_id is None:
                raise ValidationError("This report does not target a listing.")
            listing = Listing.objects.select_for_update().get(pk=report.listing_id)
            hide_reported_listing(listing, user, values["reason"])
        if action == "suspend_shop":
            shop_id = report.shop_id or report.listing.shop_id
            moderate_shop(shop_id, user, suspend=True)
        statuses = {
            "review": "reviewing",
            "dismiss": "dismissed",
            "resolve": "resolved",
            "hide_listing": "resolved",
            "suspend_shop": "resolved",
        }
        report.status = statuses[action]
        report.response = values["response"]
        report.version += 1
        report.save()
        ReportDecision.objects.create(
            report=report, actor=user, action=action, reason=values["reason"]
        )
    return report
