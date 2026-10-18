from rest_framework import serializers

from moderation.models import Report


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
