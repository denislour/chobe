from django.db import transaction

from listings.services.management import submit_listing
from moderation.public import open_listing_review


def submit_for_review(user, listing, version):
    with transaction.atomic():
        listing = submit_listing(user, listing, version)
        open_listing_review(listing)
    return listing
