import io
import warnings

from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from accounts.models import Profile
from accounts.services.privacy import withdraw_phone_consent
from accounts.services.versioning import (
    save_versioned,
)


def profile_for(user):
    return Profile.objects.get_or_create(
        user=user, defaults={"display_name": user.username[:80]}
    )[0]


def process_avatar_upload(upload):
    if upload.size > 2 * 1024 * 1024:
        raise ValidationError("Use an image smaller than 2 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValidationError("Use a JPEG, PNG, or WebP image.")
                if max(image.size) > 4096:
                    raise ValidationError(
                        "Image dimensions must not exceed 4096 pixels."
                    )
                image.load()
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((512, 512))
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
        raise ValidationError("Upload a valid image.") from error


def update_profile(instance, values):
    values = values.copy()
    with transaction.atomic():
        changed_phone = "phone" in values and values["phone"] != instance.phone
        if values.pop("remove_avatar", False):
            values["avatar"] = b""
        instance = save_versioned(instance, values)
        if changed_phone:
            withdraw_phone_consent(instance.user)
    return instance
