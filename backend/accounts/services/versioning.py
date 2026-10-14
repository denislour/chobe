from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import APIException


class VersionConflict(APIException):
    status_code = 409
    default_detail = "This page has changed. Reload the latest values and try again."


def save_versioned(instance, values):
    version = values.pop("version")
    values.update(version=F("version") + 1, updated_at=timezone.now())
    if (
        not type(instance)
        .objects.filter(pk=instance.pk, version=version)
        .update(**values)
    ):
        raise VersionConflict()
    instance.refresh_from_db()
    return instance
