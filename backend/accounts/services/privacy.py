from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import (
    ConsentEvent,
    PrivacySettings,
    Profile,
    ViewingHistory,
)
from accounts.services.versioning import save_versioned


def privacy_for(user):
    return PrivacySettings.objects.get_or_create(user=user)[0]


def withdraw_phone_consent(user):
    privacy = privacy_for(user)
    was_shared = privacy.share_phone
    privacy.share_phone = False
    if was_shared:
        privacy.consent_at = timezone.now()
        ConsentEvent.objects.create(user=user, share_phone=False)
    privacy.version += 1
    privacy.save()


def public_listing_phone(user, *, is_public_listing):
    if not is_public_listing or not user.is_active:
        return None
    return (
        Profile.objects.filter(
            user=user, user__is_active=True, user__privacy__share_phone=True
        )
        .values_list("phone", flat=True)
        .first()
        or None
    )


def update_privacy(instance, values):
    values = values.copy()
    with transaction.atomic():
        if (
            values.get("share_phone")
            and not Profile.objects.filter(user=instance.user)
            .exclude(phone="")
            .exists()
        ):
            raise ValidationError({"share_phone": ["Add a phone number first."]})
        changed = (
            "share_phone" in values and values["share_phone"] != instance.share_phone
        )
        if changed:
            values["consent_at"] = timezone.now()
        instance = save_versioned(instance, values)
        if changed:
            ConsentEvent.objects.create(
                user=instance.user, share_phone=instance.share_phone
            )
        if not instance.record_history:
            clear_viewing_history(instance.user)
    return instance


def viewing_history_for(user):
    if not privacy_for(user).record_history:
        return ViewingHistory.objects.none()
    return ViewingHistory.objects.filter(
        user=user, viewed_at__gte=timezone.now() - timedelta(days=30)
    )[:100]


def record_viewing_history(user, listing_id):
    with transaction.atomic():
        if not privacy_for(user).record_history:
            return None
        entry, _ = ViewingHistory.objects.update_or_create(
            user=user, listing_id=listing_id
        )
        keep = list(viewing_history_for(user).values_list("pk", flat=True))
        ViewingHistory.objects.filter(user=user).exclude(pk__in=keep).delete()
    return entry


def clear_viewing_history(user):
    ViewingHistory.objects.filter(user=user).delete()
