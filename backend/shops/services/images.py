import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


def process_shop_image_upload(upload, *, bounds):
    if upload.size > 2 * 1024 * 1024:
        raise ValidationError("Use an image smaller than 2 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload, formats=("JPEG", "PNG", "WEBP")) as image:
                if max(image.size) > 4096:
                    raise ValidationError("Use an image up to 4096 pixels per side.")
                image.load()
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail(bounds)
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
        raise ValidationError("Upload a valid JPEG, PNG, or WebP image.") from error
