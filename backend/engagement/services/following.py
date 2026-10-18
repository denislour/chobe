from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from accounts.models import User
from shops.models import (
    Shop,
    ShopFollow,
)


def follow_shop(user, shop_id):
    with transaction.atomic():
        if not User.objects.filter(pk=user.pk, is_active=True).exists():
            raise PermissionDenied("Log in again before following shops.")
        shop = get_object_or_404(
            Shop.objects.select_for_update(),
            pk=shop_id,
            status=Shop.Status.ACTIVE,
            owner__is_active=True,
        )
        ShopFollow.objects.get_or_create(user=user, shop=shop)
