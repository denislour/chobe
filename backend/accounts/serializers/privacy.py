from typing import ClassVar

from django.utils import timezone
from rest_framework import serializers

from accounts.models import AccountDataExport, PrivacySettings, ViewingHistory
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


class ViewingHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewingHistory
        fields = ("listing_id", "viewed_at")
        read_only_fields = ("viewed_at",)
        validators = ()
        extra_kwargs: ClassVar[dict] = {"listing_id": {"min_value": 1}}


class AccountDataExportSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source="pk", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = AccountDataExport
        fields = ("job_id", "status", "created_at", "expires_at")

    def get_status(self, obj) -> str:
        if obj.expires_at and obj.expires_at <= timezone.now():
            return AccountDataExport.Status.EXPIRED
        return obj.status
