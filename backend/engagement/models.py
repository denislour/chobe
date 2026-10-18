from typing import ClassVar

from django.conf import settings
from django.db import models


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="favorites"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "listings_favorite"
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=("user", "listing"), name="listing_favorite_unique"
            )
        ]
        ordering = ("-created_at", "-pk")


class SavedSearch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    filters = models.JSONField(default=dict)
    active = models.BooleanField(default=True)
    frequency = models.CharField(
        max_length=12,
        choices=[("immediate", "Immediate"), ("daily", "Daily")],
        default="daily",
    )
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "listings_savedsearch"
        ordering = ("-created_at", "-pk")


class ShopFollow(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shop_follows",
    )
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, related_name="followers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "shops_shopfollow"
        ordering = ("-created_at", "-pk")
        constraints = (
            models.UniqueConstraint(fields=("user", "shop"), name="shop_follow_unique"),
        )
