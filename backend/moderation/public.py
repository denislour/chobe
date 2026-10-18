from listings.models import (
    ModerationCase,
)


def open_listing_review(listing):
    revision = listing.revisions.get(version=listing.submitted_version)
    return ModerationCase.objects.get_or_create(revision=revision)[0]
