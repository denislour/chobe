from typing import ClassVar

from django.conf import settings
from django.db import models


class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    inbox = models.BooleanField(default=False)
    email = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "listings_notificationpreference"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    search = models.ForeignKey("engagement.SavedSearch", on_delete=models.CASCADE)
    listing = models.ForeignKey("listings.Listing", on_delete=models.CASCADE)
    listing_version = models.PositiveIntegerField()
    read_at = models.DateTimeField(null=True, blank=True)
    email_status = models.CharField(max_length=12, default="blocked")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "listings_notification"
        ordering = ("-created_at", "-pk")
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=("search", "listing", "listing_version"),
                name="listing_notification_unique",
            )
        ]
