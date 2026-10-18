from typing import ClassVar

from django.db import transaction
from rest_framework import serializers

from common.exceptions import (
    VersionConflict,
)
from discovery.queries import search_listings
from listings.models import Notification, NotificationPreference, SavedSearch
from listings.serializers.discovery import ListingSearchSerializer


class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = (
            "id",
            "name",
            "filters",
            "active",
            "frequency",
            "version",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
        extra_kwargs: ClassVar[dict] = {"version": {"required": False, "min_value": 1}}

    def validate_filters(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Use a search filter object.")
        serializer = ListingSearchSerializer(data=value)
        serializer.is_valid(raise_exception=True)
        filters = dict(serializer.validated_data)
        filters.pop("page", None)
        for key in ("category", "shop"):
            if key in filters:
                filters[key] = str(filters[key])
        search_listings(filters).exists()
        return filters

    def validate(self, attrs):
        if set(self.initial_data) - set(self.fields):
            raise serializers.ValidationError("Use supported saved-search fields.")
        if self.instance and "version" not in attrs:
            raise serializers.ValidationError({"version": ["This field is required."]})
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        with transaction.atomic():
            from accounts.models import User

            User.objects.select_for_update().get(pk=user.pk)
            if SavedSearch.objects.filter(user=user).count() >= 20:
                raise serializers.ValidationError("You can save up to 20 searches.")
            validated_data.pop("version", None)
            return SavedSearch.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        with transaction.atomic():
            instance = SavedSearch.objects.select_for_update().get(pk=instance.pk)
            if instance.version != validated_data.pop("version"):
                raise VersionConflict()
            for key, value in validated_data.items():
                setattr(instance, key, value)
            instance.version += 1
            instance.save()
        return instance


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
