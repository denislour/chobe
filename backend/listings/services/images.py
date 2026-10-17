import io
import warnings

from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from listings.models import ListingImage
from listings.services.management import (
    audit,
    check_version,
    locked_listing,
    owner_activity,
)


def process_listing_image(upload):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError({"image": ["Use an image smaller than 5 MiB."]})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload, formats=("JPEG", "PNG", "WEBP")) as image:
                if max(image.size) > 8192 or image.width * image.height > 24000000:
                    raise ValueError("Image dimensions exceed the limit.")
                image.load()
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((1920, 1920))
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=85)
                return output.getvalue()
    except (
        OSError,
        ValueError,
        UnidentifiedImageError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as error:
        raise ValidationError(
            {
                "image": [
                    "Upload a valid JPEG, PNG, or WebP image within the size limits."
                ]
            }
        ) from error


def add_image(user, listing, version, upload):
    content = process_listing_image(upload)
    with transaction.atomic():
        listing = locked_listing(listing, user)
        check_version(listing, version)
        count = listing.images.filter(attached=True).count()
        if count >= 10:
            raise ValidationError({"image": ["Use up to 10 images per listing."]})
        ListingImage.objects.create(listing=listing, content=content, position=count)
        listing.version += 1
        listing.submitted_version = None
        owner_activity(listing)
        listing.save()
        audit(listing, user, "image_added")
    return listing


def arrange_images(user, listing, version, ids):
    with transaction.atomic():
        listing = locked_listing(listing, user)
        check_version(listing, version)
        existing = {
            str(pk)
            for pk in listing.images.filter(attached=True).values_list("pk", flat=True)
        }
        if len(ids) != len(set(ids)) or not set(ids).issubset(existing):
            raise ValidationError(
                {
                    "images": [
                        "Choose images attached to this listing, without duplicates."
                    ]
                }
            )
        listing.images.filter(attached=True).exclude(pk__in=ids).update(attached=False)
        for position, pk in enumerate(ids):
            listing.images.filter(pk=pk).update(position=position)
        listing.version += 1
        listing.submitted_version = None
        owner_activity(listing)
        listing.save()
        audit(listing, user, "images_changed")
    return listing
