from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.services.versioning import (
    save_versioned,
)
from shops.models import Shop
from shops.services.audit import audit_change


def moderate_shop(shop_id, actor, *, suspend):
    if (
        not actor.is_active
        or not actor.is_staff
        or not actor.has_perm("shops.change_shop")
    ):
        raise PermissionDenied("You do not have permission to moderate shops.")
    with transaction.atomic():
        shop = Shop.objects.select_for_update().get(pk=shop_id)
        previous = shop.status
        if suspend:
            if previous not in (Shop.Status.ACTIVE, Shop.Status.PAUSED):
                raise ValidationError("Only active or paused shops can be suspended.")
            values = {"status": Shop.Status.SUSPENDED, "suspended_from": previous}
        else:
            if previous != Shop.Status.SUSPENDED:
                raise ValidationError("Only suspended shops can be restored.")
            values = {"status": shop.suspended_from, "suspended_from": ""}
        shop = save_versioned(shop, {"version": shop.version, **values})
        audit_change(shop, actor, "moderated", {"from": previous, "to": shop.status})
        return shop
