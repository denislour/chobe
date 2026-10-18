from typing import ClassVar

from django.db import transaction
from rest_framework import serializers

from common.exceptions import VersionConflict
from listings.models import (
    Notification,
    NotificationPreference,
)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ("inbox", "email", "version")
        extra_kwargs: ClassVar[dict] = {"version": {"required": True, "min_value": 1}}

    def update(self, instance, validated_data):
        with transaction.atomic():
            instance = NotificationPreference.objects.select_for_update().get(
                pk=instance.pk
            )
            if instance.version != validated_data.pop("version"):
                raise VersionConflict()
            for key, value in validated_data.items():
                setattr(instance, key, value)
            instance.version += 1
            instance.save()
        return instance


class NotificationSerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    search_name = serializers.CharField(source="search.name", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "listing_id",
            "title",
            "available",
            "search_name",
            "read_at",
            "email_status",
            "created_at",
        )
        read_only_fields = fields

    def get_available(self, instance) -> bool:
        return instance.listing_id in self.context.get("visible_ids", set())

    def get_title(self, instance) -> str:
        return (
            instance.listing.published.get("title", "Listing unavailable")
            if self.get_available(instance)
            else "Listing unavailable"
        )
