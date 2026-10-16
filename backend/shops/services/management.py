from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.services.versioning import VersionConflict, save_versioned
from shops.models import Shop, ShopSlug
from shops.services.audit import audit_change

def require_active_owner(user):
    if not get_user_model().objects.filter(pk=user.pk, is_active=True).exists():
        raise PermissionDenied("Log in again before changing your shop.")


def create_shop(user, values):
    try:
        with transaction.atomic():
            require_active_owner(user)
            if Shop.objects.filter(owner=user).exists():
                raise ValidationError("You already have a shop.")
            shop = Shop.objects.create(owner=user, **values)
            audit_change(shop, user, "created", {"slug": shop.slug})
            return shop
    except IntegrityError as error:
        raise ValidationError(
            "You already have a shop or this shop address is in use. Reload and try again."
        ) from error


def update_shop(instance, user, values):
    values = values.copy()
    try:
        with transaction.atomic():
            require_active_owner(user)
            shop = Shop.objects.select_for_update().get(pk=instance.pk, owner=user)
            if shop.version != values["version"]:
                raise VersionConflict()
            if shop.status == Shop.Status.CLOSED:
                raise ValidationError("A closed shop cannot be edited.")
            old_slug = shop.slug
            fields = sorted(set(values) - {"version"})
            shop = save_versioned(shop, values)
            changes = {"fields": fields}
            if old_slug != shop.slug:
                changes["slug"] = {"from": old_slug, "to": shop.slug}
            audit_change(shop, user, "updated", changes)
            return shop
    except IntegrityError as error:
        raise ValidationError(
            {"slug": ["This shop address is already in use."]}
        ) from error
