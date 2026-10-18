from rest_framework import serializers

from listings.models import Listing


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
