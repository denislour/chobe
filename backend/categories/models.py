from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Category(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        ACTIVE = "active"
        RETIRED = "retired"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.CharField(max_length=1000, blank=True)
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    restricted = models.BooleanField(default=False)
    attributes = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=12, choices=Status, default=Status.DRAFT)
    version = models.PositiveIntegerField(default=1)
    published = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "name", "pk")
        permissions = (
            ("publish_category", "Can publish category versions"),
            ("retire_category", "Can retire categories"),
        )

    def __str__(self):
        return self.name


class CategoryRevision(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="revisions"
    )
    version = models.PositiveIntegerField()
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        ordering = ("-version",)
        constraints = (
            models.UniqueConstraint(
                fields=("category", "version"), name="category_revision_unique"
            ),
        )

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Published category revisions cannot be edited.")
        return super().save(*args, **kwargs)


class CategoryAuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="audit_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=20)
    version = models.PositiveIntegerField()
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
