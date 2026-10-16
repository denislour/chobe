from uuid import uuid4

from django.conf import settings
from django.db import models


class Shop(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active"
        PAUSED = "paused"
        SUSPENDED = "suspended"
        CLOSED = "closed"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shop"
    )
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.CharField(max_length=1000)
    area = models.CharField(max_length=120)
    contact_hours = models.CharField(max_length=120, blank=True)
    website_url = models.URLField(max_length=400, blank=True)
    social_url = models.URLField(max_length=400, blank=True)
    logo = models.BinaryField(default=bytes, blank=True)
    banner = models.BinaryField(default=bytes, blank=True)
    status = models.CharField(max_length=12, choices=Status, default=Status.ACTIVE)
    suspended_from = models.CharField(max_length=12, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ShopSlug(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="slugs")
    slug = models.SlugField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ShopAuditEvent(models.Model):
    shop = models.ForeignKey(
        Shop, on_delete=models.CASCADE, related_name="audit_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=24)
    changes = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
