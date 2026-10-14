from uuid import uuid4

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    class Meta(AbstractUser.Meta):
        constraints = (
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="accounts_user_email_ci_unique",
                violation_error_message="A user with this email already exists.",
            ),
        )


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=80)
    area = models.CharField(max_length=120, blank=True)
    bio = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=16, blank=True)
    avatar = models.BinaryField(default=bytes, blank=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)


class PrivacySettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="privacy")
    share_phone = models.BooleanField(default=False)
    record_history = models.BooleanField(default=True)
    consent_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)


class ConsentEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    share_phone = models.BooleanField()
    policy_version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)


class ViewingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    listing_id = models.PositiveBigIntegerField()
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-viewed_at", "-pk")
        constraints = (
            models.UniqueConstraint(
                fields=("user", "listing_id"),
                name="accounts_history_user_listing_unique",
            ),
        )


class AccountDataExport(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued"
        PROCESSING = "processing"
        READY = "ready"
        FAILED = "failed"
        EXPIRED = "expired"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=12, choices=Status, default=Status.QUEUED)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = (
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(status__in=("queued", "processing")),
                name="accounts_one_active_export",
            ),
        )


class DeletionRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=12, choices=Status, default=Status.REQUESTED)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
