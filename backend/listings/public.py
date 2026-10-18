from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from categories.services.attributes import validate_category_attributes
from categories.services.publication import visible_categories
from listings.models import ListingMetric
from listings.services.management import audit


def apply_review_decision(listing, revision, user, decision, reason):
    """Apply a decision while the workflow holds the listing row lock."""
    if listing.status == "deleted" or listing.retention_due_at <= timezone.now():
        raise ValidationError("This listing is no longer available for review.")
    if decision == "approve":
        if listing.shop.status != "active" or not listing.shop.owner.is_active:
            raise ValidationError("The shop must be active before publishing.")
        snapshot = revision.snapshot
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
        if listing.published.get("version") == revision.version:
            listing.published = {}
            listing.published_at = None
    listing.version += 1
    listing.save()
    audit(listing, user, decision, reason)


def hide_reported_listing(listing, user, reason):
    if listing.status != "deleted":
        listing.status = "hidden"
        listing.moderation_hold = True
        listing.version += 1
        listing.submitted_version = None
        listing.save()
        audit(listing, user, "report_hidden", reason)


def record_listing_metric(listing, kind):
    metric, _ = ListingMetric.objects.get_or_create(
        listing=listing, day=timezone.localdate(), kind=kind
    )
    ListingMetric.objects.filter(pk=metric.pk).update(count=F("count") + 1)
