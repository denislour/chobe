from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.services.versioning import (
    save_versioned,
)
from common.exceptions import (
    VersionConflict,
)
from shops.models import Shop, ShopSlug
from shops.services.audit import audit_change

OWNER_TRANSITIONS = {
    Shop.Status.ACTIVE: {Shop.Status.PAUSED, Shop.Status.CLOSED},
    Shop.Status.PAUSED: {Shop.Status.ACTIVE, Shop.Status.CLOSED},
    Shop.Status.SUSPENDED: set(),
    Shop.Status.CLOSED: set(),
}


def require_active_owner(user):
    if not get_user_model().objects.filter(pk=user.pk, is_active=True).exists():
        raise PermissionDenied("Log in again before changing your shop.")


def reserve_slug(shop, slug):
    existing = ShopSlug.objects.filter(slug=slug).first()
    if existing is not None and existing.shop_id != shop.pk:
        raise ValidationError({"slug": ["This shop address is already in use."]})
    if existing is None:
        ShopSlug.objects.create(shop=shop, slug=slug)


def create_shop(user, values):
    try:
        with transaction.atomic():
            require_active_owner(user)
            if Shop.objects.filter(owner=user).exists():
                raise ValidationError("You already have a shop.")
            shop = Shop.objects.create(owner=user, **values)
            reserve_slug(shop, shop.slug)
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
            for field in ("logo", "banner"):
                if values.pop(f"remove_{field}", False):
                    values[field] = b""
            fields = sorted(set(values) - {"version"})
            shop = save_versioned(shop, values)
            reserve_slug(shop, shop.slug)
            changes = {"fields": fields}
            if old_slug != shop.slug:
                changes["slug"] = {"from": old_slug, "to": shop.slug}
            audit_change(shop, user, "updated", changes)
            return shop
    except IntegrityError as error:
        raise ValidationError(
            {"slug": ["This shop address is already in use."]}
        ) from error


def change_shop_status(instance, user, values):
    with transaction.atomic():
        require_active_owner(user)
        shop = Shop.objects.select_for_update().get(pk=instance.pk, owner=user)
        status = values["status"]
        if shop.version != values["version"]:
            raise VersionConflict()
        if status not in OWNER_TRANSITIONS[shop.status]:
            raise ValidationError({"status": ["This status change is not allowed."]})
        previous = shop.status
        shop = save_versioned(shop, values.copy())
        audit_change(shop, user, "status_changed", {"from": previous, "to": status})
        return shop
