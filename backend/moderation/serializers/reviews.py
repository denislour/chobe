from typing import ClassVar

from rest_framework import serializers

from moderation.models import ModerationCase


class ModerationSerializer(serializers.ModelSerializer):
    listing_id = serializers.IntegerField(source="revision.listing_id", read_only=True)
    listing_version = serializers.IntegerField(
        source="revision.version", read_only=True
    )
    snapshot = serializers.JSONField(source="revision.snapshot", read_only=True)
    current = serializers.SerializerMethodField()

    class Meta:
        model = ModerationCase
        fields = (
            "id",
            "listing_id",
            "listing_version",
            "snapshot",
            "current",
            "status",
            "source",
            "reason",
            "appeal",
            "appeal_open",
            "version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_current(self, instance) -> bool:
        return instance.revision.listing.submitted_version == instance.revision.version


class ModerationDecisionSerializer(serializers.ModelSerializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    reason = serializers.CharField(max_length=2000)

    class Meta:
        model = ModerationCase
        fields = ("version", "decision", "reason")
        extra_kwargs: ClassVar[dict] = {"version": {"required": True, "min_value": 1}}
