from typing import ClassVar
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Listing(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        PENDING = "pending"
        REJECTED = "rejected"
        ACTIVE = "active"
        HIDDEN = "hidden"
        SOLD = "sold"
        DELETED = "deleted"

    class PriceMode(models.TextChoices):
        FIXED = "fixed"
        NEGOTIABLE = "negotiable"
        FREE = "free"

    class Condition(models.TextChoices):
        NEW = "new"
        USED = "used"

    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, related_name="listings"
    )
    category = models.ForeignKey(
        "categories.Category", on_delete=models.PROTECT, null=True
    )
    title = models.CharField(max_length=160, blank=True)
    description = models.TextField(max_length=10000, blank=True)
    condition = models.CharField(
        max_length=8, choices=Condition, default=Condition.USED
    )
    price_mode = models.CharField(
        max_length=12, choices=PriceMode, default=PriceMode.FIXED
    )
    price = models.PositiveBigIntegerField(null=True, blank=True)
    area = models.CharField(max_length=120, blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    schema_version = models.PositiveIntegerField(default=1)
    phone_consent = models.BooleanField(default=False)
    rights_confirmed = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=Status, default=Status.DRAFT)
    version = models.PositiveIntegerField(default=1)
    moderation_hold = models.BooleanField(default=False)
    submitted_version = models.PositiveIntegerField(null=True, blank=True)
    published = models.JSONField(default=dict, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    last_owner_action_at = models.DateTimeField()
    retention_due_at = models.DateTimeField(db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        permissions: ClassVar[list] = [
            ("moderate_listing", "Can review and publish listing snapshots")
        ]
        indexes: ClassVar[list] = [models.Index(fields=("shop", "status"))]

    def __str__(self):
        return self.title or f"Listing {self.pk}"


class ListingImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="images"
    )
    content = models.BinaryField()
    position = models.PositiveSmallIntegerField(default=0)
    attached = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("position", "created_at", "pk")


class ListingRevision(models.Model):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="revisions"
    )
    version = models.PositiveIntegerField()
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-version",)
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=("listing", "version"), name="listing_revision_unique"
            )
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Submitted revisions cannot be changed.")
        return super().save(*args, **kwargs)


class ModerationCase(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"

    revision = models.OneToOneField(
        ListingRevision, on_delete=models.CASCADE, related_name="moderation"
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
        ordering = ("-created_at", "-pk")


class ListingAuditEvent(models.Model):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="audit_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=32)
    source = models.CharField(max_length=12, default="manual")
    version = models.PositiveIntegerField()
    reason = models.CharField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="favorites"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
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
        ordering = ("-created_at", "-pk")


class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    inbox = models.BooleanField(default=False)
    email = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    search = models.ForeignKey(SavedSearch, on_delete=models.CASCADE)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    listing_version = models.PositiveIntegerField()
    read_at = models.DateTimeField(null=True, blank=True)
    email_status = models.CharField(max_length=12, default="blocked")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=("search", "listing", "listing_version"),
                name="listing_notification_unique",
            )
        ]


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
        Listing, on_delete=models.CASCADE, null=True, blank=True
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


class ListingMetric(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    day = models.DateField()
    kind = models.CharField(
        max_length=8, choices=[("view", "View"), ("call", "Call"), ("copy", "Copy")]
    )
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=("listing", "day", "kind"), name="listing_metric_unique"
            )
        ]
