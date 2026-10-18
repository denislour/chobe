from typing import ClassVar
from uuid import uuid4

from django.conf import settings
from django.db import models


class ModerationCase(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"

    revision = models.OneToOneField(
        "listings.ListingRevision", on_delete=models.CASCADE, related_name="moderation"
    )
    status = models.CharField(max_length=12, choices=Status, default=Status.PENDING)
    source = models.CharField(max_length=12, default="manual")
    reason = models.CharField(max_length=2000, blank=True)
    appeal = models.CharField(max_length=2000, blank=True)
    appeal_open = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "listings_moderationcase"
        ordering = ("-created_at", "-pk")


class Report(models.Model):
    class Reason(models.TextChoices):
        PROHIBITED = "prohibited"
        FRAUD = "fraud"
        INCORRECT = "incorrect"
        IMAGES = "images"
        SPAM = "spam"
        OTHER = "other"

    class Status(models.TextChoices):
        OPEN = "open"
        REVIEWING = "reviewing"
        RESOLVED = "resolved"
        DISMISSED = "dismissed"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, null=True, blank=True
    )
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, null=True, blank=True
    )
    reason = models.CharField(max_length=12, choices=Reason)
    description = models.CharField(max_length=2000)
    status = models.CharField(max_length=12, choices=Status, default=Status.OPEN)
    response = models.CharField(max_length=500, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "listings_report"
        ordering = ("-created_at", "-pk")
        permissions: ClassVar[list] = [
            ("review_report", "Can review marketplace reports")
        ]
        constraints: ClassVar[list] = [
            models.CheckConstraint(
                condition=(
                    models.Q(listing__isnull=False, shop__isnull=True)
                    | models.Q(listing__isnull=True, shop__isnull=False)
                ),
                name="report_one_target",
            )
        ]


class ReportDecision(models.Model):
    report = models.ForeignKey(
        Report, on_delete=models.CASCADE, related_name="decisions"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=16)
    reason = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "listings_reportdecision"
