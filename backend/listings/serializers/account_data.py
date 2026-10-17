from rest_framework import serializers

from listings.models import (
    Favorite,
    Listing,
    NotificationPreference,
    Report,
    SavedSearch,
)


class ListingSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = (
            "id",
            "title",
            "description",
            "category_id",
            "condition",
            "price_mode",
            "price",
            "area",
            "attributes",
            "schema_version",
            "status",
            "version",
            "phone_consent",
            "created_at",
            "retention_due_at",
        )
        read_only_fields = fields


class FavoriteSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ("listing_id", "created_at")
        read_only_fields = fields


class SavedSearchSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ("name", "filters", "active", "frequency", "created_at")
        read_only_fields = fields


class ReportSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            "id",
            "listing_id",
            "shop_id",
            "reason",
            "description",
            "status",
            "response",
            "created_at",
        )
        read_only_fields = fields


class NotificationPreferenceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ("inbox", "email")
        read_only_fields = fields
