from typing import ClassVar

from rest_framework import serializers

from accounts.models import PrivacySettings
from accounts.services.privacy import update_privacy


class PrivacySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacySettings
        fields = (
            "share_phone",
            "record_history",
            "consent_at",
            "version",
            "updated_at",
        )
        read_only_fields = ("consent_at", "updated_at")
        extra_kwargs: ClassVar[dict] = {
            "version": {"min_value": 1, "required": True},
        }

    def validate(self, attrs):
        if "version" not in attrs:
            raise serializers.ValidationError({"version": ["This field is required."]})
        return attrs

    def update(self, instance, validated_data):
        return update_privacy(instance, validated_data)
